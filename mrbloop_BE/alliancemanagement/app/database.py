"""
Database connection module.

Manages the async aiomysql pool (same pattern as discordbot core/db.py).
The pool is created at API startup in main.py's lifespan.
"""

import aiomysql
import logging
from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

_pool: aiomysql.Pool | None = None


async def create_pool() -> aiomysql.Pool:
    global _pool
    _pool = await aiomysql.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        minsize=1,
        maxsize=10,
        cursorclass=aiomysql.DictCursor,
    )
    logger.info("DB pool created → %s:%s/%s", DB_HOST, DB_PORT, DB_NAME)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        logger.info("DB pool closed")
        _pool = None


def get_pool() -> aiomysql.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not created. Call create_pool() first.")
    return _pool
