import re
import urllib.parse
from typing import Any, Dict, List, Tuple
from flask import Blueprint, jsonify, request
import pandas as pd


from api_routes.state import (
    CLUSTER_COLORS,
    CLUSTER_OTHER,
    get_dataset,
)
from parser import format_seconds
import yandex_api

artists_bp = Blueprint("artists", __name__)


def _is_artist_match(row: pd.Series, target_lower: str) -> bool:
    artists = row.get("all_artists")
    if isinstance(artists, list) and any(a.lower() == target_lower for a in artists):
        return True
    return (
        str(row.get("primary_artist", "")).lower() == target_lower
        or str(row.get("artist_raw", "")).lower() == target_lower
    )


def _compute_artist_metrics(matched_df: pd.DataFrame, target_lower: str, df: pd.DataFrame) -> Dict[str, Any]:
    tot_matched = len(matched_df)
    tot_lib = len(df)
    share_pct = round((tot_matched / tot_lib) * 100, 2) if tot_lib > 0 else 0.0

    tot_dur = int(matched_df["duration_sec"].sum())
    avg_dur = int(matched_df["duration_sec"].mean()) if tot_matched > 0 else 0

    genre_counts = matched_df["genre_cluster"].value_counts().to_dict()
    dominant_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "Unknown"

    genres_breakdown = [
        {
            "genre": g,
            "count": int(c),
            "percent": round((c / tot_matched) * 100, 1),
            "color": CLUSTER_COLORS.get(g, "#FFFFFF"),
        }
        for g, c in genre_counts.items()
    ]

    collab_dict: Dict[str, int] = {}
    for arts in matched_df["all_artists"]:
        if isinstance(arts, list):
            for a in arts:
                if a.lower() != target_lower:
                    collab_dict[a] = collab_dict.get(a, 0) + 1

    top_collabs = sorted(
        [{"artist": a, "count": c} for a, c in collab_dict.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:12]

    return {
        "share_pct": share_pct,
        "tot_dur": tot_dur,
        "avg_dur": avg_dur,
        "dominant_genre": dominant_genre,
        "genres_breakdown": genres_breakdown,
        "top_collabs": top_collabs,
    }


def _serialize_artist_tracks(matched_df: pd.DataFrame) -> List[Dict[str, Any]]:
    tracks = []
    for _, row in matched_df.iterrows():
        title = row.get("title_raw", "")
        artist = row.get("artist_raw", "")
        yandex_url = row.get("yandex_url") or f"https://music.yandex.ru/search?text={urllib.parse.quote_plus(f'{artist} - {title}')}"
        genre_val = row.get("genre_cluster", CLUSTER_OTHER)
        tracks.append({
            "id": int(row.get("id", 0)),
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


@artists_bp.route("/api/artist", methods=["GET"])
def get_artist():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Параметр 'name' обязателен"}), 400

    df = get_dataset()
    if df.empty:
        return jsonify({"error": "Медиатека пуста"}), 404

    target_lower = name.lower()
    matched_df = df[df.apply(lambda r: _is_artist_match(r, target_lower), axis=1)]
    if matched_df.empty:
        return jsonify({"error": f"Артист '{name}' не найден в медиатеке"}), 404

    metrics = _compute_artist_metrics(matched_df, target_lower, df)
    tracks = _serialize_artist_tracks(matched_df)

    all_arts = [a for arts in df["all_artists"] if isinstance(arts, list) for a in arts]
    rank_s = pd.Series(all_arts).value_counts()
    rank = next((i + 1 for i, (a, _) in enumerate(rank_s.items()) if a.lower() == target_lower), None)

    canonical = matched_df.iloc[0]["primary_artist"] if target_lower == matched_df.iloc[0]["primary_artist"].lower() else name
    return jsonify({
        "artist": canonical,
        "rank": rank,
        "total_tracks": len(matched_df),
        "library_share_percent": metrics["share_pct"],
        "total_duration_sec": metrics["tot_dur"],
        "total_duration_fmt": format_seconds(metrics["tot_dur"]),
        "avg_duration_sec": metrics["avg_dur"],
        "solo_count": int((~matched_df["is_collab"]).sum()),
        "collab_count": int(matched_df["is_collab"].sum()),
        "dominant_genre": metrics["dominant_genre"],
        "dominant_color": CLUSTER_COLORS.get(metrics["dominant_genre"], "#FFCC00"),
        "genres": metrics["genres_breakdown"],
        "top_collaborators": metrics["top_collabs"],
        "tracks": tracks,
        "yandex_url": f"https://music.yandex.ru/search?text={urllib.parse.quote_plus(canonical)}&type=artists",
    })


@artists_bp.route("/api/track-stream/<track_id>", methods=["GET"])
def track_stream(track_id):
    auth_h = request.headers.get("Authorization", "")
    token = auth_h.replace("Bearer ", "").strip() if auth_h.startswith("Bearer ") else None

    artist_param = request.args.get("artist", "").strip() or None
    title_param = request.args.get("title", "").strip() or None
    effective_id = str(track_id).strip()

    df = get_dataset()
    if df is not None and not df.empty and effective_id.isdigit() and int(effective_id) <= 50000:
        match_row = df[df["id"] == int(effective_id)]
        if not match_row.empty:
            r = match_row.iloc[0]
            raw_tid = str(r.get("track_id", "")).strip()
            if raw_tid.isdigit() and int(raw_tid) > 50000:
                effective_id = raw_tid
            else:
                m_u = re.search(r"/track/(\d+)", str(r.get("yandex_url", "")))
                if m_u:
                    effective_id = m_u.group(1)
            artist_param = artist_param or str(r.get("artist_raw", "")).strip() or None
            title_param = title_param or str(r.get("title_raw", "")).strip() or None

    info = yandex_api.get_track_stream_url(effective_id, token=token, artist=artist_param, title=title_param)
    if not info:
        return jsonify({"success": False, "error": f"Не удалось получить аудио-поток для трека {track_id}"}), 404
    return jsonify({"success": True, **info})


def normalize_duplicate_title(title: str) -> str:
    t = str(title).strip()
    t = re.sub(
        r"[\(\[\{].*?(?:remaster|deluxe|version|bonus|edit|mix|live|remix|acoustic|instrumental|feat|ft\.).*?[\)\]\}]",
        "",
        t,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[\W_]+", " ", t).strip().lower()


def _build_duplicate_groups(grouped: pd.DataFrame) -> Tuple[List[Dict[str, Any]], int, int]:
    groups_list = []
    tot_red = 0
    tot_red_sec = 0

    for (a_key, t_key), grp in grouped.groupby(["norm_artist", "norm_title"]):
        sorted_grp = grp.sort_values(by="id", ascending=True)
        tracks_in_grp = []
        is_first = True

        for _, row in sorted_grp.iterrows():
            t_id = str(row.get("id", ""))
            y_url = f"https://music.yandex.ru/track/{t_id}" if t_id.isdigit() and int(t_id) > 1000 else None
            cover = row.get("cover_uri", None)
            if cover and isinstance(cover, str) and "%%" in cover:
                cover = "https://" + cover.replace("%%", "200x200")
            elif not cover:
                cover = None

            dur = int(row.get("duration_sec", 0))
            tracks_in_grp.append({
                "id": t_id,
                "title": str(row.get("title_raw", "")),
                "artist": str(row.get("primary_artist", "")),
                "all_artists": row.get("all_artists", []),
                "duration_sec": dur,
                "duration_fmt": str(row.get("duration_fmt", "")),
                "genre_cluster": str(row.get("genre_cluster", CLUSTER_OTHER)),
                "cover_url": cover,
                "yandex_url": y_url,
                "is_original": is_first,
            })
            if not is_first:
                tot_red += 1
                tot_red_sec += dur
            is_first = False

        groups_list.append({
            "key": f"{a_key} - {t_key}",
            "artist": sorted_grp.iloc[0].get("primary_artist", a_key),
            "title": sorted_grp.iloc[0].get("title_raw", t_key),
            "count": len(tracks_in_grp),
            "tracks": tracks_in_grp,
        })
    groups_list.sort(key=lambda g: g["count"], reverse=True)
    return groups_list, tot_red, tot_red_sec


@artists_bp.route("/api/duplicates", methods=["GET"])
def get_duplicates():
    df = get_dataset()
    if df.empty:
        return jsonify({"success": True, "total_duplicates": 0, "duplicate_groups_count": 0, "total_redundant_time_sec": 0, "total_redundant_time_fmt": "0:00", "groups": []})

    temp_df = df.copy()
    temp_df["norm_title"] = temp_df["title_raw"].apply(normalize_duplicate_title)
    temp_df["norm_artist"] = temp_df["primary_artist"].astype(str).str.strip().str.lower()
    valid = temp_df[(temp_df["norm_title"] != "") & (temp_df["norm_artist"] != "")]
    grouped = valid.groupby(["norm_artist", "norm_title"]).filter(lambda x: len(x) > 1)

    if grouped.empty:
        return jsonify({"success": True, "total_duplicates": 0, "duplicate_groups_count": 0, "total_redundant_time_sec": 0, "total_redundant_time_fmt": "0:00", "groups": []})

    groups_list, tot_red, tot_red_sec = _build_duplicate_groups(grouped)
    return jsonify({
        "success": True,
        "total_duplicates": tot_red,
        "duplicate_groups_count": len(groups_list),
        "total_redundant_time_sec": tot_red_sec,
        "total_redundant_time_fmt": format_seconds(tot_red_sec),
        "groups": groups_list,
    })
