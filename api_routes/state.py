import logging
import os
from typing import Dict, Optional
from flask import request
import pandas as pd

from ai_genre_classifier import AIGenreClassifier
from genre_classifier import (
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_OTHER,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
    GenreClassifier,
)
from parser import load_playlist

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FILE_PATH = os.path.join(
    BASE_DIR, "Мне нравится_965180470_20260915_213456.txt"
)
SYNCED_CACHE_PATH = os.path.join(BASE_DIR, "synced_likes.pkl")
TOKEN_FILE_PATH = os.path.join(BASE_DIR, ".yandex_token")

_df_cache: Optional[pd.DataFrame] = None
_classifier = GenreClassifier()
_ai_classifier = AIGenreClassifier()

CLUSTER_COLORS: Dict[str, str] = {
    CLUSTER_DUBSTEP_EDM: "#00E5FF",
    CLUSTER_HEAVY_METAL: "#FF3D00",
    CLUSTER_PHONK_MEMPHIS: "#D500F9",
    CLUSTER_HIPHOP_TRAP: "#FFD600",
    CLUSTER_ROCK_ALTERNATIVE: "#00E676",
    CLUSTER_OTHER: "#B0BEC5",
}

CLUSTER_ICONS: Dict[str, str] = {
    CLUSTER_DUBSTEP_EDM: "electric_bolt",
    CLUSTER_HEAVY_METAL: "local_fire_department",
    CLUSTER_PHONK_MEMPHIS: "speed",
    CLUSTER_HIPHOP_TRAP: "mic",
    CLUSTER_ROCK_ALTERNATIVE: "graphic_eq",
    CLUSTER_OTHER: "category",
}


def get_classifier() -> GenreClassifier:
    return _classifier


def get_ai_classifier() -> AIGenreClassifier:
    return _ai_classifier


def set_dataset_cache(df: pd.DataFrame) -> None:
    global _df_cache
    _df_cache = df


def _load_persisted_cache() -> Optional[pd.DataFrame]:
    if not os.path.exists(SYNCED_CACHE_PATH):
        return None
    try:
        persisted = pd.read_pickle(SYNCED_CACHE_PATH)
        if persisted is not None and not persisted.empty:
            return persisted
    except (IOError, OSError, ValueError) as e:
        logger.warning("Ошибка загрузки кэша синхронизации: %s", e)
    return None


def _load_base_playlist() -> pd.DataFrame:
    if not os.path.exists(DEFAULT_FILE_PATH):
        return pd.DataFrame()
    df = load_playlist(DEFAULT_FILE_PATH)
    if df.empty:
        return df

    genres = [
        _classifier.classify_track(a, t, aa, allow_network=False)[0]
        for a, t, aa in zip(df["artist_raw"], df["title_raw"], df["all_artists"])
    ]
    df["genre_cluster"] = genres
    return df


def get_dataset() -> pd.DataFrame:
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    persisted = _load_persisted_cache()
    if persisted is not None:
        _df_cache = persisted
        return _df_cache

    _df_cache = _load_base_playlist()
    return _df_cache


def get_auth_token_from_request() -> str:
    """Извлекает токен авторизации из query, body, заголовка или кэш-файла."""
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

    if not token and os.path.exists(TOKEN_FILE_PATH):
        try:
            with open(TOKEN_FILE_PATH, "r", encoding="utf-8") as f:
                token = f.read().strip()
        except OSError as e:
            logger.debug("Could not read token file: %s", e)

    return token
