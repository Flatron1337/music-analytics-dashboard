import argparse
import json
import os
import sqlite3
import sys
import time
from typing import Dict, List, Set, Tuple

from ai_genre_classifier import (
    AIGenreClassifier,
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_OTHER,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
)

BASE_DIR = os.path.dirname(__file__)
CACHE_DB_PATH = os.path.join(BASE_DIR, "genre_cache.sqlite")
SYNCED_PKL_PATH = os.path.join(BASE_DIR, "synced_likes.pkl")
DEFAULT_TXT_PATH = os.path.join(BASE_DIR, "Мне нравится_965180470_20260915_213456.txt")


def load_artist_tracks_map() -> Dict[str, List[str]]:
    """Builds a map of lowercase artist name -> list of track titles from the library."""
    artist_tracks: Dict[str, List[str]] = {}

    # 1. Try synced pickle
    if os.path.exists(SYNCED_PKL_PATH):
        try:
            import pandas as pd
            df = pd.read_pickle(SYNCED_PKL_PATH)
            if not df.empty and "all_artists" in df.columns and "title_raw" in df.columns:
                for _, row in df.iterrows():
                    title = str(row.get("title_raw", "")).strip()
                    artists = row.get("all_artists", [])
                    if isinstance(artists, list):
                        for art in artists:
                            key = str(art).strip().lower()
                            if key:
                                artist_tracks.setdefault(key, []).append(title)
                return artist_tracks
        except Exception:
            pass

    # 2. Try text playlist file
    txt_candidates = [
        DEFAULT_TXT_PATH,
        *[os.path.join(BASE_DIR, f) for f in os.listdir(BASE_DIR) if f.startswith("Мне нравится") and f.endswith(".txt")]
    ]
    txt_path = next((p for p in txt_candidates if os.path.exists(p)), None)

    if txt_path:
        from parser import load_playlist
        df = load_playlist(txt_path)
        if not df.empty:
            for _, row in df.iterrows():
                title = str(row.get("title_raw", "")).strip()
                artists = row.get("all_artists", [])
                if isinstance(artists, list):
                    for art in artists:
                        key = str(art).strip().lower()
                        if key:
                            artist_tracks.setdefault(key, []).append(title)

    return artist_tracks


def get_target_artists(db_path: str, only_unresolved: bool = True) -> List[Tuple[str, str]]:
    """Returns list of (artist_key, artist_name) needing classification."""
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        if only_unresolved:
            cursor.execute(
                "SELECT artist_key, artist_name FROM artist_cache WHERE source = 'unresolved'"
            )
        else:
            cursor.execute(
                "SELECT artist_key, artist_name FROM artist_cache WHERE source = 'unresolved' OR cluster = 'Other & Electronic'"
            )
        return cursor.fetchall()


def count_clusters(db_path: str) -> Dict[str, int]:
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cluster, count(*) FROM artist_cache GROUP BY cluster")
        return dict(cursor.fetchall())


def main():
    parser = argparse.ArgumentParser(description="AI Genre Enrichment for Music Library")
    parser.add_argument("--batch-size", type=int, default=35, help="Number of artists per AI batch")
    parser.add_argument("--all-other", action="store_true", help="Re-classify all 'Other & Electronic', not only 'unresolved'")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of artists to process (0 = all)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay in seconds between batches to respect rate limits")
    args = parser.parse_args()

    print("=" * 65)
    print(" 🧠 AI GENRE ENRICHMENT (Google Gemini 3.6 Flash + Groq)")
    print("=" * 65)

    if not os.path.exists(CACHE_DB_PATH):
        print(f"❌ База кэша не найдена: {CACHE_DB_PATH}")
        sys.exit(1)

    initial_counts = count_clusters(CACHE_DB_PATH)
    targets = get_target_artists(CACHE_DB_PATH, only_unresolved=not args.all_other)

    if not targets:
        print("✨ Все артисты уже классифицированы! Нет неопределённых исполнителей.")
        return

    if args.limit > 0:
        targets = targets[:args.limit]

    total_count = len(targets)
    print(f"📊 Исходное распределение кластеров: {initial_counts}")
    print(f"🎯 Найдено исполнителей для обработки нейросетью: {total_count:,}")
    print("⏳ Сбор названий треков из медиатеки...")

    artist_tracks_map = load_artist_tracks_map()
    print(f"✅ Найдено треков для {len(artist_tracks_map):,} уникальных артистов.")

    classifier = AIGenreClassifier()
    batch_size = max(5, args.batch_size)
    processed_total = 0
    saved_total = 0

    start_time = time.time()

    for i in range(0, total_count, batch_size):
        chunk = targets[i : i + batch_size]
        items_payload = []

        for key, name in chunk:
            tracks = artist_tracks_map.get(key, [])
            sample_tracks = tracks[:4] if tracks else []
            items_payload.append({
                "artist": name,
                "tracks": sample_tracks,
            })

        batch_idx = (i // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size
        pct = (i / total_count) * 100

        print(f"[{batch_idx}/{total_batches}] ({pct:.1f}%) Запрос AI для {len(items_payload)} артистов...", end="", flush=True)

        try:
            results, provider = classifier.classify_batch(
                items_payload,
                on_progress=lambda msg: print(f"\n  {msg}", flush=True)
            )
            saved = classifier.save_ai_results_to_sqlite(CACHE_DB_PATH, results)
            saved_total += saved
            processed_total += len(chunk)
            print(f" ✅ Готово ({provider}: сохранено {saved})", flush=True)
        except Exception as e:
            print(f" ❌ Ошибка: {e}", flush=True)

        if i + batch_size < total_count:
            time.sleep(args.delay)

    elapsed = time.time() - start_time
    final_counts = count_clusters(CACHE_DB_PATH)

    print("\n" + "=" * 65)
    print(" 🎉 AI КЛАССИФИКАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("=" * 65)
    print(f"⏱ Время работы:    {elapsed:.1f} сек. ({elapsed / 60:.1f} мин.)")
    print(f"📦 Обработано:     {processed_total:,} артистов")
    print(f"💾 Записано в базу: {saved_total:,} записей")
    print("\n📊 Сравнение распределения до и после:")
    for cl in sorted(final_counts.keys()):
        init_c = initial_counts.get(cl, 0)
        fin_c = final_counts.get(cl, 0)
        diff = fin_c - init_c
        diff_str = f"(+{diff:,})" if diff > 0 else f"({diff:,})" if diff < 0 else ""
        print(f" - {cl:<22}: {init_c:>5} -> {fin_c:>5} {diff_str}")
    print("=" * 65)


if __name__ == "__main__":
    main()
