"""SQLite-backed caching for HTTP requests and query results."""

import hashlib
import json
import sqlite3
import time
from typing import Any, Optional

from . import config


class Cache:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(config.CACHE_DB_PATH)
        self._init_db()

    def _init_db(self) -> None:
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)"
            )
            # Prune expired entries opportunistically
            conn.execute("DELETE FROM cache_entries WHERE expires_at < ?", (time.time(),))

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        cache_key = self._hash_key(key)
        now = time.time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data_json, expires_at FROM cache_entries WHERE cache_key = ?",
                    (cache_key,),
                )
                row = cursor.fetchone()
                if row and row[1] > now:
                    return json.loads(row[0])
        except Exception:
            return None
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = config.DEFAULT_CACHE_TTL_SECONDS) -> None:
        cache_key = self._hash_key(key)
        now = time.time()
        expires_at = now + ttl_seconds
        data_json = json.dumps(value, ensure_ascii=False)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO cache_entries (cache_key, data_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        data_json = excluded.data_json,
                        created_at = excluded.created_at,
                        expires_at = excluded.expires_at
                    """,
                    (cache_key, data_json, now, expires_at),
                )
        except Exception:
            pass

    def clear(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries")
        except Exception:
            pass


# Singleton instance
default_cache = Cache()
