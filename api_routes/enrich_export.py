import logging
import os
import queue

import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from flask import Blueprint, jsonify, request, Response, send_file
import pandas as pd

from ai_genre_classifier import _load_keys
from api_routes.auth_sync import stream_queue_events
from api_routes.state import (
    SYNCED_CACHE_PATH,
    get_ai_classifier,
    get_classifier,
    get_dataset,
    set_dataset_cache,
)
import yandex_api

logger = logging.getLogger(__name__)

enrich_export_bp = Blueprint("enrich_export", __name__)


@enrich_export_bp.route("/api/enrich-genres/status", methods=["GET"])
def enrich_genres_status():
    import genre_db
    classifier = get_classifier()
    ai_classifier = get_ai_classifier()
    cache_db = classifier.db_path

    stats = genre_db.get_db_stats(cache_db)
    g_k, q_k = _load_keys()
    has_gemini = bool(ai_classifier.gemini_key or g_k)
    has_groq = bool(ai_classifier.groq_key or q_k)

    return jsonify({
        "total_cached_artists": stats["total"],
        "unresolved_artists": stats["unresolved"],
        "ai_enriched_artists": stats["ai_enriched"],
        "database_backend": stats["backend"],
        "has_gemini": has_gemini,
        "has_groq": has_groq,
    })



def _build_artist_tracks_map() -> Dict[str, List[str]]:
    artist_tracks: Dict[str, List[str]] = {}
    df = get_dataset()
    if not df.empty and "all_artists" in df.columns and "title_raw" in df.columns:
        for _, r in df.iterrows():
            t = str(r.get("title_raw", "")).strip()
            arts = r.get("all_artists", [])
            if isinstance(arts, list):
                for a in arts:
                    k = str(a).strip().lower()
                    if k:
                        artist_tracks.setdefault(k, []).append(t)
    return artist_tracks


def _process_enrichment_batches(
    targets: List[Tuple[str, str]],
    artist_tracks: Dict[str, List[str]],
    cache_db: str,
    q: queue.Queue,
) -> int:
    ai_classifier = get_ai_classifier()
    total = len(targets)
    batch_size = 35
    processed = 0
    saved_total = 0

    for i in range(0, total, batch_size):
        chunk = targets[i : i + batch_size]
        payload = [
            {"artist": name, "tracks": artist_tracks.get(k, [])[:4]}
            for k, name in chunk
        ]
        pct = int(5 + ((i / total) * 90))
        q.put({"type": "progress", "percent": pct, "current": processed, "total": total, "message": f"AI-анализ: {processed}/{total} артистов..."})

        try:
            results, _ = ai_classifier.classify_batch(payload)
            saved = ai_classifier.save_ai_results_to_sqlite(cache_db, results)
            saved_total += saved
        except Exception as ex:
            logger.warning("Ошибка пакета AI: %s", ex)

        processed += len(chunk)
        time.sleep(1.2)

    return saved_total


def _reclassify_library(classifier: Any) -> None:
    classifier.reload_memory_cache()
    df = get_dataset()
    if not df.empty:
        df["genre_cluster"] = [
            classifier.classify_track(a, t, aa, allow_network=False)[0]
            for a, t, aa in zip(df["artist_raw"], df["title_raw"], df["all_artists"])
        ]
        set_dataset_cache(df)
        try:
            df.to_pickle(SYNCED_CACHE_PATH)
        except (IOError, OSError, ValueError) as ex:
            logger.debug("Could not persist synced cache: %s", ex)


def _run_enrich_worker(cache_db: str, q: queue.Queue) -> None:
    try:
        import genre_db
        targets = genre_db.fetch_unresolved_artists(cache_db)
        total = len(targets)
        if total == 0:
            q.put({"type": "done", "percent": 100, "current": 0, "total": 0, "message": "Все артисты уже классифицированы!"})
            return

        q.put({"type": "progress", "percent": 2, "current": 0, "total": total, "message": f"Запуск AI для {total:,} артистов..."})
        artist_tracks = _build_artist_tracks_map()
        saved = _process_enrichment_batches(targets, artist_tracks, cache_db, q)

        classifier = get_classifier()
        _reclassify_library(classifier)

        q.put({"type": "done", "percent": 100, "current": total, "total": total, "total_enriched": saved, "message": f"AI-классификация завершена! Обработано {saved} артистов."})
    except Exception as e:
        q.put({"type": "error", "percent": 0, "message": f"Ошибка AI: {e}"})
    finally:
        q.put(None)



@enrich_export_bp.route("/api/enrich-genres/stream", methods=["GET", "POST"])
def enrich_genres_stream():
    classifier = get_classifier()
    ai_classifier = get_ai_classifier()
    cache_db = classifier.db_path

    if not ai_classifier.gemini_key or not ai_classifier.groq_key:
        g_k, q_k = _load_keys()
        if not ai_classifier.gemini_key and g_k:
            ai_classifier.gemini_key = g_k
        if not ai_classifier.groq_key and q_k:
            ai_classifier.groq_key = q_k

    c_gem = request.headers.get("X-Gemini-Key") or request.args.get("gemini_key")
    c_groq = request.headers.get("X-Groq-Key") or request.args.get("groq_key")
    if c_gem:
        ai_classifier.gemini_key = c_gem.strip()
    if c_groq:
        ai_classifier.groq_key = c_groq.strip()

    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run_enrich_worker, args=(cache_db, q), daemon=True).start()

    return Response(
        stream_queue_events(q, timeout=25),
        mimetype="text/event-stream",
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


def _preset_genre(data: pd.DataFrame, genre: str) -> Tuple[Optional[pd.DataFrame], str, Optional[str]]:
    if not genre or genre.lower() in ("все", "all"):
        return None, "", "Для пресета 'genre' необходимо указать конкретный жанр"
    return data[data["genre_cluster"] == genre], f"⚡ {genre} — Подборка", None


def _preset_gems(data: pd.DataFrame, _: str) -> Tuple[Optional[pd.DataFrame], str, Optional[str]]:
    counts = data["primary_artist"].value_counts()
    rare = set(counts[counts <= 2].index)
    return data[data["primary_artist"].isin(rare)], "💎 Скрытые жемчужины — Редкие артисты", None


PRESET_HANDLERS = {
    "genre": _preset_genre,
    "collab": lambda d, _: (d[d["is_collab"]], "🤝 Фитотека — Все коллаборации", None),
    "solo": lambda d, _: (d[~d["is_collab"]], "🎙️ Соло — Чистый вокал", None),
    "gems": _preset_gems,
    "golden_era": lambda d, _: (d.sort_values(by="id", ascending=False), "⏳ Золотая эра — Первые лайки", None),
}


def _filter_by_preset(data: pd.DataFrame, preset: str, genre: str) -> Tuple[Optional[pd.DataFrame], str, Optional[str]]:
    handler = PRESET_HANDLERS.get(preset)
    if not handler:
        return None, "", f"Неизвестный пресет '{preset}'"
    return handler(data, genre)



@enrich_export_bp.route("/api/export-playlist", methods=["POST"])
def export_playlist():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "error": "Требуется токен авторизации (token)"}), 400

    preset = data.get("preset", "genre").strip().lower()
    genre = data.get("genre", "").strip()
    custom_title = data.get("title", "").strip()
    limit_val = int(data.get("limit", 100)) if str(data.get("limit", 100)).isdigit() else 100

    client, _, err = yandex_api.login_yandex(token)
    if err or not client:
        return jsonify({"success": False, "error": err or "Ошибка авторизации в Яндекс Музыке"}), 401

    df = get_dataset()
    if df.empty or "track_id" not in df.columns:
        return jsonify({"success": False, "error": "Медиатека пуста или не синхронизирована"}), 400

    df_valid = df[df["track_id"].notna() & (df["track_id"].astype(str) != "")].copy()
    if df_valid.empty:
        return jsonify({"success": False, "error": "Не найдено треков с валидными ID"}), 400

    filtered, def_title, err = _filter_by_preset(df_valid, preset, genre)
    if err:
        return jsonify({"success": False, "error": err}), 400
    if filtered is None or filtered.empty:
        return jsonify({"success": False, "error": "По выбранному фильтру не найдено треков"}), 404

    subset = filtered.head(limit_val) if limit_val > 0 else filtered
    final_title = custom_title if custom_title else def_title

    track_dicts = [
        {"track_id": str(r["track_id"]), "album_id": str(r.get("album_id", "")) if pd.notna(r.get("album_id")) else ""}
        for _, r in subset.iterrows()
    ]
    ok, msg, url = yandex_api.create_remote_playlist(client, final_title, track_dicts)
    if not ok:
        return jsonify({"success": False, "error": msg}), 500

    return jsonify({"success": True, "message": msg, "playlist_title": final_title, "playlist_url": url, "tracks_count": len(track_dicts)})


@enrich_export_bp.route("/api/genre-cache/download", methods=["GET"])
def download_genre_cache():
    classifier = get_classifier()
    cache_path = classifier.db_path
    if not os.path.exists(cache_path):
        return jsonify({"success": False, "error": "Файл genre_cache.sqlite не найден"}), 404
    return send_file(cache_path, as_attachment=True, download_name="genre_cache.sqlite")
