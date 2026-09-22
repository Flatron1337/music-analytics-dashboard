import json
import math
import os
import queue
import re
import sys
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import networkx as nx
import pandas as pd

from ai_genre_classifier import AIGenreClassifier, _load_keys
from genre_classifier import (
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_OTHER,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
    GenreClassifier,
)
from parser import (
    build_collaborations_graph,
    format_seconds,
    load_playlist,
)
import yandex_api

app = Flask(__name__)
CORS(app)

DEFAULT_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "Мне нравится_965180470_20260915_213456.txt"
)
SYNCED_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), "synced_likes.pkl"
)

# Global in-memory cache
_df_cache: Optional[pd.DataFrame] = None
_classifier = GenreClassifier()
_ai_classifier = AIGenreClassifier()

CLUSTER_COLORS: Dict[str, str] = {
    CLUSTER_DUBSTEP_EDM: "#00E5FF",      # Cyber Cyan
    CLUSTER_HEAVY_METAL: "#FF3D00",      # Fiery Red
    CLUSTER_PHONK_MEMPHIS: "#D500F9",    # Neon Purple
    CLUSTER_HIPHOP_TRAP: "#FFD600",      # Electric Yellow
    CLUSTER_ROCK_ALTERNATIVE: "#00E676", # Neon Green
    CLUSTER_OTHER: "#B0BEC5",            # Soft Slate
}

CLUSTER_ICONS: Dict[str, str] = {
    CLUSTER_DUBSTEP_EDM: "electric_bolt",
    CLUSTER_HEAVY_METAL: "local_fire_department",
    CLUSTER_PHONK_MEMPHIS: "speed",
    CLUSTER_HIPHOP_TRAP: "mic",
    CLUSTER_ROCK_ALTERNATIVE: "graphic_eq",
    CLUSTER_OTHER: "category",
}


def get_dataset() -> pd.DataFrame:
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    # 1. First check if there is an up-to-date synced collection on disk
    if os.path.exists(SYNCED_CACHE_PATH):
        try:
            persisted_df = pd.read_pickle(SYNCED_CACHE_PATH)
            if not persisted_df.empty:
                _df_cache = persisted_df
                return _df_cache
        except Exception as e:
            print(f"⚠️ Ошибка загрузки кэша синхронизации: {e}", flush=True)

    # 2. Fallback to base playlist file
    if not os.path.exists(DEFAULT_FILE_PATH):
        _df_cache = pd.DataFrame()
        return _df_cache

    df = load_playlist(DEFAULT_FILE_PATH)
    if df.empty:
        _df_cache = df
        return _df_cache

    # High-speed in-memory classification using zip
    artists_raw = df["artist_raw"].tolist()
    titles_raw = df["title_raw"].tolist()
    all_artists_list = df["all_artists"].tolist()
    genres = [
        _classifier.classify_track(
            artist_raw=a,
            title_raw=t,
            all_artists=aa,
            allow_network=False,
        )[0]
        for a, t, aa in zip(artists_raw, titles_raw, all_artists_list)
    ]

    df["genre_cluster"] = genres
    _df_cache = df
    return _df_cache


# Pre-warm dataset in a background daemon thread
import threading
threading.Thread(target=get_dataset, daemon=True).start()


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Music Analytics REST API (Yandex Music)",
        "status": "online",
        "tracks_loaded": len(_df_cache) if _df_cache is not None else 0,
        "is_ready": _df_cache is not None,
        "endpoints": [
            "/api/health",
            "/api/overview",
            "/api/genres",
            "/api/timeline",
            "/api/tracks",
            "/api/auth/device-code",
            "/api/auth/poll-token",
            "/api/sync-likes",
            "/api/sync-likes/stream",
            "/api/export-playlist",
            "/api/artist",
            "/api/collaborations-graph",
            "/api/collaborations-graph/export-html",
            "/api/enrich-genres/status",
            "/api/enrich-genres/stream",
            "/api/track-stream/<track_id>",
            "/api/duplicates",
            "/api/audio-features",
        ],
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "Music Analytics REST API",
        "tracks_loaded": len(_df_cache) if _df_cache is not None else 0,
        "is_ready": _df_cache is not None,
    })



@app.route("/api/overview", methods=["GET"])
def get_overview():
    df = get_dataset()
    if df.empty:
        return jsonify({"error": "No tracks loaded"}), 404

    total_tracks = len(df)
    total_duration_sec = int(df["duration_sec"].sum())
    avg_duration_sec = int(df["duration_sec"].mean()) if total_tracks > 0 else 0

    all_artists_flat: List[str] = []
    for artists in df["all_artists"]:
        all_artists_flat.extend(artists)

    artist_counts = pd.Series(all_artists_flat).value_counts()
    unique_artists_count = len(artist_counts)

    top_artists = [
        {"artist": artist, "count": int(count)}
        for artist, count in artist_counts.head(15).items()
    ]

    if "artists_count" not in df.columns:
        if "all_artists" in df.columns:
            df["artists_count"] = df["all_artists"].apply(lambda a: len(a) if isinstance(a, list) else 1)
        elif "is_collab" in df.columns:
            df["artists_count"] = df["is_collab"].apply(lambda c: 2 if c else 1)
        else:
            df["artists_count"] = 1

    if "is_collab" not in df.columns:
        df["is_collab"] = df["artists_count"] > 1

    solo_count = int((df["artists_count"] == 1).sum())
    collab_count = int((df["artists_count"] > 1).sum())
    collab_ratio = round((collab_count / total_tracks) * 100, 1) if total_tracks > 0 else 0.0

    return jsonify({
        "total_tracks": total_tracks,
        "total_duration_sec": total_duration_sec,
        "total_duration_fmt": format_seconds(total_duration_sec),
        "avg_duration_sec": avg_duration_sec,
        "avg_duration_fmt": f"{avg_duration_sec // 60}:{avg_duration_sec % 60:02d}",
        "unique_artists": unique_artists_count,
        "solo_count": solo_count,
        "collab_count": collab_count,
        "collab_ratio_percent": collab_ratio,
        "top_artists": top_artists,
    })


@app.route("/api/genres", methods=["GET"])
def get_genres():
    df = get_dataset()
    if df.empty:
        return jsonify({"clusters": []})

    total = len(df)
    counts = df["genre_cluster"].value_counts()

    clusters: List[Dict[str, Any]] = []
    for cluster_name, count in counts.items():
        pct = round((count / total) * 100, 1) if total > 0 else 0.0
        clusters.append({
            "name": cluster_name,
            "count": int(count),
            "percent": pct,
            "color": CLUSTER_COLORS.get(cluster_name, "#FFFFFF"),
            "icon": CLUSTER_ICONS.get(cluster_name, "music_note"),
        })

    return jsonify({"clusters": clusters, "total_tracks": total})


@app.route("/api/timeline", methods=["GET"])
def get_timeline():
    df = get_dataset()
    if df.empty:
        return jsonify({"segments": []})

    total = len(df)
    num_segments = min(8, max(1, total))
    segment_size = max(1, total // num_segments)
    segments: List[Dict[str, Any]] = []

    for i in range(num_segments):
        start_idx = i * segment_size
        end_idx = total if i == num_segments - 1 else (i + 1) * segment_size
        seg_slice = df.iloc[start_idx:end_idx]
        if seg_slice.empty:
            continue

        seg_label = f"#{start_idx + 1}–#{end_idx}"
        counts = seg_slice["genre_cluster"].value_counts().to_dict()
        dominant = max(counts, key=counts.get) if counts else "Unknown"

        genre_stats = [
            {
                "genre": g,
                "count": int(c),
                "color": CLUSTER_COLORS.get(g, "#999999"),
                "percent": round(c / len(seg_slice) * 100, 1)
            }
            for g, c in counts.items()
        ]

        segments.append({
            "segment_index": i,
            "label": seg_label,
            "tracks_count": len(seg_slice),
            "dominant_genre": dominant,
            "dominant_color": CLUSTER_COLORS.get(dominant, "#FFCC00"),
            "genres": genre_stats,
        })

    return jsonify({"segments": segments})


@app.route("/api/tracks", methods=["GET"])
def get_tracks():
    df = get_dataset()
    if df.empty:
        return jsonify({"tracks": [], "total": 0, "page": 1, "total_pages": 0})

    query = request.args.get("q", "").strip().lower()
    genre_filter = request.args.get("genre", "").strip()
    sort_by = request.args.get("sort", "newest").strip().lower()
    collab_filter = request.args.get("collab", "all").strip().lower()
    page = max(1, int(request.args.get("page", 1)))
    limit = max(1, min(100, int(request.args.get("limit", 40))))

    filtered = df

    # Filter by genre
    if genre_filter and genre_filter.lower() != "all" and genre_filter.lower() != "все":
        filtered = filtered[filtered["genre_cluster"] == genre_filter]

    # Filter by collaboration type (solo vs collab)
    if collab_filter == "solo":
        filtered = filtered[~filtered["is_collab"]]
    elif collab_filter == "collab":
        filtered = filtered[filtered["is_collab"]]

    # Search query
    if query:
        filtered = filtered[
            filtered["title_raw"].str.lower().str.contains(query, na=False)
            | filtered["artist_raw"].str.lower().str.contains(query, na=False)
        ]

    # Sort tracks
    if sort_by == "oldest":
        filtered = filtered.sort_values(by="id", ascending=False)
    elif sort_by == "duration_desc":
        filtered = filtered.sort_values(by="duration_sec", ascending=False)
    elif sort_by == "duration_asc":
        filtered = filtered.sort_values(by="duration_sec", ascending=True)
    elif sort_by == "title_asc":
        filtered = filtered.sort_values(by="title_raw", key=lambda s: s.str.lower(), ascending=True)
    elif sort_by == "artist_asc":
        filtered = filtered.sort_values(by="artist_raw", key=lambda s: s.str.lower(), ascending=True)
    else:  # newest / default
        filtered = filtered.sort_values(by="id", ascending=True)

    total_filtered = len(filtered)
    total_pages = max(1, math.ceil(total_filtered / limit))
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, total_filtered)

    page_slice = filtered.iloc[start_idx:end_idx]
    tracks: List[Dict[str, Any]] = []

    for _, row in page_slice.iterrows():
        title = row.get("title_raw", "")
        artist = row.get("artist_raw", "")
        yandex_query = urllib.parse.quote_plus(f"{artist} - {title}")
        yandex_url = row.get("yandex_url") or f"https://music.yandex.ru/search?text={yandex_query}"

        tracks.append({
            "id": int(row.get("id", 0)),
            "title": title,
            "artist": artist,
            "artists": row.get("all_artists", []),
            "duration_sec": int(row.get("duration_sec", 0)),
            "duration_fmt": row.get("duration_fmt", "0:00"),
            "genre": row.get("genre_cluster", CLUSTER_OTHER),
            "genre_color": CLUSTER_COLORS.get(row.get("genre_cluster", ""), "#FFFFFF"),
            "is_collab": bool(row.get("is_collab", False)),
            "cover_uri": row.get("cover_uri", ""),
            "yandex_url": yandex_url,
        })

    return jsonify({
        "tracks": tracks,
        "total": total_filtered,
        "page": page,
        "total_pages": total_pages,
        "limit": limit
    })


@app.route("/api/auth/device-code", methods=["POST"])
def auth_device_code():
    data, err = yandex_api.request_yandex_device_code()
    if err or not data:
        return jsonify({"success": False, "error": err or "Failed to get device code"}), 400
    return jsonify({
        "success": True,
        "device_code": data["device_code"],
        "user_code": data["user_code"],
        "verification_url": data.get("verification_url", "https://ya.ru/device"),
        "expires_in": data.get("expires_in", 300),
        "interval": data.get("interval", 5),
    })


@app.route("/api/auth/poll-token", methods=["POST"])
def auth_poll_token():
    data = request.get_json(silent=True) or {}
    device_code = data.get("device_code", "").strip()
    if not device_code:
        return jsonify({"status": "error", "message": "device_code is required"}), 400

    token, err = yandex_api.poll_yandex_device_token(device_code)
    if token:
        return jsonify({"status": "success", "token": token})

    if err:
        err_lower = err.lower()
        if "authorization_pending" in err_lower or "ещё не подтверждён" in err_lower or "не подтвержден" in err_lower:
            return jsonify({"status": "authorization_pending"})
        if "slow_down" in err_lower:
            return jsonify({"status": "slow_down"})
        return jsonify({"status": "error", "message": err})

    return jsonify({"status": "authorization_pending"})


@app.route("/api/sync-likes", methods=["POST"])
def sync_likes():
    global _df_cache
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "error": "token is required"}), 400

    client, user_info, err = yandex_api.login_yandex(token)
    if err or not client:
        return jsonify({"success": False, "error": err or "Invalid token"}), 400

    try:
        likes_df = yandex_api.fetch_user_likes_df(client)
    except Exception as e:
        return jsonify({"success": False, "error": f"Ошибка загрузки треков: {e}"}), 500

    if likes_df is None or likes_df.empty:
        return jsonify({"success": False, "error": "Не удалось загрузить треки или плейлист пуст"}), 400

    # High-speed in-memory classification using zip
    artists_raw = likes_df["artist_raw"].tolist()
    titles_raw = likes_df["title_raw"].tolist()
    all_artists_list = likes_df["all_artists"].tolist()
    genres = [
        _classifier.classify_track(
            artist_raw=a,
            title_raw=t,
            all_artists=aa,
            allow_network=False,
        )[0]
        for a, t, aa in zip(artists_raw, titles_raw, all_artists_list)
    ]

    if "artists_count" not in likes_df.columns:
        if "all_artists" in likes_df.columns:
            likes_df["artists_count"] = likes_df["all_artists"].apply(lambda a: len(a) if isinstance(a, list) else 1)
        else:
            likes_df["artists_count"] = 1
    if "is_collab" not in likes_df.columns:
        likes_df["is_collab"] = likes_df["artists_count"] > 1

    likes_df["genre_cluster"] = genres
    _df_cache = likes_df

    # Persist synced collection and token to disk so it survives server restarts
    try:
        likes_df.to_pickle(SYNCED_CACHE_PATH)
        token_file = os.path.join(os.path.dirname(__file__), ".yandex_token")
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить кэш синхронизации/токен на диск: {e}", flush=True)

    return jsonify({
        "success": True,
        "tracks_synced": len(likes_df),
        "message": f"Синхронизировано {len(likes_df)} треков из Яндекс Музыки!"
    })


@app.route("/api/sync-likes/stream", methods=["GET", "POST"])
def sync_likes_stream():
    token = request.args.get("token", "").strip()
    if not token and request.is_json:
        data = request.get_json(silent=True) or {}
        token = data.get("token", "").strip()
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header.strip()
    if not token:
        token_file = os.path.join(os.path.dirname(__file__), ".yandex_token")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    token = f.read().strip()
            except Exception:
                pass

    if not token:
        return jsonify({"success": False, "error": "Токен авторизации (token) не указан"}), 400

    def generate_events():
        q: queue.Queue = queue.Queue()

        def worker():
            nonlocal token
            try:
                q.put({
                    "type": "progress",
                    "stage": "auth",
                    "percent": 2,
                    "current": 0,
                    "total": 0,
                    "message": "Подключение к Яндекс Музыке..."
                })

                client, user_info, err = yandex_api.login_yandex(token)
                if err or not client:
                    q.put({
                        "type": "error",
                        "stage": "error",
                        "percent": 0,
                        "message": err or "Недействительный токен Яндекс Музыки"
                    })
                    return

                user_title = user_info.get("full_name") or user_info.get("login") or "Пользователь"
                q.put({
                    "type": "progress",
                    "stage": "fetching_init",
                    "percent": 5,
                    "current": 0,
                    "total": 0,
                    "message": f"Авторизован как {user_title}. Запрос треков..."
                })

                def on_progress(current_pct: int, total_pct: int, msg: str):
                    scaled_pct = int(5 + (current_pct * 0.80))
                    q.put({
                        "type": "progress",
                        "stage": "fetching",
                        "percent": min(85, max(5, scaled_pct)),
                        "current": current_pct,
                        "total": total_pct,
                        "message": msg
                    })

                likes_df = yandex_api.fetch_user_likes_df(client, progress_callback=on_progress)
                if likes_df is None or likes_df.empty:
                    q.put({
                        "type": "error",
                        "stage": "error",
                        "percent": 0,
                        "message": "Не удалось загрузить треки или медиатека пуста"
                    })
                    return

                total_tracks = len(likes_df)
                q.put({
                    "type": "progress",
                    "stage": "classifying",
                    "percent": 88,
                    "current": total_tracks,
                    "total": total_tracks,
                    "message": f"Классификация жанров для {total_tracks:,} треков..."
                })

                artists_raw = likes_df["artist_raw"].tolist()
                titles_raw = likes_df["title_raw"].tolist()
                all_artists_list = likes_df["all_artists"].tolist()
                genres = [
                    _classifier.classify_track(
                        artist_raw=a,
                        title_raw=t,
                        all_artists=aa,
                        allow_network=False,
                    )[0]
                    for a, t, aa in zip(artists_raw, titles_raw, all_artists_list)
                ]

                if "artists_count" not in likes_df.columns:
                    if "all_artists" in likes_df.columns:
                        likes_df["artists_count"] = likes_df["all_artists"].apply(
                            lambda a: len(a) if isinstance(a, list) else 1
                        )
                    else:
                        likes_df["artists_count"] = 1
                if "is_collab" not in likes_df.columns:
                    likes_df["is_collab"] = likes_df["artists_count"] > 1

                likes_df["genre_cluster"] = genres

                global _df_cache
                _df_cache = likes_df

                try:
                    likes_df.to_pickle(SYNCED_CACHE_PATH)
                    token_path = os.path.join(os.path.dirname(__file__), ".yandex_token")
                    with open(token_path, "w", encoding="utf-8") as f:
                        f.write(token)
                except Exception as ex:
                    print(f"⚠️ Не удалось сохранить кэш: {ex}", flush=True)

                q.put({
                    "type": "complete",
                    "stage": "done",
                    "percent": 100,
                    "current": total_tracks,
                    "total": total_tracks,
                    "tracks_synced": total_tracks,
                    "message": f"Синхронизировано {total_tracks:,} треков из Яндекс Музыки!"
                })
            except Exception as e:
                q.put({
                    "type": "error",
                    "stage": "error",
                    "percent": 0,
                    "message": f"Ошибка синхронизации: {e}"
                })
            finally:
                q.put(None)

        worker_thread = threading.Thread(target=worker, daemon=True)
        worker_thread.start()

        while True:
            try:
                item = q.get(timeout=20)
                if item is None:
                    break
                event_name = item.get("type", "message")
                data_str = json.dumps(item, ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data_str}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(
        generate_events(),
        mimetype="text/event-stream",
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.route("/api/enrich-genres/status", methods=["GET"])
def enrich_genres_status():
    cache_db = _classifier.db_path
    unresolved_count = 0
    try:
        import sqlite3
        with sqlite3.connect(cache_db, timeout=10.0) as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM artist_cache WHERE source = 'unresolved'")
            row = cur.fetchone()
            unresolved_count = row[0] if row else 0
    except Exception as e:
        print(f"⚠️ Ошибка получения статуса AI: {e}", flush=True)

    # Dynamic key reload from environment or local config
    if not _ai_classifier.gemini_key or not _ai_classifier.groq_key:
        g_k, q_k = _load_keys()
        if not _ai_classifier.gemini_key and g_k:
            _ai_classifier.gemini_key = g_k
        if not _ai_classifier.groq_key and q_k:
            _ai_classifier.groq_key = q_k

    # Header / query param override support
    custom_gemini = request.headers.get("X-Gemini-Key") or request.args.get("gemini_key")
    custom_groq = request.headers.get("X-Groq-Key") or request.args.get("groq_key")
    if custom_gemini:
        _ai_classifier.gemini_key = custom_gemini.strip()
    if custom_groq:
        _ai_classifier.groq_key = custom_groq.strip()

    has_gemini = bool(_ai_classifier.gemini_key)
    has_groq = bool(_ai_classifier.groq_key)

    return jsonify({
        "success": True,
        "unresolved_count": unresolved_count,
        "is_configured": has_gemini or has_groq,
        "has_gemini": has_gemini,
        "has_groq": has_groq,
    })


@app.route("/api/enrich-genres/stream", methods=["GET", "POST"])
def enrich_genres_stream():
    cache_db = _classifier.db_path

    # Dynamic key reload & custom key overrides
    if not _ai_classifier.gemini_key or not _ai_classifier.groq_key:
        g_k, q_k = _load_keys()
        if not _ai_classifier.gemini_key and g_k:
            _ai_classifier.gemini_key = g_k
        if not _ai_classifier.groq_key and q_k:
            _ai_classifier.groq_key = q_k

    custom_gemini = request.headers.get("X-Gemini-Key") or request.args.get("gemini_key")
    custom_groq = request.headers.get("X-Groq-Key") or request.args.get("groq_key")
    if custom_gemini:
        _ai_classifier.gemini_key = custom_gemini.strip()
    if custom_groq:
        _ai_classifier.groq_key = custom_groq.strip()

    def generate_events():
        q: queue.Queue = queue.Queue()

        def worker():
            try:
                import sqlite3
                targets = []
                with sqlite3.connect(cache_db, timeout=20.0) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT artist_key, artist_name FROM artist_cache WHERE source = 'unresolved'")
                    targets = cur.fetchall()

                total = len(targets)
                if total == 0:
                    q.put({
                        "type": "done",
                        "percent": 100,
                        "current": 0,
                        "total": 0,
                        "message": "Все артисты уже классифицированы нейросетью!"
                    })
                    return

                q.put({
                    "type": "progress",
                    "percent": 2,
                    "current": 0,
                    "total": total,
                    "message": f"Найдено {total:,} артистов для AI-анализа. Запуск..."
                })

                artist_tracks = {}
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

                batch_size = 35
                processed = 0
                saved_total = 0

                for i in range(0, total, batch_size):
                    chunk = targets[i : i + batch_size]
                    items_payload = []
                    for k, name in chunk:
                        trks = artist_tracks.get(k, [])
                        items_payload.append({
                            "artist": name,
                            "tracks": trks[:4] if trks else [],
                        })

                    pct = int(5 + ((i / total) * 90))
                    q.put({
                        "type": "progress",
                        "percent": pct,
                        "current": processed,
                        "total": total,
                        "message": f"AI-анализ: обработано {processed}/{total} артистов..."
                    })

                    try:
                        results, provider = _ai_classifier.classify_batch(items_payload)
                        saved = _ai_classifier.save_ai_results_to_sqlite(cache_db, results)
                        saved_total += saved
                    except Exception as ex:
                        print(f"⚠️ Ошибка пакета AI: {ex}", flush=True)

                    processed += len(chunk)
                    time.sleep(1.2)

                _classifier.reload_memory_cache()
                global _df_cache
                if _df_cache is not None and not _df_cache.empty:
                    artists_raw = _df_cache["artist_raw"].tolist()
                    titles_raw = _df_cache["title_raw"].tolist()
                    all_artists_list = _df_cache["all_artists"].tolist()
                    _df_cache["genre_cluster"] = [
                        _classifier.classify_track(a, t, aa, allow_network=False)[0]
                        for a, t, aa in zip(artists_raw, titles_raw, all_artists_list)
                    ]
                    try:
                        _df_cache.to_pickle(SYNCED_CACHE_PATH)
                    except Exception:
                        pass

                q.put({
                    "type": "done",
                    "percent": 100,
                    "current": total,
                    "total": total,
                    "total_enriched": saved_total,
                    "message": f"AI-классификация завершена! Обработано {saved_total} артистов, медиатека обновлена."
                })
            except Exception as e:
                q.put({
                    "type": "error",
                    "percent": 0,
                    "message": f"Ошибка AI-классификации: {e}"
                })
            finally:
                q.put(None)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            try:
                item = q.get(timeout=25)
                if item is None:
                    break
                event_name = item.get("type", "message")
                data_str = json.dumps(item, ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data_str}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(
        generate_events(),
        mimetype="text/event-stream",
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.route("/api/export-playlist", methods=["POST"])
def export_playlist():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "error": "Требуется токен авторизации (token)"}), 400

    preset = data.get("preset", "genre").strip().lower()
    genre = data.get("genre", "").strip()
    custom_title = data.get("title", "").strip()
    
    limit_raw = data.get("limit", 100)
    try:
        limit_val = int(limit_raw)
    except (ValueError, TypeError):
        limit_val = 100

    # 1. Проверяем авторизацию пользователя
    client, user_info, err = yandex_api.login_yandex(token)
    if err or not client:
        return jsonify({"success": False, "error": err or "Ошибка авторизации в Яндекс Музыке"}), 401

    # 2. Получаем текущую коллекцию
    df = get_dataset()
    if df.empty:
        return jsonify({"success": False, "error": "Медиатека пуста или ещё не загружена"}), 400

    if "track_id" not in df.columns or df["track_id"].dropna().empty:
        return jsonify({
            "success": False,
            "error": "В текущей медиатеке отсутствуют ID треков Яндекс Музыки. Сначала выполните синхронизацию медиатеки (кнопка «Синхронизировать лайки» в профиле)."
        }), 400

    # Отбираем валидные треки с track_id
    df_valid = df[df["track_id"].notna() & (df["track_id"].astype(str) != "")].copy()
    if df_valid.empty:
        return jsonify({
            "success": False,
            "error": "Не найдено треков с валидными ID. Пожалуйста, выполните синхронизацию лайков."
        }), 400

    # 3. Фильтрация по пресетам
    default_title = "Умный плейлист"
    if preset == "genre":
        if not genre or genre.lower() in ("все", "all"):
            return jsonify({"success": False, "error": "Для пресета 'genre' необходимо указать конкретный жанр"}), 400
        filtered = df_valid[df_valid["genre_cluster"] == genre]
        default_title = f"⚡ {genre} — Подборка"

    elif preset == "collab":
        filtered = df_valid[df_valid["is_collab"]]
        default_title = "🤝 Фитотека — Все коллаборации"

    elif preset == "solo":
        filtered = df_valid[~df_valid["is_collab"]]
        default_title = "🎙️ Соло — Чистый вокал"

    elif preset == "gems":
        # Артисты, у которых не более 2 треков в медиатеке
        artist_counts = df_valid["primary_artist"].value_counts()
        rare_artists = set(artist_counts[artist_counts <= 2].index)
        filtered = df_valid[df_valid["primary_artist"].isin(rare_artists)]
        default_title = "💎 Скрытые жемчужины — Редкие артисты"

    elif preset == "golden_era":
        # Самые первые добавленные треки (наибольший id в порядке лайков)
        filtered = df_valid.sort_values(by="id", ascending=False)
        default_title = "⏳ Золотая эра — Первые лайки"

    else:
        return jsonify({
            "success": False,
            "error": f"Неизвестный пресет '{preset}'. Доступные: genre, collab, solo, gems, golden_era"
        }), 400

    if filtered.empty:
        return jsonify({"success": False, "error": "По выбранному фильтру не найдено подходящих треков"}), 404

    # Если limit_val <= 0, экспортируем всю выборку целиком (без лимита)
    if limit_val > 0:
        subset = filtered.head(limit_val)
    else:
        subset = filtered

    final_title = custom_title if custom_title else default_title

    # 4. Подготавливаем структуру треков для yandex_api.create_remote_playlist
    track_dicts = []
    for _, row in subset.iterrows():
        track_dicts.append({
            "track_id": str(row["track_id"]),
            "album_id": str(row.get("album_id", "")) if pd.notna(row.get("album_id")) else ""
        })

    # 5. Создаём удалённый плейлист в аккаунте Яндекс Музыки
    success, msg, url = yandex_api.create_remote_playlist(client, final_title, track_dicts)
    if not success:
        return jsonify({"success": False, "error": msg}), 500

    return jsonify({
        "success": True,
        "message": msg,
        "playlist_title": final_title,
        "playlist_url": url,
        "tracks_count": len(track_dicts),
    })


@app.route("/api/artist", methods=["GET"])
def get_artist():
    artist_name = request.args.get("name", "").strip()
    if not artist_name:
        return jsonify({"error": "Параметр 'name' обязателен"}), 400

    df = get_dataset()
    if df.empty:
        return jsonify({"error": "Медиатека пуста"}), 404

    target_lower = artist_name.lower()

    def is_artist_match(row):
        artists = row.get("all_artists")
        if isinstance(artists, list):
            if any(a.lower() == target_lower for a in artists):
                return True
        pri = str(row.get("primary_artist", "")).lower()
        if pri == target_lower:
            return True
        raw = str(row.get("artist_raw", "")).lower()
        return raw == target_lower

    matched_df = df[df.apply(is_artist_match, axis=1)]
    if matched_df.empty:
        return jsonify({"error": f"Артист '{artist_name}' не найден в медиатеке"}), 404

    total_matched = len(matched_df)
    total_library = len(df)
    library_share_pct = round((total_matched / total_library) * 100, 2) if total_library > 0 else 0.0

    total_dur_sec = int(matched_df["duration_sec"].sum())
    total_dur_fmt = format_seconds(total_dur_sec)
    avg_dur_sec = int(matched_df["duration_sec"].mean()) if total_matched > 0 else 0

    solo_count = int((~matched_df["is_collab"]).sum())
    collab_count = int(matched_df["is_collab"].sum())

    genre_counts = matched_df["genre_cluster"].value_counts().to_dict()
    dominant_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "Unknown"

    genres_breakdown = [
        {
            "genre": g,
            "count": int(c),
            "percent": round((c / total_matched) * 100, 1),
            "color": CLUSTER_COLORS.get(g, "#FFFFFF"),
        }
        for g, c in genre_counts.items()
    ]

    # Коллабораторы
    collab_dict = {}
    for artists in matched_df["all_artists"]:
        if isinstance(artists, list):
            for a in artists:
                if a.lower() != target_lower:
                    collab_dict[a] = collab_dict.get(a, 0) + 1

    top_collabs = sorted(
        [{"artist": a, "count": c} for a, c in collab_dict.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:12]

    # Общий ранг артиста в библиотеке
    all_artists_flat = []
    for artists in df["all_artists"]:
        if isinstance(artists, list):
            all_artists_flat.extend(artists)
    rank_series = pd.Series(all_artists_flat).value_counts()
    rank = None
    for idx, (art, _) in enumerate(rank_series.items()):
        if art.lower() == target_lower:
            rank = idx + 1
            break

    # Список треков артиста
    tracks = []
    for _, row in matched_df.iterrows():
        title = row.get("title_raw", "")
        artist = row.get("artist_raw", "")
        yandex_url = row.get("yandex_url") or f"https://music.yandex.ru/search?text={urllib.parse.quote_plus(artist + ' - ' + title)}"
        tracks.append({
            "id": int(row.get("id", 0)),
            "title": title,
            "artist": artist,
            "artists": row.get("all_artists", []),
            "duration_sec": int(row.get("duration_sec", 0)),
            "duration_fmt": row.get("duration_fmt", "0:00"),
            "genre": row.get("genre_cluster", CLUSTER_OTHER),
            "genre_color": CLUSTER_COLORS.get(row.get("genre_cluster", ""), "#FFFFFF"),
            "is_collab": bool(row.get("is_collab", False)),
            "cover_uri": row.get("cover_uri", ""),
            "yandex_url": yandex_url,
        })

    canonical_name = matched_df.iloc[0]["primary_artist"] if target_lower == matched_df.iloc[0]["primary_artist"].lower() else artist_name
    encoded_artist_query = urllib.parse.quote_plus(canonical_name)
    artist_yandex_url = f"https://music.yandex.ru/search?text={encoded_artist_query}&type=artists"

    return jsonify({
        "artist": canonical_name,
        "rank": rank,
        "total_tracks": total_matched,
        "library_share_percent": library_share_pct,
        "total_duration_sec": total_dur_sec,
        "total_duration_fmt": total_dur_fmt,
        "avg_duration_sec": avg_dur_sec,
        "solo_count": solo_count,
        "collab_count": collab_count,
        "dominant_genre": dominant_genre,
        "dominant_color": CLUSTER_COLORS.get(dominant_genre, "#FFCC00"),
        "genres": genres_breakdown,
        "top_collaborators": top_collabs,
        "tracks": tracks,
        "yandex_url": artist_yandex_url,
    })


@app.route("/api/collaborations-graph", methods=["GET"])
def get_collaborations_graph():
    df = get_dataset()
    if df.empty:
        return jsonify({
            "nodes": [],
            "edges": [],
            "stats": {"total_nodes": 0, "total_edges": 0, "focus_artist": None}
        })

    try:
        min_collabs = int(request.args.get("min_collabs", 1))
    except (ValueError, TypeError):
        min_collabs = 1

    try:
        limit_nodes = int(request.args.get("limit_nodes", 60))
    except (ValueError, TypeError):
        limit_nodes = 60

    focus_artist = request.args.get("focus_artist", "").strip() or None

    full_graph = build_collaborations_graph(
        df,
        min_collaborations=min_collabs,
        focus_artist=focus_artist,
    )

    if full_graph.number_of_nodes() == 0:
        return jsonify({
            "nodes": [],
            "edges": [],
            "stats": {"total_nodes": 0, "total_edges": 0, "focus_artist": focus_artist}
        })

    if not focus_artist and full_graph.number_of_nodes() > limit_nodes:
        top_candidates = sorted(
            full_graph.nodes(),
            key=lambda n: (full_graph.degree(n), full_graph.nodes[n].get("count", 0)),
            reverse=True
        )[:limit_nodes]
        subg = full_graph.subgraph(top_candidates).copy()
        connected = [n for n in subg.nodes() if subg.degree(n) > 0]
        graph = subg.subgraph(connected).copy() if connected else subg
    else:
        graph = full_graph

    if graph.number_of_nodes() == 0:
        return jsonify({
            "nodes": [],
            "edges": [],
            "stats": {"total_nodes": 0, "total_edges": 0, "focus_artist": focus_artist}
        })

    pos = nx.spring_layout(graph, k=0.45, iterations=50, seed=42)

    artist_genres = {}
    if "is_collab" in df.columns and "all_artists" in df.columns:
        collab_subset = df[df["is_collab"]]
        if not collab_subset.empty:
            exploded = collab_subset.explode("all_artists")
            grouped = (
                exploded.groupby(["all_artists", "genre_cluster"])
                .size()
                .unstack(fill_value=0)
            )
            for art in graph.nodes():
                if art in grouped.index:
                    artist_genres[art] = grouped.loc[art].idxmax()

    degrees = dict(graph.degree())
    nodes_list = []
    for node, data in graph.nodes(data=True):
        count = int(data.get("count", 1))
        deg = int(degrees.get(node, 0))
        coords = pos.get(node, [0.0, 0.0])
        dom_genre = artist_genres.get(node, CLUSTER_OTHER)
        color = CLUSTER_COLORS.get(dom_genre, "#00E5FF")

        nodes_list.append({
            "id": node,
            "name": node,
            "tracks_count": count,
            "degree": deg,
            "dominant_genre": dom_genre,
            "color": color,
            "x": round(float(coords[0]), 4),
            "y": round(float(coords[1]), 4),
        })

    edges_list = []
    for u, v, data in graph.edges(data=True):
        edges_list.append({
            "source": u,
            "target": v,
            "weight": int(data.get("weight", 1)),
        })

    nodes_list.sort(key=lambda n: n["tracks_count"], reverse=True)

    return jsonify({
        "nodes": nodes_list,
        "edges": edges_list,
        "stats": {
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "min_collaborations": min_collabs,
            "focus_artist": focus_artist,
        }
    })


@app.route("/api/track-stream/<track_id>", methods=["GET"])
def track_stream(track_id):
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
    if not token:
        token_file = os.path.join(os.path.dirname(__file__), ".yandex_token")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    token = f.read().strip()
            except Exception:
                pass

    info = yandex_api.get_track_stream_url(track_id, token)
    if not info:
        return jsonify({
            "success": False,
            "error": f"Не удалось получить аудио-поток для трека {track_id}"
        }), 404

    return jsonify({"success": True, **info})


@app.route("/api/duplicates", methods=["GET"])
def get_duplicates():
    df = get_dataset()
    if df.empty:
        return jsonify({
            "success": True,
            "total_duplicates": 0,
            "duplicate_groups_count": 0,
            "total_redundant_time_sec": 0,
            "total_redundant_time_fmt": "0:00",
            "groups": []
        })

    def normalize_title(title: str) -> str:
        t = str(title).strip()
        t = re.sub(
            r"[\(\[\{].*?(?:remaster|deluxe|version|bonus|edit|mix|live|remix|acoustic|instrumental|feat|ft\.).*?[\)\]\}]",
            "",
            t,
            flags=re.IGNORECASE,
        )
        t = re.sub(r"[\W_]+", " ", t).strip().lower()
        return t

    temp_df = df.copy()
    temp_df["norm_title"] = temp_df["title_raw"].apply(normalize_title)
    temp_df["norm_artist"] = temp_df["primary_artist"].astype(str).str.strip().str.lower()

    valid_mask = (temp_df["norm_title"] != "") & (temp_df["norm_artist"] != "")
    subset = temp_df[valid_mask]

    grouped = subset.groupby(["norm_artist", "norm_title"]).filter(lambda x: len(x) > 1)
    if grouped.empty:
        return jsonify({
            "success": True,
            "total_duplicates": 0,
            "duplicate_groups_count": 0,
            "total_redundant_time_sec": 0,
            "total_redundant_time_fmt": "0:00",
            "groups": []
        })

    groups_list = []
    total_redundant = 0
    total_redundant_sec = 0

    for (artist_key, title_key), grp in grouped.groupby(["norm_artist", "norm_title"]):
        sorted_grp = grp.sort_values(by="id", ascending=True)
        tracks_in_group = []
        is_first = True

        for _, row in sorted_grp.iterrows():
            t_id = str(row.get("id", ""))
            yandex_url = (
                f"https://music.yandex.ru/track/{t_id}"
                if t_id and t_id.isdigit() and int(t_id) > 1000
                else None
            )
            cover = row.get("cover_uri", None)
            if cover and isinstance(cover, str) and "%%" in cover:
                cover = "https://" + cover.replace("%%", "200x200")
            elif not cover:
                cover = None

            dur_sec = int(row.get("duration_sec", 0))

            tracks_in_group.append({
                "id": t_id,
                "title": str(row.get("title_raw", "")),
                "artist": str(row.get("primary_artist", "")),
                "all_artists": row.get("all_artists", []),
                "duration_sec": dur_sec,
                "duration_fmt": str(row.get("duration_fmt", "")),
                "genre_cluster": str(row.get("genre_cluster", CLUSTER_OTHER)),
                "cover_url": cover,
                "yandex_url": yandex_url,
                "is_original": is_first,
            })
            if not is_first:
                total_redundant += 1
                total_redundant_sec += dur_sec
            is_first = False

        canonical_artist = sorted_grp.iloc[0].get("primary_artist", artist_key)
        canonical_title = sorted_grp.iloc[0].get("title_raw", title_key)

        groups_list.append({
            "key": f"{artist_key} - {title_key}",
            "artist": canonical_artist,
            "title": canonical_title,
            "count": len(tracks_in_group),
            "tracks": tracks_in_group,
        })

    groups_list.sort(key=lambda g: g["count"], reverse=True)

    return jsonify({
        "success": True,
        "total_duplicates": total_redundant,
        "duplicate_groups_count": len(groups_list),
        "total_redundant_time_sec": total_redundant_sec,
        "total_redundant_time_fmt": format_seconds(total_redundant_sec),
        "groups": groups_list,
    })


@app.route("/api/audio-features", methods=["GET"])
def get_audio_features():
    df = get_dataset()
    if df.empty:
        return jsonify({"success": False, "error": "No tracks loaded"}), 400

    total_tracks = len(df)
    avg_dur_sec = int(df["duration_sec"].mean()) if total_tracks > 0 else 0
    genre_counts = df["genre_cluster"].value_counts().to_dict()

    energy_weights = {
        CLUSTER_HEAVY_METAL: 0.96,
        CLUSTER_DUBSTEP_EDM: 0.94,
        CLUSTER_PHONK_MEMPHIS: 0.89,
        CLUSTER_HIPHOP_TRAP: 0.73,
        CLUSTER_ROCK_ALTERNATIVE: 0.69,
        CLUSTER_OTHER: 0.50,
    }
    weighted_energy = sum(
        genre_counts.get(g, 0) * energy_weights.get(g, 0.5) for g in genre_counts
    )
    overall_energy_pct = round((weighted_energy / total_tracks) * 100, 1) if total_tracks > 0 else 50.0

    fast_count = int(genre_counts.get(CLUSTER_DUBSTEP_EDM, 0) * 0.35 + genre_counts.get(CLUSTER_HEAVY_METAL, 0) * 0.40)
    driving_count = int(genre_counts.get(CLUSTER_PHONK_MEMPHIS, 0) * 0.85 + genre_counts.get(CLUSTER_DUBSTEP_EDM, 0) * 0.55 + genre_counts.get(CLUSTER_HIPHOP_TRAP, 0) * 0.50)
    mid_count = int(genre_counts.get(CLUSTER_ROCK_ALTERNATIVE, 0) * 0.75 + genre_counts.get(CLUSTER_HIPHOP_TRAP, 0) * 0.40 + genre_counts.get(CLUSTER_OTHER, 0) * 0.40)
    chill_count = max(0, total_tracks - (fast_count + driving_count + mid_count))

    collab_ratio = round((int(df["is_collab"].sum()) / total_tracks) * 100, 1) if total_tracks > 0 else 0.0

    return jsonify({
        "success": True,
        "total_tracks": total_tracks,
        "energy_score_percent": overall_energy_pct,
        "energy_label": "Максимальный драйв 🔥" if overall_energy_pct > 80 else ("Высокая энергия ⚡" if overall_energy_pct > 65 else "Сбалансированная 🎧"),
        "average_duration_sec": avg_dur_sec,
        "average_duration_fmt": format_seconds(avg_dur_sec),
        "collab_ratio_percent": collab_ratio,
        "bpm_profile": [
            {"range": "150–180+ BPM", "label": "Скоростной / Рейв", "count": fast_count, "percent": round((fast_count / total_tracks) * 100, 1), "color": "#00E5FF"},
            {"range": "130–150 BPM", "label": "Драйв / Фонк & Дабстеп", "count": driving_count, "percent": round((driving_count / total_tracks) * 100, 1), "color": "#D500F9"},
            {"range": "100–130 BPM", "label": "Кач / Рок & Трэп", "count": mid_count, "percent": round((mid_count / total_tracks) * 100, 1), "color": "#FFD600"},
            {"range": "< 100 BPM", "label": "Чилл / Эмбиент", "count": chill_count, "percent": round((chill_count / total_tracks) * 100, 1), "color": "#00E676"},
        ],
        "loudness_profile": {
            "heavy_lufs_percent": round(((genre_counts.get(CLUSTER_HEAVY_METAL, 0) + genre_counts.get(CLUSTER_DUBSTEP_EDM, 0) + genre_counts.get(CLUSTER_PHONK_MEMPHIS, 0)) / total_tracks) * 100, 1),
            "standard_lufs_percent": round(((genre_counts.get(CLUSTER_HIPHOP_TRAP, 0) + genre_counts.get(CLUSTER_ROCK_ALTERNATIVE, 0)) / total_tracks) * 100, 1),
            "acoustic_lufs_percent": round((genre_counts.get(CLUSTER_OTHER, 0) / total_tracks) * 100, 1),
        }
    })


@app.route("/api/collaborations-graph/export-html", methods=["GET"])
def export_collaborations_graph_html():
    df = get_dataset()
    if df.empty or "is_collab" not in df.columns:
        return "<h3>Нет данных для построения графа</h3>", 400

    min_collabs = int(request.args.get("min_collabs", 1))
    limit_nodes = int(request.args.get("limit_nodes", 75))

    full_graph = build_collaborations_graph(df, min_collaborations=min_collabs)
    if full_graph.number_of_nodes() == 0:
        return "<h3>Граф пуст при данных фильтрах</h3>", 400

    if full_graph.number_of_nodes() > limit_nodes:
        top_candidates = sorted(
            full_graph.nodes(),
            key=lambda n: (full_graph.degree(n), full_graph.nodes[n].get("count", 0)),
            reverse=True
        )[:limit_nodes]
        subg = full_graph.subgraph(top_candidates).copy()
        connected = [n for n in subg.nodes() if subg.degree(n) > 0]
        graph = subg.subgraph(connected).copy() if connected else subg
    else:
        graph = full_graph

    # Determine dominant genres
    artist_genres = {}
    collab_subset = df[df["is_collab"]]
    if not collab_subset.empty:
        exploded = collab_subset.explode("all_artists")
        grouped = (
            exploded.groupby(["all_artists", "genre_cluster"])
            .size()
            .unstack(fill_value=0)
        )
        for art in graph.nodes():
            if art in grouped.index:
                artist_genres[art] = grouped.loc[art].idxmax()

    vis_nodes = []
    for node, data in graph.nodes(data=True):
        count = int(data.get("count", 1))
        deg = int(graph.degree(node))
        dom_genre = artist_genres.get(node, CLUSTER_OTHER)
        color = CLUSTER_COLORS.get(dom_genre, "#00E5FF")
        vis_nodes.append({
            "id": node,
            "label": node,
            "value": count,
            "title": f"<b>{node}</b><br>Жанр: {dom_genre}<br>Треков в коллекции: {count}<br>Совместных связей: {deg}",
            "color": {
                "background": color,
                "border": "#ffffff",
                "highlight": {"background": "#ffffff", "border": color}
            },
            "font": {"color": "#ffffff", "face": "Inter, sans-serif", "size": 14}
        })

    vis_edges = []
    for u, v, data in graph.edges(data=True):
        weight = int(data.get("weight", 1))
        vis_edges.append({
            "from": u,
            "to": v,
            "value": weight,
            "title": f"Совместных треков: {weight}",
            "color": {"color": "rgba(255, 255, 255, 0.25)", "highlight": "#00E5FF"}
        })

    nodes_json = json.dumps(vis_nodes, ensure_ascii=False)
    edges_json = json.dumps(vis_edges, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Карта коллабораций артистов — Яндекс Музыка</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0B0E14;
      color: #F0F4F8;
      font-family: 'Inter', sans-serif;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
    }}
    #header {{
      position: absolute;
      top: 16px;
      left: 20px;
      z-index: 10;
      background: rgba(18, 24, 38, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      padding: 16px 24px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }}
    h1 {{ font-size: 20px; font-weight: 800; background: linear-gradient(135deg, #00E5FF, #D500F9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    p.subtitle {{ font-size: 13px; color: #94A3B8; margin-top: 4px; }}
    #legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      z-index: 10;
      background: rgba(18, 24, 38, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      padding: 14px 20px;
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; box-shadow: 0 0 8px currentColor; }}
    #network {{ width: 100vw; height: 100vh; }}
  </style>
</head>
<body>
  <div id="header">
    <h1>🕸️ Карта коллабораций артистов</h1>
    <p class="subtitle">Интерактивный граф соавторства • Узлов: {len(vis_nodes)} • Связей: {len(vis_edges)}</p>
  </div>

  <div id="legend">
    <div class="legend-item"><span class="legend-dot" style="background:#00E5FF; color:#00E5FF"></span>Dubstep & EDM</div>
    <div class="legend-item"><span class="legend-dot" style="background:#FF3D00; color:#FF3D00"></span>Heavy & Metal</div>
    <div class="legend-item"><span class="legend-dot" style="background:#D500F9; color:#D500F9"></span>Phonk & Memphis</div>
    <div class="legend-item"><span class="legend-dot" style="background:#FFD600; color:#FFD600"></span>Hip-Hop & Trap</div>
    <div class="legend-item"><span class="legend-dot" style="background:#00E676; color:#00E676"></span>Rock & Alternative</div>
  </div>

  <div id="network"></div>

  <script type="text/javascript">
    const container = document.getElementById('network');
    const data = {{
      nodes: new vis.DataSet({nodes_json}),
      edges: new vis.DataSet({edges_json})
    }};
    const options = {{
      nodes: {{
        shape: 'dot',
        scaling: {{ min: 14, max: 40 }},
        borderWidth: 2,
        shadow: {{ enabled: true, color: 'rgba(0,0,0,0.5)', size: 10 }}
      }},
      edges: {{
        smooth: {{ type: 'continuous' }},
        scaling: {{ min: 1.5, max: 8 }}
      }},
      physics: {{
        stabilization: true,
        barnesHut: {{
          gravitationalConstant: -18000,
          springConstant: 0.04,
          springLength: 95
        }}
      }},
      interaction: {{ hover: true, tooltipDelay: 100, zoomView: true, dragView: true }}
    }};
    const network = new vis.Network(container, data, options);
  </script>
</body>
</html>"""

    return Response(
        html_content,
        mimetype="text/html",
        headers={"Content-Disposition": "attachment; filename=collaborations_graph.html"}
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    print("=" * 60, flush=True)
    print(" 🚀 MUSIC ANALYTICS FLUTTER REST API", flush=True)
    print(f" 🌐 Локально:    http://{host}:{port}", flush=True)
    print(f" 📱 Для Android: http://10.0.2.2:{port} (эмулятор) или локальный Wi-Fi IP", flush=True)
    print("=" * 60, flush=True)
    app.run(host=host, port=port, debug=False)

