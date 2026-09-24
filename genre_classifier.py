import json
import logging
import os
import re

import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def _load_lastfm_key() -> str:
    key = os.environ.get("LASTFM_API_KEY", "").strip()
    if not key:
        keys_file = os.path.join(os.path.dirname(__file__), ".ai_keys.json")
        if os.path.exists(keys_file):
            try:
                with open(keys_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = str(data.get("lastfm_api_key", "")).strip()
            except (IOError, json.JSONDecodeError) as e:
                logger.debug("Could not read lastfm key from %s: %s", keys_file, e)
    return key

LASTFM_API_KEY = _load_lastfm_key()
CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "genre_cache.sqlite")

CLUSTER_HEAVY_METAL = "Heavy & Metal"
CLUSTER_DUBSTEP_EDM = "Dubstep & EDM"
CLUSTER_PHONK_MEMPHIS = "Phonk & Memphis"
CLUSTER_HIPHOP_TRAP = "Hip-Hop & Trap"
CLUSTER_ROCK_ALTERNATIVE = "Rock & Alternative"
CLUSTER_OTHER = "Other & Electronic"

def _load_genre_data() -> Tuple[Dict[str, str], Dict[str, str]]:
    data_file = os.path.join(os.path.dirname(__file__), "genre_data.json")
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("TITLE_KEYWORDS", {}), data.get("BUILTIN_ARTISTS", {})
        except (IOError, json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load genre_data.json: %s", e)
    return {}, {}

TITLE_KEYWORDS, BUILTIN_ARTISTS = _load_genre_data()


class GenreClassifier:
    def __init__(self, db_path: str = CACHE_DB_PATH) -> None:
        self.db_path = db_path
        self._mem_cache: Dict[str, Tuple[str, List[str]]] = {}
        self._init_db()
        self._load_memory_cache()

    def _init_db(self) -> None:
        import genre_db
        genre_db.init_db(self.db_path)

    def reload_memory_cache(self) -> int:
        import genre_db
        self._mem_cache = genre_db.load_all_cached_artists(self.db_path)
        return len(self._mem_cache)

    def _load_memory_cache(self) -> None:
        self.reload_memory_cache()

    def get_cached_artist(self, artist_name: str) -> Optional[Tuple[str, List[str]]]:
        key = artist_name.strip().lower()
        if key in self._mem_cache:
            return self._mem_cache[key]
        return None

    def save_cached_artist(
        self,
        artist_name: str,
        cluster: str,
        tags: List[str],
        source: str = "api",
    ) -> None:
        import genre_db
        key = artist_name.strip().lower()
        self._mem_cache[key] = (cluster, tags)
        genre_db.save_cached_artists_batch([(artist_name, cluster, tags, source)], self.db_path)

    def save_cached_artists_batch(self, batch: List[Tuple[str, str, List[str], str]]) -> None:
        if not batch:
            return
        import genre_db
        for art, cl, tags, _ in batch:
            self._mem_cache[art.strip().lower()] = (cl, tags)
        genre_db.save_cached_artists_batch(batch, self.db_path)


    def fetch_lastfm_tags(self, artist_name: str, timeout: float = 4.0) -> List[str]:
        cleaned = artist_name.strip()
        url = (
            f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptags"
            f"&artist={urllib.parse.quote(cleaned)}&api_key={LASTFM_API_KEY}&format=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "MusicClassifier/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                toptags_obj = data.get("toptags")
                toptags = toptags_obj.get("tag", []) if isinstance(toptags_obj, dict) else []
                tags: List[str] = []
                for item in toptags:
                    if isinstance(item, dict) and "name" in item:
                        tags.append(str(item["name"]).strip().lower())
                return tags
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            logger.debug("Failed to fetch lastfm tags for '%s': %s", artist_name, e)
            return []

    def map_tags_to_cluster(self, tags: List[str]) -> Optional[str]:
        scores: Dict[str, int] = {
            CLUSTER_HEAVY_METAL: 0,
            CLUSTER_DUBSTEP_EDM: 0,
            CLUSTER_PHONK_MEMPHIS: 0,
            CLUSTER_HIPHOP_TRAP: 0,
            CLUSTER_ROCK_ALTERNATIVE: 0,
            CLUSTER_OTHER: 0,
        }

        for rank, tag in enumerate(tags[:12]):
            rank_multiplier = max(1, 10 - rank)
            tag_clean = tag.strip().lower()
            if tag_clean in TAG_WEIGHTS:
                cluster, base_w = TAG_WEIGHTS[tag_clean]
                scores[cluster] += base_w * rank_multiplier
            else:
                for sub, (cluster, base_w) in TAG_WEIGHTS.items():
                    if sub in tag_clean:
                        scores[cluster] += (base_w // 2) * rank_multiplier
                        break

        best_cluster = max(scores, key=scores.get)
        if scores[best_cluster] > 0:
            return best_cluster
        return None

    def match_title_keywords(self, title_raw: str) -> Optional[str]:
        title_lower = title_raw.lower()
        for kw, cluster in TITLE_KEYWORDS.items():
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, title_lower):
                return cluster
        return None

    def resolve_artist_worker(self, artist_name: str) -> Tuple[str, str, List[str], str]:
        artist_clean = artist_name.strip()
        artist_lower = artist_clean.lower()

        if artist_lower in BUILTIN_ARTISTS:
            return artist_clean, BUILTIN_ARTISTS[artist_lower], [], "builtin"

        for kw, cluster in TITLE_KEYWORDS.items():
            if kw in artist_lower:
                return artist_clean, cluster, [], "artist_keyword"

        tags = self.fetch_lastfm_tags(artist_clean)
        if tags:
            cluster = self.map_tags_to_cluster(tags)
            if cluster:
                return artist_clean, cluster, tags, "lastfm"
            else:
                return artist_clean, CLUSTER_OTHER, tags, "lastfm_other"

        return artist_clean, CLUSTER_OTHER, [], "unresolved"

    def classify_artist(
        self,
        artist_name: str,
        allow_network: bool = True,
    ) -> Tuple[str, List[str], str]:
        artist_clean = artist_name.strip()
        cached = self.get_cached_artist(artist_clean)
        if cached and cached[0] != CLUSTER_OTHER:
            return cached[0], cached[1], "cache"

        if not allow_network:
            artist_lower = artist_clean.lower()
            if artist_lower in BUILTIN_ARTISTS:
                return BUILTIN_ARTISTS[artist_lower], [], "builtin"
            return CLUSTER_OTHER, [], "unresolved"

        _, cluster, tags, source = self.resolve_artist_worker(artist_clean)
        self.save_cached_artist(artist_clean, cluster, tags, source=source)
        return cluster, tags, source

    def classify_track(
        self,
        artist_raw: str,
        title_raw: str,
        all_artists: List[str],
        allow_network: bool = False,
    ) -> Tuple[str, str]:
        for artist in all_artists:
            artist_lower = artist.strip().lower()
            if artist_lower in BUILTIN_ARTISTS:
                return BUILTIN_ARTISTS[artist_lower], "builtin_artist"

        title_cluster = self.match_title_keywords(title_raw)
        if title_cluster:
            return title_cluster, "title_keyword"

        for artist in all_artists:
            cached = self.get_cached_artist(artist)
            if cached and cached[0] != CLUSTER_OTHER:
                return cached[0], "artist_cache"

        primary = all_artists[0] if all_artists else artist_raw
        cluster, _, source = self.classify_artist(primary, allow_network=allow_network)
        return cluster, source
