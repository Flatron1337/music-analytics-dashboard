import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "genre_cache.sqlite")


def get_database_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if "sslmode=" not in url and not url.startswith("sqlite"):
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
    return url



def _get_pg_connection():
    import psycopg2
    db_url = get_database_url()
    return psycopg2.connect(db_url, connect_timeout=10)


def init_db(db_path: str = DEFAULT_SQLITE_PATH) -> str:
    """Инициализирует таблицу artist_cache в PostgreSQL или локальном SQLite."""
    db_url = get_database_url()
    if db_url:
        try:
            with _get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS artist_cache (
                            artist_key VARCHAR(255) PRIMARY KEY,
                            artist_name VARCHAR(255) NOT NULL,
                            cluster VARCHAR(100) NOT NULL,
                            tags_json TEXT,
                            source VARCHAR(50) NOT NULL,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
            return "postgresql"
        except Exception as e:
            logger.warning("Ошибка инициализации PostgreSQL: %s. Переход на SQLite.", e)

    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS artist_cache (
                artist_key TEXT PRIMARY KEY,
                artist_name TEXT NOT NULL,
                cluster TEXT NOT NULL,
                tags_json TEXT,
                source TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    return "sqlite"


def load_all_cached_artists(db_path: str = DEFAULT_SQLITE_PATH) -> Dict[str, Tuple[str, List[str]]]:
    """Загружает весь кэш артистов в память из активной БД."""
    result: Dict[str, Tuple[str, List[str]]] = {}
    db_url = get_database_url()

    if db_url:
        try:
            with _get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT artist_key, cluster, tags_json FROM artist_cache")
                    for k, cl, tj in cur.fetchall():
                        tags = json.loads(tj) if tj else []
                        result[k] = (cl, tags)
            return result
        except Exception as e:
            logger.warning("Не удалось прочитать кэш из PostgreSQL: %s", e)

    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path, timeout=20.0) as conn:
                cur = conn.cursor()
                cur.execute("SELECT artist_key, cluster, tags_json FROM artist_cache")
                for k, cl, tj in cur.fetchall():
                    tags = json.loads(tj) if tj else []
                    result[k] = (cl, tags)
        except Exception as e:
            logger.warning("Не удалось прочитать кэш из SQLite: %s", e)

    return result


def fetch_unresolved_artists(db_path: str = DEFAULT_SQLITE_PATH) -> List[Tuple[str, str]]:
    """Возвращает список неразмеченных артистов для AI-классификации."""
    db_url = get_database_url()
    if db_url:
        try:
            with _get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT artist_key, artist_name FROM artist_cache WHERE source = 'unresolved'")
                    return cur.fetchall()
        except Exception as e:
            logger.warning("Ошибка выборки неразмеченных артистов из PostgreSQL: %s", e)

    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path, timeout=20.0) as conn:
                cur = conn.cursor()
                cur.execute("SELECT artist_key, artist_name FROM artist_cache WHERE source = 'unresolved'")
                return cur.fetchall()
        except Exception as e:
            logger.warning("Ошибка выборки неразмеченных артистов из SQLite: %s", e)
    return []


def _save_batch_pg(batch: List[Tuple[str, str, str, str, str]]) -> bool:
    try:
        with _get_pg_connection() as conn:
            with conn.cursor() as cur:
                query = """
                INSERT INTO artist_cache (artist_key, artist_name, cluster, tags_json, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (artist_key) DO UPDATE
                SET artist_name = EXCLUDED.artist_name,
                    cluster = EXCLUDED.cluster,
                    tags_json = EXCLUDED.tags_json,
                    source = EXCLUDED.source,
                    updated_at = CURRENT_TIMESTAMP;
                """
                cur.executemany(query, batch)
        return True
    except Exception as e:
        logger.warning("Ошибка пакетной записи в PostgreSQL: %s", e)
        return False


def _save_batch_sqlite(db_path: str, batch: List[Tuple[str, str, str, str, str]]) -> None:
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT OR REPLACE INTO artist_cache (artist_key, artist_name, cluster, tags_json, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            batch,
        )


def save_cached_artists_batch(batch: List[Tuple[str, str, List[str], str]], db_path: str = DEFAULT_SQLITE_PATH) -> int:
    """Сохраняет пакет артистов в БД (PostgreSQL с зеркалированием в SQLite)."""
    if not batch:
        return 0

    prepared = [
        (art.strip().lower(), art.strip(), cl, json.dumps(tags, ensure_ascii=False), src)
        for art, cl, tags, src in batch
    ]

    db_url = get_database_url()
    if db_url:
        _save_batch_pg(prepared)

    try:
        _save_batch_sqlite(db_path, prepared)
    except Exception as e:
        logger.debug("Зеркалирование в SQLite пропущено: %s", e)

    return len(prepared)


def get_db_stats(db_path: str = DEFAULT_SQLITE_PATH) -> Dict[str, Any]:
    """Возвращает текущую статистику базы данных артистов."""
    db_url = get_database_url()
    backend = "postgresql" if db_url else "sqlite"
    tot, unres, ai = 0, 0, 0

    if db_url:
        try:
            with _get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM artist_cache")
                    tot = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM artist_cache WHERE source = 'unresolved'")
                    unres = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM artist_cache WHERE source LIKE 'ai_%' OR source = 'ai'")
                    ai = cur.fetchone()[0]
            return {"backend": backend, "total": tot, "unresolved": unres, "ai_enriched": ai}
        except Exception as e:
            logger.debug("Ошибка получения статистики PostgreSQL: %s", e)

    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path, timeout=5.0) as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM artist_cache")
                tot = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM artist_cache WHERE source = 'unresolved'")
                unres = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM artist_cache WHERE source LIKE 'ai_%' OR source = 'ai'")
                ai = cur.fetchone()[0]
        except Exception as e:
            logger.debug("Ошибка получения статистики SQLite: %s", e)



    return {"backend": backend, "total": tot, "unresolved": unres, "ai_enriched": ai}



def sync_sqlite_to_postgres(db_path: str = DEFAULT_SQLITE_PATH) -> int:
    """Синхронизирует локальный SQLite кэш в PostgreSQL."""
    db_url = get_database_url()
    if not db_url or not os.path.exists(db_path):
        return 0

    init_db(db_path)
    items: List[Tuple[str, str, List[str], str]] = []
    with sqlite3.connect(db_path, timeout=20.0) as conn:
        cur = conn.cursor()
        cur.execute("SELECT artist_key, artist_name, cluster, tags_json, source FROM artist_cache")
        for _k, name, cl, tj, src in cur.fetchall():
            tags = json.loads(tj) if tj else []
            items.append((name, cl, tags, src))

    return save_cached_artists_batch(items, db_path)


if __name__ == "__main__":
    import sys
    status = get_db_stats()
    print("Database backend status:", status)
    if "--sync" in sys.argv:
        synced = sync_sqlite_to_postgres()
        print(f"Synced {synced} rows to active database.")

