from itertools import combinations
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
import pandas as pd

LINE_PATTERN = re.compile(r"^\s*(\d+)\.\s+(.*?)\s*\[(\d+):(\d+)\]\s*$")
FEAT_PATTERN = re.compile(
    r"(?:\(|\[)(?:feat\.?|ft\.?)\s+([^()\[\]]+)(?:\)|\])",
    re.IGNORECASE,
)
ARTIST_SPLIT_PATTERN = re.compile(
    r"\s*(?:,\s*|&|\s+feat\.?\s+|\s+ft\.?\s+|\s+vs\.?\s+|(?<=\s)/(?=\s))\s*",
    re.IGNORECASE,
)


def extract_artists(artist_raw: str, title_raw: str) -> List[str]:
    found_artists: List[str] = []
    seen: Set[str] = set()

    def add_artist(name: str) -> None:
        cleaned = name.strip(" ,.-_/\\()[]\"'")
        if cleaned and len(cleaned) > 1 and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            found_artists.append(cleaned)

    for item in ARTIST_SPLIT_PATTERN.split(artist_raw):
        add_artist(item)

    for match in FEAT_PATTERN.finditer(title_raw):
        feat_content = match.group(1)
        for item in ARTIST_SPLIT_PATTERN.split(feat_content):
            add_artist(item)

    if not found_artists:
        fallback = artist_raw.strip()
        if fallback:
            found_artists.append(fallback)

    return found_artists


def parse_track_line(line: str) -> Optional[Dict[str, Any]]:
    match = LINE_PATTERN.match(line)
    if not match:
        return None

    track_id = int(match.group(1))
    body = match.group(2).strip()
    minutes = int(match.group(3))
    seconds = int(match.group(4))
    duration_sec = minutes * 60 + seconds

    if " - " in body:
        artist_raw, title_raw = body.split(" - ", 1)
    else:
        artist_raw = body
        title_raw = "Unknown"

    artist_raw = artist_raw.strip()
    title_raw = title_raw.strip()

    artists = extract_artists(artist_raw, title_raw)
    primary_artist = artists[0] if artists else artist_raw

    return {
        "id": track_id,
        "artist_raw": artist_raw,
        "title_raw": title_raw,
        "primary_artist": primary_artist,
        "all_artists": artists,
        "artists_count": len(artists),
        "is_collab": len(artists) > 1,
        "duration_sec": duration_sec,
        "duration_fmt": f"{minutes}:{seconds:02d}",
    }


def load_playlist(file_path: str) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as file:
        for line in file:
            line_str = line.strip()
            if not line_str:
                continue
            item = parse_track_line(line_str)
            if item:
                records.append(item)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    return df.sort_values(by="id", ascending=True).reset_index(drop=True)


def parse_playlist_text(text: str) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        item = parse_track_line(line_str)
        if item:
            records.append(item)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    return df.sort_values(by="id", ascending=True).reset_index(drop=True)


def format_seconds(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    days = hours // 24
    rem_hours = hours % 24

    parts: List[str] = []
    if days > 0:
        parts.append(f"{days} дн.")
    if rem_hours > 0 or days > 0:
        parts.append(f"{rem_hours} ч.")
    parts.append(f"{minutes} мин.")
    if not parts:
        parts.append(f"{seconds} сек.")
    return " ".join(parts)


def build_collaborations_graph(
    df: pd.DataFrame,
    min_collaborations: int = 1,
    focus_artist: Optional[str] = None,
) -> nx.Graph:
    graph = nx.Graph()
    artist_counts: Dict[str, int] = {}
    collab_weights: Dict[Tuple[str, str], int] = {}

    for _, row in df.iterrows():
        artists: List[str] = row["all_artists"]
        for artist in artists:
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

        if len(artists) > 1:
            unique_in_track = sorted(list(dict.fromkeys(artists)))
            for a1, a2 in combinations(unique_in_track, 2):
                pair = (a1, a2)
                collab_weights[pair] = collab_weights.get(pair, 0) + 1

    for (a1, a2), weight in collab_weights.items():
        if weight >= min_collaborations:
            graph.add_edge(a1, a2, weight=weight)

    for node in list(graph.nodes()):
        graph.nodes[node]["count"] = artist_counts.get(node, 1)

    if focus_artist and focus_artist in graph:
        neighbors = set(graph.neighbors(focus_artist))
        neighbors.add(focus_artist)
        return graph.subgraph(neighbors).copy()

    return graph


def calculate_timeline_segments(
    df: pd.DataFrame,
    num_segments: int = 8,
    top_n_artists: int = 6,
) -> pd.DataFrame:
    total_tracks = len(df)
    if total_tracks == 0:
        return pd.DataFrame()

    segment_size = max(1, total_tracks // num_segments)
    records: List[Dict[str, Any]] = []

    exploded = df.explode("all_artists")
    top_global = (
        exploded["all_artists"]
        .value_counts()
        .head(top_n_artists)
        .index.tolist()
    )

    for i in range(num_segments):
        start_idx = i * segment_size
        end_idx = total_tracks if i == num_segments - 1 else (i + 1) * segment_size
        seg_slice = exploded.iloc[start_idx:end_idx]
        seg_label = f"#{start_idx + 1}–#{end_idx}"

        counts = seg_slice["all_artists"].value_counts()
        total_in_seg = len(seg_slice)

        for artist in top_global:
            cnt = int(counts.get(artist, 0))
            records.append(
                {
                    "segment": seg_label,
                    "segment_index": i,
                    "artist": artist,
                    "count": cnt,
                    "share_pct": round((cnt / total_in_seg * 100), 2) if total_in_seg > 0 else 0.0,
                }
            )

    return pd.DataFrame(records)
