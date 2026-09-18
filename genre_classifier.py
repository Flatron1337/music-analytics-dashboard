import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

LASTFM_API_KEY = "b25b959554ed76058ac220b7b2e0a026"
CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "genre_cache.sqlite")

CLUSTER_HEAVY_METAL = "Heavy & Metal"
CLUSTER_DUBSTEP_EDM = "Dubstep & EDM"
CLUSTER_PHONK_MEMPHIS = "Phonk & Memphis"
CLUSTER_HIPHOP_TRAP = "Hip-Hop & Trap"
CLUSTER_ROCK_ALTERNATIVE = "Rock & Alternative"
CLUSTER_OTHER = "Other & Electronic"

TITLE_KEYWORDS: Dict[str, str] = {
    # Phonk / Memphis
    "phonk": CLUSTER_PHONK_MEMPHIS,
    "drift": CLUSTER_PHONK_MEMPHIS,
    "memphis": CLUSTER_PHONK_MEMPHIS,
    "slowed": CLUSTER_PHONK_MEMPHIS,
    "sped up": CLUSTER_PHONK_MEMPHIS,
    "montagem": CLUSTER_PHONK_MEMPHIS,
    "funk": CLUSTER_PHONK_MEMPHIS,
    # Dubstep / EDM / Hard Dance
    "dubstep": CLUSTER_DUBSTEP_EDM,
    "riddim": CLUSTER_DUBSTEP_EDM,
    "tearout": CLUSTER_DUBSTEP_EDM,
    "hardtekk": CLUSTER_DUBSTEP_EDM,
    "tekk": CLUSTER_DUBSTEP_EDM,
    "jumpstyle": CLUSTER_DUBSTEP_EDM,
    "gabber": CLUSTER_DUBSTEP_EDM,
    "dnb": CLUSTER_DUBSTEP_EDM,
    "drum and bass": CLUSTER_DUBSTEP_EDM,
    "drum & bass": CLUSTER_DUBSTEP_EDM,
    "neurofunk": CLUSTER_DUBSTEP_EDM,
    "deathstep": CLUSTER_DUBSTEP_EDM,
    "remix": CLUSTER_DUBSTEP_EDM,
    "vip": CLUSTER_DUBSTEP_EDM,
    # Heavy & Metal
    "deathcore": CLUSTER_HEAVY_METAL,
    "beatdown": CLUSTER_HEAVY_METAL,
    "metalcore": CLUSTER_HEAVY_METAL,
    "slam": CLUSTER_HEAVY_METAL,
    "grindcore": CLUSTER_HEAVY_METAL,
    "death metal": CLUSTER_HEAVY_METAL,
    "black metal": CLUSTER_HEAVY_METAL,
    # Rock / Punk
    "punk": CLUSTER_ROCK_ALTERNATIVE,
    "grunge": CLUSTER_ROCK_ALTERNATIVE,
    "rock": CLUSTER_ROCK_ALTERNATIVE,
}

TAG_WEIGHTS: Dict[str, Tuple[str, int]] = {
    # Heavy & Metal
    "deathcore": (CLUSTER_HEAVY_METAL, 25),
    "slamming death metal": (CLUSTER_HEAVY_METAL, 25),
    "slamming brutal death metal": (CLUSTER_HEAVY_METAL, 25),
    "brutal deathcore": (CLUSTER_HEAVY_METAL, 25),
    "beatdown": (CLUSTER_HEAVY_METAL, 22),
    "beatdown hardcore": (CLUSTER_HEAVY_METAL, 22),
    "grindcore": (CLUSTER_HEAVY_METAL, 22),
    "slam": (CLUSTER_HEAVY_METAL, 22),
    "death metal": (CLUSTER_HEAVY_METAL, 20),
    "metalcore": (CLUSTER_HEAVY_METAL, 20),
    "black metal": (CLUSTER_HEAVY_METAL, 20),
    "brutal death metal": (CLUSTER_HEAVY_METAL, 20),
    "technical deathcore": (CLUSTER_HEAVY_METAL, 20),
    "technical death metal": (CLUSTER_HEAVY_METAL, 20),
    "dsbm": (CLUSTER_HEAVY_METAL, 20),
    "nu metal": (CLUSTER_HEAVY_METAL, 18),
    "heavy metal": (CLUSTER_HEAVY_METAL, 18),
    "thrash metal": (CLUSTER_HEAVY_METAL, 18),
    "metal": (CLUSTER_HEAVY_METAL, 14),
    "groove metal": (CLUSTER_HEAVY_METAL, 16),
    "moshcore": (CLUSTER_HEAVY_METAL, 18),
    "hardcore punk": (CLUSTER_HEAVY_METAL, 14),
    # Dubstep & Bass EDM & Hard Dance
    "riddim": (CLUSTER_DUBSTEP_EDM, 25),
    "tearout": (CLUSTER_DUBSTEP_EDM, 25),
    "trench": (CLUSTER_DUBSTEP_EDM, 25),
    "deathstep": (CLUSTER_DUBSTEP_EDM, 25),
    "dubstep": (CLUSTER_DUBSTEP_EDM, 22),
    "brostep": (CLUSTER_DUBSTEP_EDM, 22),
    "hardtekk": (CLUSTER_DUBSTEP_EDM, 22),
    "jumpstyle": (CLUSTER_DUBSTEP_EDM, 22),
    "gabber": (CLUSTER_DUBSTEP_EDM, 22),
    "uptempo": (CLUSTER_DUBSTEP_EDM, 22),
    "uptempo hardcore": (CLUSTER_DUBSTEP_EDM, 22),
    "speedcore": (CLUSTER_DUBSTEP_EDM, 22),
    "drum and bass": (CLUSTER_DUBSTEP_EDM, 20),
    "dnb": (CLUSTER_DUBSTEP_EDM, 20),
    "neurofunk": (CLUSTER_DUBSTEP_EDM, 20),
    "tekk": (CLUSTER_DUBSTEP_EDM, 20),
    "breakcore": (CLUSTER_DUBSTEP_EDM, 18),
    "darkstep": (CLUSTER_DUBSTEP_EDM, 18),
    "hardstyle": (CLUSTER_DUBSTEP_EDM, 18),
    "bass music": (CLUSTER_DUBSTEP_EDM, 16),
    "jungle": (CLUSTER_DUBSTEP_EDM, 16),
    "edm": (CLUSTER_DUBSTEP_EDM, 14),
    "techno": (CLUSTER_DUBSTEP_EDM, 14),
    "hard techno": (CLUSTER_DUBSTEP_EDM, 16),
    "electronic": (CLUSTER_DUBSTEP_EDM, 6),
    "dance": (CLUSTER_DUBSTEP_EDM, 6),
    # Phonk & Memphis
    "phonk": (CLUSTER_PHONK_MEMPHIS, 25),
    "drift phonk": (CLUSTER_PHONK_MEMPHIS, 25),
    "wave phonk": (CLUSTER_PHONK_MEMPHIS, 25),
    "memphis rap": (CLUSTER_PHONK_MEMPHIS, 25),
    "memphis": (CLUSTER_PHONK_MEMPHIS, 22),
    "horrorcore": (CLUSTER_PHONK_MEMPHIS, 22),
    "witch house": (CLUSTER_PHONK_MEMPHIS, 22),
    "trap metal": (CLUSTER_PHONK_MEMPHIS, 22),
    "necrotrap": (CLUSTER_PHONK_MEMPHIS, 22),
    "dark trap": (CLUSTER_PHONK_MEMPHIS, 20),
    "brazilian funk": (CLUSTER_PHONK_MEMPHIS, 20),
    "funk brasileiro": (CLUSTER_PHONK_MEMPHIS, 20),
    "cloud rap": (CLUSTER_PHONK_MEMPHIS, 16),
    "emo rap": (CLUSTER_PHONK_MEMPHIS, 14),
    # Hip-Hop & Trap
    "dirty south": (CLUSTER_HIPHOP_TRAP, 22),
    "southern rap": (CLUSTER_HIPHOP_TRAP, 22),
    "gangsta rap": (CLUSTER_HIPHOP_TRAP, 22),
    "trap": (CLUSTER_HIPHOP_TRAP, 20),
    "rage": (CLUSTER_HIPHOP_TRAP, 20),
    "hip-hop": (CLUSTER_HIPHOP_TRAP, 18),
    "hip hop": (CLUSTER_HIPHOP_TRAP, 18),
    "rap": (CLUSTER_HIPHOP_TRAP, 16),
    "boom bap": (CLUSTER_HIPHOP_TRAP, 18),
    "drill": (CLUSTER_HIPHOP_TRAP, 18),
    "russian rap": (CLUSTER_HIPHOP_TRAP, 18),
    "russian hip-hop": (CLUSTER_HIPHOP_TRAP, 18),
    "battle rap": (CLUSTER_HIPHOP_TRAP, 16),
    "west coast rap": (CLUSTER_HIPHOP_TRAP, 18),
    "east coast rap": (CLUSTER_HIPHOP_TRAP, 18),
    "underground hip-hop": (CLUSTER_HIPHOP_TRAP, 16),
    # Rock & Alternative
    "rock": (CLUSTER_ROCK_ALTERNATIVE, 18),
    "alternative rock": (CLUSTER_ROCK_ALTERNATIVE, 22),
    "alternative": (CLUSTER_ROCK_ALTERNATIVE, 16),
    "post-grunge": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "grunge": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "punk": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "punk rock": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "pop punk": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "post-punk": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "russian rock": (CLUSTER_ROCK_ALTERNATIVE, 20),
    "indie rock": (CLUSTER_ROCK_ALTERNATIVE, 18),
    "indie": (CLUSTER_ROCK_ALTERNATIVE, 14),
    "emo": (CLUSTER_ROCK_ALTERNATIVE, 16),
    "post-hardcore": (CLUSTER_ROCK_ALTERNATIVE, 16),
    # Other & Electronic
    "pop": (CLUSTER_OTHER, 14),
    "synthpop": (CLUSTER_OTHER, 14),
    "synthwave": (CLUSTER_OTHER, 14),
    "retrowave": (CLUSTER_OTHER, 14),
    "ambient": (CLUSTER_OTHER, 12),
    "downtempo": (CLUSTER_OTHER, 12),
    "lo-fi": (CLUSTER_OTHER, 12),
    "soundtrack": (CLUSTER_OTHER, 12),
}

BUILTIN_ARTISTS: Dict[str, str] = {
    # Underground Collectives & Key Artists
    "home4circus": CLUSTER_DUBSTEP_EDM,
    "harmony hustlers": CLUSTER_PHONK_MEMPHIS,
    "24.16": CLUSTER_DUBSTEP_EDM,
    "t-rip": CLUSTER_PHONK_MEMPHIS,
    "dj shizoid": CLUSTER_DUBSTEP_EDM,
    "dayerteq": CLUSTER_DUBSTEP_EDM,
    "kamz0ner": CLUSTER_PHONK_MEMPHIS,
    "keener": CLUSTER_DUBSTEP_EDM,
    "unsyn": CLUSTER_DUBSTEP_EDM,
    # Heavy & Metal
    "paleface swiss": CLUSTER_HEAVY_METAL,
    "angelmaker": CLUSTER_HEAVY_METAL,
    "thy art is murder": CLUSTER_HEAVY_METAL,
    "chelsea grin": CLUSTER_HEAVY_METAL,
    "infant annihilator": CLUSTER_HEAVY_METAL,
    "the dark prison massacre": CLUSTER_HEAVY_METAL,
    "slayer": CLUSTER_HEAVY_METAL,
    "slipknot": CLUSTER_HEAVY_METAL,
    "archspire": CLUSTER_HEAVY_METAL,
    "gorepot": CLUSTER_HEAVY_METAL,
    "whitechapel": CLUSTER_HEAVY_METAL,
    "korn": CLUSTER_HEAVY_METAL,
    "disturbed": CLUSTER_HEAVY_METAL,
    "coal chamber": CLUSTER_HEAVY_METAL,
    "benighted": CLUSTER_HEAVY_METAL,
    "orbit culture": CLUSTER_HEAVY_METAL,
    "suicide silence": CLUSTER_HEAVY_METAL,
    "slaughter to prevail": CLUSTER_HEAVY_METAL,
    "alex terrible": CLUSTER_HEAVY_METAL,
    "attila": CLUSTER_HEAVY_METAL,
    "dry kill logic": CLUSTER_HEAVY_METAL,
    "synestia": CLUSTER_HEAVY_METAL,
    "disembodied tyrant": CLUSTER_HEAVY_METAL,
    "frontierer": CLUSTER_HEAVY_METAL,
    "netherwalker": CLUSTER_HEAVY_METAL,
    "soulfly": CLUSTER_HEAVY_METAL,
    "after the burial": CLUSTER_HEAVY_METAL,
    "lorna shore": CLUSTER_HEAVY_METAL,
    "spite": CLUSTER_HEAVY_METAL,
    "bodysnatcher": CLUSTER_HEAVY_METAL,
    "shadow of intent": CLUSTER_HEAVY_METAL,
    "vulvodynia": CLUSTER_HEAVY_METAL,
    "acranius": CLUSTER_HEAVY_METAL,
    "gutrectomy": CLUSTER_HEAVY_METAL,
    "peelingflesh": CLUSTER_HEAVY_METAL,
    "snuffed on sight": CLUSTER_HEAVY_METAL,
    "ten56.": CLUSTER_HEAVY_METAL,
    "thrown": CLUSTER_HEAVY_METAL,
    "nordside": CLUSTER_HEAVY_METAL,
    "sigil": CLUSTER_HEAVY_METAL,
    "fatuous rump": CLUSTER_HEAVY_METAL,
    "cabal": CLUSTER_HEAVY_METAL,
    "bethlehem": CLUSTER_HEAVY_METAL,
    "signs of the swarm": CLUSTER_HEAVY_METAL,
    "brand of sacrifice": CLUSTER_HEAVY_METAL,
    "distant": CLUSTER_HEAVY_METAL,
    "enterprise earth": CLUSTER_HEAVY_METAL,
    "mental cruelty": CLUSTER_HEAVY_METAL,
    "ingested": CLUSTER_HEAVY_METAL,
    "extermination dismemberment": CLUSTER_HEAVY_METAL,
    "organectomy": CLUSTER_HEAVY_METAL,
    "waking the cadaver": CLUSTER_HEAVY_METAL,
    "knocked loose": CLUSTER_HEAVY_METAL,
    "cold blooded murder": CLUSTER_HEAVY_METAL,
    "bound in fear": CLUSTER_HEAVY_METAL,
    "emmure": CLUSTER_HEAVY_METAL,
    "dethklok": CLUSTER_HEAVY_METAL,
    "we butter the bread with butter": CLUSTER_HEAVY_METAL,
    "rings of saturn": CLUSTER_HEAVY_METAL,
    "mirar": CLUSTER_HEAVY_METAL,
    "psycho-frame": CLUSTER_HEAVY_METAL,
    "brojob": CLUSTER_HEAVY_METAL,
    "archgoat": CLUSTER_HEAVY_METAL,
    "kublai khan tx": CLUSTER_HEAVY_METAL,
    "cold hard truth": CLUSTER_HEAVY_METAL,
    "tayga hardcore division": CLUSTER_HEAVY_METAL,
    "call the vatican": CLUSTER_HEAVY_METAL,
    # Dubstep & EDM
    "subtronics": CLUSTER_DUBSTEP_EDM,
    "excision": CLUSTER_DUBSTEP_EDM,
    "svdden death": CLUSTER_DUBSTEP_EDM,
    "samplifire": CLUSTER_DUBSTEP_EDM,
    "perry wayne": CLUSTER_DUBSTEP_EDM,
    "riot ten": CLUSTER_DUBSTEP_EDM,
    "nimda": CLUSTER_DUBSTEP_EDM,
    "infekt": CLUSTER_DUBSTEP_EDM,
    "hol!": CLUSTER_DUBSTEP_EDM,
    "kai wachi": CLUSTER_DUBSTEP_EDM,
    "must die!": CLUSTER_DUBSTEP_EDM,
    "the satan": CLUSTER_DUBSTEP_EDM,
    "dj törke": CLUSTER_DUBSTEP_EDM,
    "crankdat": CLUSTER_DUBSTEP_EDM,
    "marauda": CLUSTER_DUBSTEP_EDM,
    "marshmello": CLUSTER_DUBSTEP_EDM,
    "shiverz": CLUSTER_DUBSTEP_EDM,
    "skrillex": CLUSTER_DUBSTEP_EDM,
    "zomboy": CLUSTER_DUBSTEP_EDM,
    "subfiltronik": CLUSTER_DUBSTEP_EDM,
    "eptic": CLUSTER_DUBSTEP_EDM,
    "virtual riot": CLUSTER_DUBSTEP_EDM,
    "spag heddy": CLUSTER_DUBSTEP_EDM,
    "kompany": CLUSTER_DUBSTEP_EDM,
    "wooli": CLUSTER_DUBSTEP_EDM,
    "barely alive": CLUSTER_DUBSTEP_EDM,
    "ray volpe": CLUSTER_DUBSTEP_EDM,
    "space laces": CLUSTER_DUBSTEP_EDM,
    "stuca": CLUSTER_DUBSTEP_EDM,
    "bandlez": CLUSTER_DUBSTEP_EDM,
    "lil texas": CLUSTER_DUBSTEP_EDM,
    "the smell of males": CLUSTER_DUBSTEP_EDM,
    "midnight tyrannosaurus": CLUSTER_DUBSTEP_EDM,
    "the prodigy": CLUSTER_DUBSTEP_EDM,
    "ghengar": CLUSTER_DUBSTEP_EDM,
    "kanine": CLUSTER_DUBSTEP_EDM,
    "sisto": CLUSTER_DUBSTEP_EDM,
    "figure": CLUSTER_DUBSTEP_EDM,
    "nosphere": CLUSTER_DUBSTEP_EDM,
    "savxges": CLUSTER_DUBSTEP_EDM,
    "level up": CLUSTER_DUBSTEP_EDM,
    "tynan": CLUSTER_DUBSTEP_EDM,
    "calcium": CLUSTER_DUBSTEP_EDM,
    "viperactive": CLUSTER_DUBSTEP_EDM,
    "tekkschuster": CLUSTER_DUBSTEP_EDM,
    "tekkstreetboyz": CLUSTER_DUBSTEP_EDM,
    "lokimitdermaske": CLUSTER_DUBSTEP_EDM,
    "bear grillz": CLUSTER_DUBSTEP_EDM,
    "black sun empire": CLUSTER_DUBSTEP_EDM,
    "hurtbox": CLUSTER_DUBSTEP_EDM,
    "overbreak": CLUSTER_DUBSTEP_EDM,
    "dj перекрыт": CLUSTER_DUBSTEP_EDM,
    "dj dr4gm4shroom": CLUSTER_DUBSTEP_EDM,
    "dj univxrsel": CLUSTER_DUBSTEP_EDM,
    # Phonk & Memphis
    "sematary": CLUSTER_PHONK_MEMPHIS,
    "ghostemane": CLUSTER_PHONK_MEMPHIS,
    "bbbernard": CLUSTER_PHONK_MEMPHIS,
    "dekma": CLUSTER_PHONK_MEMPHIS,
    "bones": CLUSTER_PHONK_MEMPHIS,
    "plxyamishikii": CLUSTER_PHONK_MEMPHIS,
    "velial squad": CLUSTER_PHONK_MEMPHIS,
    "jdflag": CLUSTER_PHONK_MEMPHIS,
    "1nzzident": CLUSTER_PHONK_MEMPHIS,
    "nxneshxffle": CLUSTER_PHONK_MEMPHIS,
    "memphis cult": CLUSTER_PHONK_MEMPHIS,
    "city morgue": CLUSTER_PHONK_MEMPHIS,
    "saymooon": CLUSTER_PHONK_MEMPHIS,
    "redzed": CLUSTER_PHONK_MEMPHIS,
    "bakkerphonk": CLUSTER_PHONK_MEMPHIS,
    "kordhell": CLUSTER_PHONK_MEMPHIS,
    "dvrst": CLUSTER_PHONK_MEMPHIS,
    "pharmacist": CLUSTER_PHONK_MEMPHIS,
    "freddie dredd": CLUSTER_PHONK_MEMPHIS,
    "scarlxrd": CLUSTER_PHONK_MEMPHIS,
    "zillakami": CLUSTER_PHONK_MEMPHIS,
    "sosmula": CLUSTER_PHONK_MEMPHIS,
    "haunted mound": CLUSTER_PHONK_MEMPHIS,
    "hackle": CLUSTER_PHONK_MEMPHIS,
    "buckshot": CLUSTER_PHONK_MEMPHIS,
    "devilish trio": CLUSTER_PHONK_MEMPHIS,
    "baker ya maker": CLUSTER_PHONK_MEMPHIS,
    "hydra mane": CLUSTER_PHONK_MEMPHIS,
    "sxmpra": CLUSTER_PHONK_MEMPHIS,
    "shadowraze": CLUSTER_PHONK_MEMPHIS,
    "cupreous": CLUSTER_PHONK_MEMPHIS,
    "dmtboy": CLUSTER_PHONK_MEMPHIS,
    "zotiyac": CLUSTER_PHONK_MEMPHIS,
    "pluggstar": CLUSTER_PHONK_MEMPHIS,
    "$uicideboy$": CLUSTER_PHONK_MEMPHIS,
    "suicideboys": CLUSTER_PHONK_MEMPHIS,
    "makaveligodd": CLUSTER_PHONK_MEMPHIS,
    "redfxrd": CLUSTER_PHONK_MEMPHIS,
    "makishima": CLUSTER_PHONK_MEMPHIS,
    "erbes": CLUSTER_PHONK_MEMPHIS,
    "gouki": CLUSTER_PHONK_MEMPHIS,
    "rory in early 20s": CLUSTER_PHONK_MEMPHIS,
    "skrpump": CLUSTER_PHONK_MEMPHIS,
    "deejaynosex": CLUSTER_PHONK_MEMPHIS,
    "dexdbell": CLUSTER_PHONK_MEMPHIS,
    "kursani": CLUSTER_PHONK_MEMPHIS,
    "valoder": CLUSTER_PHONK_MEMPHIS,
    "misterl0l": CLUSTER_PHONK_MEMPHIS,
    "dmitry.rx": CLUSTER_PHONK_MEMPHIS,
    "sql2vd": CLUSTER_PHONK_MEMPHIS,
    "ythotkk": CLUSTER_PHONK_MEMPHIS,
    # Hip-Hop & Trap
    "three 6 mafia": CLUSTER_HIPHOP_TRAP,
    "big baby tape": CLUSTER_HIPHOP_TRAP,
    "og buda": CLUSTER_HIPHOP_TRAP,
    "towa": CLUSTER_HIPHOP_TRAP,
    "chief keef": CLUSTER_HIPHOP_TRAP,
    "juicy j": CLUSTER_HIPHOP_TRAP,
    "aarne": CLUSTER_HIPHOP_TRAP,
    "ак-47": CLUSTER_HIPHOP_TRAP,
    "waka flocka flame": CLUSTER_HIPHOP_TRAP,
    "kizaru": CLUSTER_HIPHOP_TRAP,
    "gucci mane": CLUSTER_HIPHOP_TRAP,
    "4к": CLUSTER_HIPHOP_TRAP,
    "gone.fludd": CLUSTER_HIPHOP_TRAP,
    "lex luger": CLUSTER_HIPHOP_TRAP,
    "pastor troy": CLUSTER_HIPHOP_TRAP,
    "lil jon": CLUSTER_HIPHOP_TRAP,
    "50 cent": CLUSTER_HIPHOP_TRAP,
    "snoop dogg": CLUSTER_HIPHOP_TRAP,
    "lil wayne": CLUSTER_HIPHOP_TRAP,
    "rick ross": CLUSTER_HIPHOP_TRAP,
    "dmx": CLUSTER_HIPHOP_TRAP,
    "n.w.a": CLUSTER_HIPHOP_TRAP,
    "1.kla$": CLUSTER_HIPHOP_TRAP,
    "toxi$": CLUSTER_HIPHOP_TRAP,
    "unki": CLUSTER_HIPHOP_TRAP,
    "alblak 52": CLUSTER_HIPHOP_TRAP,
    "скриптонит": CLUSTER_HIPHOP_TRAP,
    "friendly thug 52 ngg": CLUSTER_HIPHOP_TRAP,
    "the notorious b.i.g.": CLUSTER_HIPHOP_TRAP,
    "birdman": CLUSTER_HIPHOP_TRAP,
    "crime mob": CLUSTER_HIPHOP_TRAP,
    "t.i.": CLUSTER_HIPHOP_TRAP,
    "project pat": CLUSTER_HIPHOP_TRAP,
    "gangsta boo": CLUSTER_HIPHOP_TRAP,
    "lord infamous": CLUSTER_HIPHOP_TRAP,
    "dj paul": CLUSTER_HIPHOP_TRAP,
    "koopsta knicca": CLUSTER_HIPHOP_TRAP,
    "crunchy black": CLUSTER_HIPHOP_TRAP,
    "travis scott": CLUSTER_HIPHOP_TRAP,
    "playboi carti": CLUSTER_HIPHOP_TRAP,
    "21 savage": CLUSTER_HIPHOP_TRAP,
    "young thug": CLUSTER_HIPHOP_TRAP,
    "future": CLUSTER_HIPHOP_TRAP,
    "kodak black": CLUSTER_HIPHOP_TRAP,
    "tay-k": CLUSTER_HIPHOP_TRAP,
    "tay - k": CLUSTER_HIPHOP_TRAP,
    "рэ.прэса": CLUSTER_HIPHOP_TRAP,
    "ken car$on": CLUSTER_HIPHOP_TRAP,
    "ken carson": CLUSTER_HIPHOP_TRAP,
    "destroy lonely": CLUSTER_HIPHOP_TRAP,
    "homixide gang": CLUSTER_HIPHOP_TRAP,
    "yeat": CLUSTER_HIPHOP_TRAP,
    "lil uzi vert": CLUSTER_HIPHOP_TRAP,
    "juice wrld": CLUSTER_HIPHOP_TRAP,
    "don omar": CLUSTER_HIPHOP_TRAP,
    "tego calderón": CLUSTER_HIPHOP_TRAP,
    "slim thug": CLUSTER_HIPHOP_TRAP,
    "chamillionaire": CLUSTER_HIPHOP_TRAP,
    "krayzie bone": CLUSTER_HIPHOP_TRAP,
    "eminem": CLUSTER_HIPHOP_TRAP,
    "кровосток": CLUSTER_HIPHOP_TRAP,
    "scally milano": CLUSTER_HIPHOP_TRAP,
    "паша техник": CLUSTER_HIPHOP_TRAP,
    "thrill pill": CLUSTER_HIPHOP_TRAP,
    "платина": CLUSTER_HIPHOP_TRAP,
    "idoleast": CLUSTER_HIPHOP_TRAP,
    "гио пика": CLUSTER_HIPHOP_TRAP,
    "icegergert": CLUSTER_HIPHOP_TRAP,
    # Rock & Alternative
    "radiohead": CLUSTER_ROCK_ALTERNATIVE,
    "nirvana": CLUSTER_ROCK_ALTERNATIVE,
    "deftones": CLUSTER_ROCK_ALTERNATIVE,
    "linkin park": CLUSTER_ROCK_ALTERNATIVE,
    "three days grace": CLUSTER_ROCK_ALTERNATIVE,
    "bring me the horizon": CLUSTER_ROCK_ALTERNATIVE,
    "король и шут": CLUSTER_ROCK_ALTERNATIVE,
    "кино": CLUSTER_ROCK_ALTERNATIVE,
    "би-2": CLUSTER_ROCK_ALTERNATIVE,
    "сплин": CLUSTER_ROCK_ALTERNATIVE,
    "молчат дома": CLUSTER_ROCK_ALTERNATIVE,
    "перемотка": CLUSTER_ROCK_ALTERNATIVE,
    "green day": CLUSTER_ROCK_ALTERNATIVE,
    "blink-182": CLUSTER_ROCK_ALTERNATIVE,
    "papa roach": CLUSTER_ROCK_ALTERNATIVE,
    "skillet": CLUSTER_ROCK_ALTERNATIVE,
    "my chemical romance": CLUSTER_ROCK_ALTERNATIVE,
    "hollywood undead": CLUSTER_ROCK_ALTERNATIVE,
    "twenty one pilots": CLUSTER_ROCK_ALTERNATIVE,
    "the offing": CLUSTER_ROCK_ALTERNATIVE,
    "muse": CLUSTER_ROCK_ALTERNATIVE,
    "the offspring": CLUSTER_ROCK_ALTERNATIVE,
    "system of a down": CLUSTER_ROCK_ALTERNATIVE,
}


class GenreClassifier:
    def __init__(self, db_path: str = CACHE_DB_PATH) -> None:
        self.db_path = db_path
        self._mem_cache: Dict[str, Tuple[str, List[str]]] = {}
        self._init_db()
        self._load_memory_cache()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS artist_cache (
                    artist_key TEXT PRIMARY KEY,
                    artist_name TEXT,
                    cluster TEXT,
                    tags_json TEXT,
                    source TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def _load_memory_cache(self) -> None:
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT artist_key, cluster, tags_json FROM artist_cache")
                for key, cluster, tags_json in cursor.fetchall():
                    tags = json.loads(tags_json) if tags_json else []
                    self._mem_cache[key] = (cluster, tags)
        except Exception:
            pass

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
        key = artist_name.strip().lower()
        self._mem_cache[key] = (cluster, tags)
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO artist_cache (artist_key, artist_name, cluster, tags_json, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key, artist_name.strip(), cluster, json.dumps(tags, ensure_ascii=False), source),
            )
            conn.commit()


    def save_cached_artists_batch(self, batch: List[Tuple[str, str, List[str], str]]) -> None:
        if not batch:
            return
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO artist_cache (artist_key, artist_name, cluster, tags_json, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        art.strip().lower(),
                        art.strip(),
                        cl,
                        json.dumps(tags, ensure_ascii=False),
                        src,
                    )
                    for art, cl, tags, src in batch
                ],
            )
            conn.commit()

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
                toptags = data.get("toptags", {}).get("tag", [])
                tags: List[str] = []
                for item in toptags:
                    if isinstance(item, dict) and "name" in item:
                        tags.append(str(item["name"]).strip().lower())
                return tags
        except Exception:
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
