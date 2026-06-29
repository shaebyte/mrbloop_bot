"""
Database connectie module.

Beheert de async aiomysql pool. De pool verbindt met het mrbloop_db
schema in de externe mrbloop_db MySQL instantie.
"""

import aiomysql
import logging
from config import settings

logger = logging.getLogger(__name__)

_pool: aiomysql.Pool | None = None


async def create_pool() -> aiomysql.Pool:
    global _pool
    _pool = await aiomysql.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        minsize=1,
        maxsize=settings.DB_POOL_SIZE,
        cursorclass=aiomysql.DictCursor,
    )
    logger.info(
        "DB pool created → %s:%s/%s (max %d conn)",
        settings.DB_HOST, settings.DB_PORT, settings.DB_NAME, settings.DB_POOL_SIZE,
    )
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
