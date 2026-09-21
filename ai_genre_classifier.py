import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

def _load_keys() -> Tuple[str, str]:
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()

    keys_file = os.path.join(os.path.dirname(__file__), ".ai_keys.json")
    if os.path.exists(keys_file):
        try:
            with open(keys_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not gemini_key:
                    gemini_key = str(data.get("gemini_api_key", "")).strip()
                if not groq_key:
                    groq_key = str(data.get("groq_api_key", "")).strip()
        except Exception:
            pass

    return gemini_key, groq_key


GEMINI_MODEL = "gemini-3.6-flash"
GROQ_MODEL = "qwen/qwen3.8-27b"

CLUSTER_HEAVY_METAL = "Heavy & Metal"
CLUSTER_DUBSTEP_EDM = "Dubstep & EDM"
CLUSTER_PHONK_MEMPHIS = "Phonk & Memphis"
CLUSTER_HIPHOP_TRAP = "Hip-Hop & Trap"
CLUSTER_ROCK_ALTERNATIVE = "Rock & Alternative"
CLUSTER_OTHER = "Other & Electronic"

VALID_CLUSTERS = {
    CLUSTER_HEAVY_METAL,
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_ROCK_ALTERNATIVE,
    CLUSTER_OTHER,
}

SYSTEM_PROMPT = """You are an elite music genre classification system.
Your task is to classify musical artists into EXACTLY ONE of these 6 target clusters, based on the artist name and their real track titles:

Target Clusters:
1. "Heavy & Metal": Deathcore, Slamming Brutal Death Metal, Metalcore, Nu Metal, Beatdown, Death Metal, Grindcore, Thrash. (e.g. ten56, Slaughter to Prevail, Paleface Swiss, Lorna Shore).
2. "Dubstep & EDM": Dubstep, Riddim, Tearout, DnB, Drum & Bass, Neurofunk, Electronic Hardcore, Hardtempo, Hardstyle, Gabber, Tekk, Speedcore, Bass music. (e.g. Chickencore, Subtronics, Excision, SVDDEN DEATH, Revolxist).
3. "Phonk & Memphis": Phonk, Drift Phonk, Memphis Rap, Brazilian Funk, Montagem, Wave Phonk. (e.g. THXWINTER PLAYA, PLAYA SSK, FEXFILLMANE, Kordhell).
4. "Hip-Hop & Trap": Rap, Trap, Russian Underground Rap, Boom Bap, Cloud Rap, Drill. (e.g. Nasvayniy, СБД, Three 6 Mafia, Big Baby Tape, Gucci Mane).
5. "Rock & Alternative": Alternative Rock, Indie, Post-Hardcore, Emo, Punk, Grunge. (e.g. Radiohead, Deftones, Nirvana, Linkin Park, Кино).
6. "Other & Electronic": Ambient, Synthwave, Retrowave, Pop, Lo-Fi, Soundtrack, Classical, Downtempo.

CRITICAL CLASSIFICATION RULES:
- Electronic Hardcore, Hardtempo, Hardstyle, Acid, Rave, Tekk MUST be classified as "Dubstep & EDM" (NOT Metal!). Example: Chickencore produces hardtempo/rave -> "Dubstep & EDM".
- Metalcore, Deathcore, Slam, Beatdown with heavy guitars/screaming MUST be classified as "Heavy & Metal". Example: ten56 -> "Heavy & Metal".
- Drift, slowed/reverb, funk phonk, memphis revival MUST be classified as "Phonk & Memphis".

Input format: A JSON array of objects:
[{"artist": "Artist Name", "tracks": ["Track 1", "Track 2"]}]

Output format: A raw JSON array of objects with EXACT field names:
[{"artist": "Artist Name", "cluster": "Cluster Name", "tags": ["subgenre1", "subgenre2"]}]

Respond ONLY with valid JSON. Do not include markdown fences or any other text.
"""


class AIGenreClassifier:
    def __init__(
        self,
        gemini_key: Optional[str] = None,
        groq_key: Optional[str] = None,
    ) -> None:
        def_gemini, def_groq = _load_keys()
        self.gemini_key = (gemini_key or def_gemini).strip()
        self.groq_key = (groq_key or def_groq).strip()

    def _call_gemini_batch(self, items: List[Dict[str, Any]], timeout: float = 25.0) -> List[Dict[str, Any]]:
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.gemini_key}"
        user_prompt = f"{SYSTEM_PROMPT}\n\nInput artists:\n{json.dumps(items, ensure_ascii=False)}"

        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MusicClassifier/3.0",
            },
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini returned empty candidates")
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return self._parse_json_result(text)

    def _call_groq_batch(self, items: List[Dict[str, Any]], timeout: float = 20.0) -> List[Dict[str, Any]]:
        if not self.groq_key:
            raise ValueError("GROQ_API_KEY is not configured")

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            content = data["choices"][0]["message"]["content"].strip()
            return self._parse_json_result(content)

    def _parse_json_result(self, raw_text: str) -> List[Dict[str, Any]]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        if not isinstance(data, list):
            raise ValueError(f"Expected list from AI, got {type(data)}")

        results: List[Dict[str, Any]] = []
        for obj in data:
            if not isinstance(obj, dict):
                continue
            artist = str(obj.get("artist", "")).strip()
            cluster = str(obj.get("cluster", "")).strip()
            tags = obj.get("tags", [])
            if not isinstance(tags, list):
                tags = [str(tags)]
            tags_clean = [str(t).strip().lower() for t in tags if str(t).strip()]

            # Validate cluster name
            if cluster not in VALID_CLUSTERS:
                cluster = self._match_best_cluster(cluster)

            if artist:
                results.append({
                    "artist": artist,
                    "cluster": cluster,
                    "tags": tags_clean,
                })
        return results

    def _match_best_cluster(self, raw_cluster: str) -> str:
        lowered = raw_cluster.lower()
        if "metal" in lowered or "deathcore" in lowered or "slam" in lowered:
            return CLUSTER_HEAVY_METAL
        if "dubstep" in lowered or "edm" in lowered or "hardcore" in lowered or "hardstyle" in lowered or "tekk" in lowered:
            return CLUSTER_DUBSTEP_EDM
        if "phonk" in lowered or "memphis" in lowered or "drift" in lowered:
            return CLUSTER_PHONK_MEMPHIS
        if "hip" in lowered or "rap" in lowered or "trap" in lowered:
            return CLUSTER_HIPHOP_TRAP
        if "rock" in lowered or "indie" in lowered or "punk" in lowered or "alternative" in lowered:
            return CLUSTER_ROCK_ALTERNATIVE
        return CLUSTER_OTHER

    def classify_batch(
        self,
        items: List[Dict[str, Any]],
        on_progress: Optional[Any] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Classifies a batch of artist objects: [{"artist": "Name", "tracks": ["T1", "T2"]}].
        Attempts Gemini first; if it fails or times out, falls back to Groq.
        Returns (results, provider_name).
        """
        if not items:
            return [], "none"

        # 1. Try Primary: Google Gemini 3.6 Flash
        try:
            results = self._call_gemini_batch(items)
            if results:
                return results, "gemini"
        except Exception as gemini_err:
            if on_progress:
                on_progress(f"⚠️ Gemini: {gemini_err}. Переключаюсь на Groq...")

        # 2. Try Fallback: Groq Qwen/LLaMA
        try:
            results = self._call_groq_batch(items)
            if results:
                return results, "groq"
        except Exception as groq_err:
            if on_progress:
                on_progress(f"⚠️ Groq: {groq_err}")
            raise RuntimeError(f"All AI providers failed. Gemini: {gemini_err}, Groq: {groq_err}")

        return [], "failed"

    @staticmethod
    def save_ai_results_to_sqlite(
        db_path: str,
        results: List[Dict[str, Any]],
    ) -> int:
        if not results:
            return 0
        saved_count = 0
        with sqlite3.connect(db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            for item in results:
                artist_name = item["artist"].strip()
                artist_key = artist_name.lower()
                cluster = item["cluster"]
                tags = item.get("tags", [])
                tags_json = json.dumps(tags, ensure_ascii=False)

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO artist_cache (artist_key, artist_name, cluster, tags_json, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (artist_key, artist_name, cluster, tags_json, "ai"),
                )
                saved_count += 1
            conn.commit()
        return saved_count
