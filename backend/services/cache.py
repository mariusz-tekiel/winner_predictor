import json
import time
import aiosqlite
from app.config import settings

DB_PATH = settings.cache_db


async def _init_db(db: aiosqlite.Connection):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            url TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            fetched_at REAL NOT NULL,
            ttl_seconds INTEGER NOT NULL
        )
    """)
    await db.commit()


async def cache_get(url: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        await _init_db(db)
        async with db.execute(
            "SELECT response_json, fetched_at, ttl_seconds FROM api_cache WHERE url = ?",
            (url,)
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return None

    response_json, fetched_at, ttl_seconds = row
    if time.time() - fetched_at > ttl_seconds:
        return None

    return json.loads(response_json)


async def cache_set(url: str, data: dict, ttl_seconds: int = 3600):
    async with aiosqlite.connect(DB_PATH) as db:
        await _init_db(db)
        await db.execute(
            """INSERT OR REPLACE INTO api_cache (url, response_json, fetched_at, ttl_seconds)
               VALUES (?, ?, ?, ?)""",
            (url, json.dumps(data), time.time(), ttl_seconds)
        )
        await db.commit()


async def cache_clear_expired():
    async with aiosqlite.connect(DB_PATH) as db:
        await _init_db(db)
        await db.execute(
            "DELETE FROM api_cache WHERE (? - fetched_at) > ttl_seconds",
            (time.time(),)
        )
        await db.commit()
