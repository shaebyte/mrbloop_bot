import aiomysql
from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


async def _connect() -> aiomysql.Connection:
    return await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        autocommit=False,
    )


async def save_gift_code(code: str) -> bool:
    """Saves a new gift code. Returns True if new, False if duplicate."""
    conn = await _connect()
    try:
        async with conn.cursor() as cur:
            try:
                await cur.execute("INSERT INTO arg_gift_codes (code) VALUES (%s)", (code,))
                await conn.commit()
                return True
            except aiomysql.IntegrityError:
                return False
    finally:
        conn.close()


async def get_accounts_to_redeem(code: str) -> list[dict]:
    """Returns all non-blacklisted accounts that haven't successfully redeemed this code."""
    conn = await _connect()
    try:
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
    finally:
        conn.close()


async def save_attempt(
    code: str,
    player_id: str,
    status: str,
    attempt_count: int = 1,
    error_message: str | None = None,
) -> None:
    conn = await _connect()
    try:
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
            await conn.commit()
    finally:
        conn.close()


async def cleanup_old_attempts(days: int = 3) -> None:
    conn = await _connect()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM arg_redeem_attempts WHERE redeemed_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
                (days,),
            )
            await conn.commit()
    finally:
        conn.close()
