import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import os
import sys
import time
from typing import Dict, List, Tuple
from tqdm import tqdm

logger = logging.getLogger(__name__)

from genre_classifier import (
    BUILTIN_ARTISTS,
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_OTHER,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
    GenreClassifier,
)
from parser import format_seconds, load_playlist

DEFAULT_INPUT_FILE = os.path.join(
    os.path.dirname(__file__), "Мне нравится_965180470_20260915_213456.txt"
)

CLUSTER_FILE_NAMES: Dict[str, str] = {
    CLUSTER_HEAVY_METAL: "Плейлист_Heavy_Metal",
    CLUSTER_DUBSTEP_EDM: "Плейлист_Dubstep_EDM",
    CLUSTER_PHONK_MEMPHIS: "Плейлист_Phonk_Memphis",
    CLUSTER_HIPHOP_TRAP: "Плейлист_HipHop_Trap",
    CLUSTER_ROCK_ALTERNATIVE: "Плейлист_Rock_Alternative",
    CLUSTER_OTHER: "Плейлист_Other_Electronic",
}


def write_txt_playlist(file_path: str, tracks: List[dict]) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        for idx, tr in enumerate(tracks, 1):
            f.write(f"{idx}. {tr['artist_raw']} - {tr['title_raw']} [{tr['duration_fmt']}]\n")


def write_m3u8_playlist(file_path: str, tracks: List[dict]) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for tr in tracks:
            f.write(f"#EXTINF:{tr['duration_sec']},{tr['artist_raw']} - {tr['title_raw']}\n")
            f.write(f"{tr['artist_raw']} - {tr['title_raw']}.mp3\n")


def write_yandex_playlist(file_path: str, tracks: List[dict]) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        for tr in tracks:
            f.write(f"{tr['artist_raw']} - {tr['title_raw']}\n")


def _resolve_artists_api(classifier: GenreClassifier, to_resolve: List[str], max_queries: int, workers: int) -> None:
    batch_to_query = to_resolve[:max_queries]
    print(f"Запрос тегов для {len(batch_to_query):,} артистов (потоков: {workers})...")
    save_buffer: List[Tuple[str, str, List[str], str]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_artist = {
            executor.submit(classifier.resolve_artist_worker, artist): artist
            for artist in batch_to_query
        }
        for future in tqdm(as_completed(future_to_artist), total=len(future_to_artist), desc="Last.fm API"):
            try:
                res = future.result()
                save_buffer.append(res)
                if len(save_buffer) >= 40:
                    classifier.save_cached_artists_batch(save_buffer)
                    save_buffer.clear()
            except Exception as err:
                artist = future_to_artist.get(future, "unknown")
                logger.warning("Ошибка запроса Last.fm для исполнителя '%s': %s", artist, err)

        if save_buffer:
            classifier.save_cached_artists_batch(save_buffer)


def _classify_all_tracks(classifier: GenreClassifier, df) -> Dict[str, List[dict]]:
    classified_tracks: Dict[str, List[dict]] = {
        CLUSTER_HEAVY_METAL: [],
        CLUSTER_DUBSTEP_EDM: [],
        CLUSTER_PHONK_MEMPHIS: [],
        CLUSTER_HIPHOP_TRAP: [],
        CLUSTER_ROCK_ALTERNATIVE: [],
        CLUSTER_OTHER: [],
    }
    records = df.to_dict(orient="records")
    for tr in tqdm(records, desc="Распределение треков"):
        cluster, _ = classifier.classify_track(
            artist_raw=tr["artist_raw"],
            title_raw=tr["title_raw"],
            all_artists=tr["all_artists"],
            allow_network=False,
        )
        if cluster not in classified_tracks:
            cluster = CLUSTER_OTHER
        classified_tracks[cluster].append(tr)
    return classified_tracks


def _save_clustered_playlists(classified_tracks: Dict[str, List[dict]], output_dir: str, total_tracks: int) -> None:
    print("\n" + "=" * 65)
    print("ИТОГИ КЛАСТЕРИЗАЦИИ И СОХРАНЕНИЕ ПЛЕЙЛИСТОВ:")
    print("=" * 65)
    os.makedirs(output_dir, exist_ok=True)
    for cluster_name, tracks in classified_tracks.items():
        base_name = CLUSTER_FILE_NAMES.get(cluster_name, "Плейлист_Прочее")
        txt_path = os.path.join(output_dir, f"{base_name}.txt")
        m3u8_path = os.path.join(output_dir, f"{base_name}.m3u8")
        yandex_path = os.path.join(output_dir, f"{base_name}_yandex.txt")
        write_txt_playlist(txt_path, tracks)
        write_m3u8_playlist(m3u8_path, tracks)
        write_yandex_playlist(yandex_path, tracks)

        total_sec = sum(t["duration_sec"] for t in tracks)
        pct = len(tracks) / total_tracks * 100 if total_tracks else 0
        print(f"🎵 {cluster_name:<20}: {len(tracks):>5,} треков ({pct:>5.1f}%) | {format_seconds(total_sec)}")
        print(f"   TXT   : {os.path.basename(txt_path)}")
        print(f"   M3U8  : {os.path.basename(m3u8_path)}")
        print(f"   Yandex: {os.path.basename(yandex_path)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Автоматическая сортировка и кластеризация треков по жанрам."
    )
    parser.add_argument("--input", "-i", default=DEFAULT_INPUT_FILE, help="Путь к файлу")
    parser.add_argument("--output-dir", "-o", default=os.path.dirname(__file__), help="Папка вывода")
    parser.add_argument("--workers", "-w", type=int, default=8, help="Потоков для Last.fm API")
    parser.add_argument("--max-api-queries", type=int, default=3000, help="Лимит запросов")
    parser.add_argument("--no-network", action="store_true", help="Только локальный кэш")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Ошибка: входной файл {args.input} не найден!")
        sys.exit(1)

    print("=" * 65)
    print("🎧 АВТОМАТИЧЕСКАЯ КЛАСТЕРИЗАЦИЯ МУЗЫКИ ПО ВСЕМ ЖАНРАМ")
    print("=" * 65)
    t0 = time.time()
    df = load_playlist(args.input)
    print(f"Успешно загружено {len(df):,} треков за {time.time() - t0:.2f} сек.\n")

    classifier = GenreClassifier()
    unique_artists = df["primary_artist"].value_counts().index.tolist()
    to_resolve = [
        art for art in unique_artists
        if art.lower() not in BUILTIN_ARTISTS
        and (not classifier.get_cached_artist(art) or classifier.get_cached_artist(art)[0] == CLUSTER_OTHER)
    ]
    print(f"Всего уникальных основных артистов: {len(unique_artists):,}")
    print(f"Требуют классификации через Last.fm API: {len(to_resolve):,}")

    if not args.no_network and to_resolve:
        _resolve_artists_api(classifier, to_resolve, args.max_api_queries, args.workers)

    print("\nКлассификация треков по жанровым кластерам...")
    classified_tracks = _classify_all_tracks(classifier, df)
    _save_clustered_playlists(classified_tracks, args.output_dir, len(df))
    print("Все плейлисты сохранены и готовы к использованию!")


if __name__ == "__main__":
    main()
