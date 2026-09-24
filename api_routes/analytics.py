import math
import re
import urllib.parse
from typing import Any, Dict, List
from flask import Blueprint, jsonify, request
import pandas as pd

from api_routes.state import (
    CLUSTER_COLORS,
    CLUSTER_ICONS,
    CLUSTER_OTHER,
    get_dataset,
)
from genre_classifier import (
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
)
from parser import calculate_timeline_segments, format_seconds

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/overview", methods=["GET"])
def get_overview():
    df = get_dataset()
    if df.empty:
        return jsonify({"error": "No tracks loaded"}), 404

    all_artists = df.explode("all_artists")["all_artists"]
    total_sec = int(df["duration_sec"].sum())
    avg_sec = int(df["duration_sec"].mean()) if len(df) > 0 else 0
    collab_count = int(df["is_collab"].sum()) if "is_collab" in df.columns else 0

    top_artists = [
        {"artist": str(a), "count": int(c)}
        for a, c in all_artists.value_counts().head(20).items()
    ]
    collab_top = (
        [
            {"artist": str(a), "count": int(c)}
            for a, c in df[df["is_collab"]].explode("all_artists")["all_artists"].value_counts().head(10).items()
        ]
        if "is_collab" in df.columns
        else []
    )

    return jsonify({
        "total_tracks": len(df),
        "unique_artists": all_artists.nunique(),
        "total_duration_sec": total_sec,
        "total_duration_fmt": format_seconds(total_sec),
        "avg_duration_sec": avg_sec,
        "avg_duration_fmt": f"{avg_sec // 60}:{avg_sec % 60:02d}",
        "solo_tracks": len(df) - collab_count,
        "collab_tracks": collab_count,
        "collab_percent": round((collab_count / len(df) * 100), 1) if len(df) > 0 else 0,
        "top_artists": top_artists,
        "top_collab_artists": collab_top,
    })


@analytics_bp.route("/api/genres", methods=["GET"])
def get_genres():
    df = get_dataset()
    if df.empty or "genre_cluster" not in df.columns:
        return jsonify({"genres": [], "total_classified": 0})

    counts = df["genre_cluster"].value_counts()
    total = len(df)
    genres = [
        {
            "name": g,
            "count": int(c),
            "percent": round((c / total * 100), 1),
            "color": CLUSTER_COLORS.get(g, "#888888"),
            "icon": CLUSTER_ICONS.get(g, "music_note"),
        }
        for g, c in counts.items()
    ]
    return jsonify({"genres": genres, "total_classified": total})


@analytics_bp.route("/api/timeline", methods=["GET"])
def get_timeline():
    df = get_dataset()
    if df.empty:
        return jsonify({"segments": []})

    segments_n = max(4, min(16, int(request.args.get("segments", 8))))
    top_n = max(3, min(12, int(request.args.get("top_n", 6))))

    df_chrono = df.sort_values(by="id", ascending=True)
    t_df = calculate_timeline_segments(df_chrono, num_segments=segments_n, top_n_artists=top_n)

    grouped = t_df.groupby("segment")
    segments = []
    for seg_name, grp in grouped:
        segments.append({
            "segment": seg_name,
            "artists": [
                {"artist": row["artist"], "count": int(row["count"])}
                for _, row in grp.iterrows()
            ],
        })
    return jsonify({"segments": segments})


def _filter_and_sort_tracks(df: pd.DataFrame) -> pd.DataFrame:
    q = request.args.get("q", "").strip().lower()
    genre = request.args.get("genre", "").strip()
    collab = request.args.get("collab", "all").strip().lower()
    sort_by = request.args.get("sort", "newest").strip().lower()

    filtered = df
    if genre and genre.lower() not in ("all", "все"):
        filtered = filtered[filtered["genre_cluster"] == genre]
    if collab == "solo":
        filtered = filtered[~filtered["is_collab"]]
    elif collab == "collab":
        filtered = filtered[filtered["is_collab"]]
    if q:
        filtered = filtered[
            filtered["title_raw"].str.lower().str.contains(q, na=False)
            | filtered["artist_raw"].str.lower().str.contains(q, na=False)
        ]

    dispatch = {
        "oldest": lambda d: d.sort_values(by="id", ascending=False),
        "duration_desc": lambda d: d.sort_values(by="duration_sec", ascending=False),
        "duration_asc": lambda d: d.sort_values(by="duration_sec", ascending=True),
        "title_asc": lambda d: d.sort_values(by="title_raw", key=lambda s: s.str.lower(), ascending=True),
        "artist_asc": lambda d: d.sort_values(by="artist_raw", key=lambda s: s.str.lower(), ascending=True),
    }
    return dispatch.get(sort_by, lambda d: d.sort_values(by="id", ascending=True))(filtered)


def _serialize_track_rows(page_slice: pd.DataFrame) -> List[Dict[str, Any]]:
    tracks: List[Dict[str, Any]] = []
    for _, row in page_slice.iterrows():
        title = row.get("title_raw", "")
        artist = row.get("artist_raw", "")
        yandex_url = row.get("yandex_url") or ""
        raw_tid = str(row.get("track_id", "")).strip()

        if raw_tid.isdigit() and int(raw_tid) > 50000:
            real_tid = raw_tid
        else:
            m = re.search(r"/track/(\d+)", str(yandex_url))
            real_tid = m.group(1) if m else str(row.get("id", 0))

        if not yandex_url:
            yandex_url = f"https://music.yandex.ru/search?text={urllib.parse.quote_plus(f'{artist} - {title}')}"

        genre_val = row.get("genre_cluster", CLUSTER_OTHER)
        tracks.append({
            "id": int(real_tid) if real_tid.isdigit() else int(row.get("id", 0)),
            "track_id": real_tid,
            "title": title,
            "artist": artist,
            "artists": row.get("all_artists", []),
            "duration_sec": int(row.get("duration_sec", 0)),
            "duration_fmt": row.get("duration_fmt", "0:00"),
            "genre": genre_val,
            "genre_color": CLUSTER_COLORS.get(genre_val, "#FFFFFF"),
            "is_collab": bool(row.get("is_collab", False)),
            "cover_uri": row.get("cover_uri", ""),
            "yandex_url": yandex_url,
        })
    return tracks


@analytics_bp.route("/api/tracks", methods=["GET"])
def get_tracks():
    df = get_dataset()
    if df.empty:
        return jsonify({"tracks": [], "total": 0, "page": 1, "total_pages": 0})

    page = max(1, int(request.args.get("page", 1)))
    limit = max(1, min(100, int(request.args.get("limit", 40))))
    filtered = _filter_and_sort_tracks(df)

    total_filtered = len(filtered)
    total_pages = max(1, math.ceil(total_filtered / limit))
    start_idx = (page - 1) * limit
    page_slice = filtered.iloc[start_idx : min(start_idx + limit, total_filtered)]

    return jsonify({
        "tracks": _serialize_track_rows(page_slice),
        "total": total_filtered,
        "page": page,
        "total_pages": total_pages,
        "limit": limit,
    })


@analytics_bp.route("/api/audio-features", methods=["GET"])
def get_audio_features():
    df = get_dataset()
    if df.empty:
        return jsonify({"success": False, "error": "No tracks loaded"}), 400

    tot = len(df)
    avg_sec = int(df["duration_sec"].mean()) if tot > 0 else 0
    g_cnt = df["genre_cluster"].value_counts().to_dict()

    weights = {
        CLUSTER_HEAVY_METAL: 0.96, CLUSTER_DUBSTEP_EDM: 0.94, CLUSTER_PHONK_MEMPHIS: 0.89,
        CLUSTER_HIPHOP_TRAP: 0.73, CLUSTER_ROCK_ALTERNATIVE: 0.69, CLUSTER_OTHER: 0.50,
    }
    w_energy = sum(g_cnt.get(g, 0) * weights.get(g, 0.5) for g in g_cnt)
    energy_pct = round((w_energy / tot) * 100, 1) if tot > 0 else 50.0

    fast = int(g_cnt.get(CLUSTER_DUBSTEP_EDM, 0) * 0.35 + g_cnt.get(CLUSTER_HEAVY_METAL, 0) * 0.40)
    driving = int(g_cnt.get(CLUSTER_PHONK_MEMPHIS, 0) * 0.85 + g_cnt.get(CLUSTER_DUBSTEP_EDM, 0) * 0.55 + g_cnt.get(CLUSTER_HIPHOP_TRAP, 0) * 0.50)
    mid = int(g_cnt.get(CLUSTER_ROCK_ALTERNATIVE, 0) * 0.75 + g_cnt.get(CLUSTER_HIPHOP_TRAP, 0) * 0.40 + g_cnt.get(CLUSTER_OTHER, 0) * 0.40)
    chill = max(0, tot - (fast + driving + mid))

    return jsonify({
        "success": True,
        "total_tracks": tot,
        "energy_score_percent": energy_pct,
        "energy_label": "Максимальный драйв 🔥" if energy_pct > 80 else ("Высокая энергия ⚡" if energy_pct > 65 else "Сбалансированная 🎧"),
        "average_duration_sec": avg_sec,
        "average_duration_fmt": format_seconds(avg_sec),
        "collab_ratio_percent": round((int(df["is_collab"].sum()) / tot) * 100, 1) if tot > 0 else 0.0,
        "bpm_profile": [
            {"range": "150–180+ BPM", "label": "Скоростной / Рейв", "count": fast, "percent": round((fast / tot) * 100, 1), "color": "#00E5FF"},
            {"range": "130–150 BPM", "label": "Драйв / Фонк & Дабстеп", "count": driving, "percent": round((driving / tot) * 100, 1), "color": "#D500F9"},
            {"range": "100–130 BPM", "label": "Кач / Рок & Трэп", "count": mid, "percent": round((mid / tot) * 100, 1), "color": "#FFD600"},
            {"range": "< 100 BPM", "label": "Чилл / Эмбиент", "count": chill, "percent": round((chill / tot) * 100, 1), "color": "#00E676"},
        ],
        "loudness_profile": {
            "heavy_lufs_percent": round(((g_cnt.get(CLUSTER_HEAVY_METAL, 0) + g_cnt.get(CLUSTER_DUBSTEP_EDM, 0) + g_cnt.get(CLUSTER_PHONK_MEMPHIS, 0)) / tot) * 100, 1),
            "standard_lufs_percent": round(((g_cnt.get(CLUSTER_HIPHOP_TRAP, 0) + g_cnt.get(CLUSTER_ROCK_ALTERNATIVE, 0)) / tot) * 100, 1),
            "acoustic_lufs_percent": round((g_cnt.get(CLUSTER_OTHER, 0) / tot) * 100, 1),
        },
    })
