import math
import os
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd

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
    format_seconds,
    load_playlist,
)
import yandex_api

app = Flask(__name__)
CORS(app)

DEFAULT_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "Мне нравится_965180470_20260915_213456.txt"
)

# Global in-memory cache
_df_cache: Optional[pd.DataFrame] = None
_classifier = GenreClassifier()

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
    num_segments = 8
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
    page = max(1, int(request.args.get("page", 1)))
    limit = max(1, min(100, int(request.args.get("limit", 40))))

    filtered = df

    if genre_filter and genre_filter.lower() != "all":
        filtered = filtered[filtered["genre_cluster"] == genre_filter]

    if query:
        filtered = filtered[
            filtered["title_raw"].str.lower().str.contains(query, na=False)
            | filtered["artist_raw"].str.lower().str.contains(query, na=False)
        ]

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
        yandex_url = f"https://music.yandex.ru/search?text={yandex_query}"

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
    res = yandex_api.request_yandex_device_code()
    if res.get("success"):
        return jsonify(res)
    return jsonify(res), 400


@app.route("/api/auth/poll-token", methods=["POST"])
def auth_poll_token():
    data = request.get_json(silent=True) or {}
    device_code = data.get("device_code", "").strip()
    if not device_code:
        return jsonify({"success": False, "error": "device_code is required"}), 400

    res = yandex_api.poll_yandex_device_token(device_code)
    return jsonify(res)


@app.route("/api/sync-likes", methods=["POST"])
def sync_likes():
    global _df_cache
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "error": "token is required"}), 400

    likes_df, err = yandex_api.fetch_user_likes_df(token)
    if err:
        return jsonify({"success": False, "error": err}), 400

    # Classify fresh tracks using cached classifier
    genres: List[str] = []
    for _, row in likes_df.iterrows():
        cluster, _ = _classifier.classify_track(
            artist_raw=row.get("artist_raw", ""),
            title_raw=row.get("title_raw", ""),
            all_artists=row.get("all_artists", []),
            allow_network=False,
        )
        genres.append(cluster)

    likes_df["genre_cluster"] = genres
    _df_cache = likes_df

    return jsonify({
        "success": True,
        "tracks_synced": len(likes_df),
        "message": f"Синхронизировано {len(likes_df)} треков из Яндекс Музыки!"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    print("=" * 60, flush=True)
    print(" 🚀 MUSIC ANALYTICS FLUTTER REST API", flush=True)
    print(f" 🌐 Локально:    http://{host}:{port}", flush=True)
    print(f" 📱 Для Android: http://10.0.2.2:{port} (эмулятор) или локальный Wi-Fi IP", flush=True)
    print("=" * 60, flush=True)
    app.run(host=host, port=port, debug=False)

