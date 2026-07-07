"""
Database connection module.

Manages the async aiomysql pool (same pattern as discordbot core/db.py and
alliancemanagement app/database.py). The pool is created once at API/poller
startup instead of opening a fresh connection per query.
"""

import logging
import aiomysql
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


async def save_gift_code(code: str) -> bool:
    """Saves a new gift code. Returns True if new, False if duplicate."""
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("INSERT INTO arg_gift_codes (code) VALUES (%s)", (code,))
                return True
            except aiomysql.IntegrityError:
                return False


async def get_accounts_to_redeem(code: str) -> list[dict]:
    """Returns all non-blacklisted accounts that haven't successfully redeemed this code."""
    async with get_pool().acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT a.player_id, a.name
                FROM arg_accounts a
                WHERE a.blacklisted = 0
                  AND NOT EXISTS (
                      SELECT 1 FROM arg_redeem_attempts ra
                      WHERE ra.player_id = a.player_id
                        AND ra.gift_code = %s
                        AND ra.status = 'success'
                  )
                """,
                (code,),
            )
            return await cur.fetchall()


async def save_attempt(
    code: str,
    player_id: str,
    status: str,
    attempt_count: int = 1,
    error_message: str | None = None,
) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO arg_redeem_attempts (gift_code, player_id, status, attempt_count, error_message)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status        = VALUES(status),
                    attempt_count = VALUES(attempt_count),
                    error_message = VALUES(error_message),
                    redeemed_at   = CURRENT_TIMESTAMP
                """,
                (code, player_id, status, attempt_count, error_message),
            )


async def cleanup_old_attempts(days: int = 3) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM arg_redeem_attempts WHERE redeemed_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
                (days,),
            )
