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
SYNCED_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), "synced_likes.pkl"
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
            "/api/export-playlist",
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

    # Persist synced collection to disk so it survives server restarts
    try:
        likes_df.to_pickle(SYNCED_CACHE_PATH)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить кэш синхронизации на диск: {e}", flush=True)

    return jsonify({
        "success": True,
        "tracks_synced": len(likes_df),
        "message": f"Синхронизировано {len(likes_df)} треков из Яндекс Музыки!"
    })


@app.route("/api/export-playlist", methods=["POST"])
def export_playlist():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "error": "Требуется токен авторизации (token)"}), 400

    preset = data.get("preset", "genre").strip().lower()
    genre = data.get("genre", "").strip()
    custom_title = data.get("title", "").strip()
    limit = max(1, min(300, int(data.get("limit", 100))))

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

    subset = filtered.head(limit)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    print("=" * 60, flush=True)
    print(" 🚀 MUSIC ANALYTICS FLUTTER REST API", flush=True)
    print(f" 🌐 Локально:    http://{host}:{port}", flush=True)
    print(f" 📱 Для Android: http://10.0.2.2:{port} (эмулятор) или локальный Wi-Fi IP", flush=True)
    print("=" * 60, flush=True)
    app.run(host=host, port=port, debug=False)

