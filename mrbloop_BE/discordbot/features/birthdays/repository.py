import logging
from core.db import get_pool

logger = logging.getLogger(__name__)

FEATURE_KEY = "birthday"


class BirthdayRepository:

    async def set_birthday(self, user_id: int, birth_month: int, birth_day: int, region: str) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_users (user_id, birth_month, birth_day, region)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        birth_month = VALUES(birth_month),
                        birth_day   = VALUES(birth_day),
                        region      = VALUES(region)
                    """,
                    (user_id, birth_month, birth_day, region),
                )
                await cur.execute(
                    "UPDATE dbot_user_birthday_status SET last_greeted_year = NULL WHERE user_id = %s",
                    (user_id,),
                )
        logger.info("Birthday saved: user=%s %s/%s region=%s", user_id, birth_month, birth_day, region)

    async def opt_in(self, user_id: int, guild_id: int) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_user_birthday_status (user_id, guild_id, opted_in)
                    VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE opted_in = 1
                    """,
                    (user_id, guild_id),
                )

    async def opt_out(self, user_id: int, guild_id: int) -> bool:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM dbot_user_birthday_status WHERE user_id = %s AND guild_id = %s",
                    (user_id, guild_id),
                )
                return cur.rowcount > 0

    async def get_birthday(self, user_id: int) -> dict | None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM dbot_users WHERE user_id = %s AND birth_month IS NOT NULL",
                    (user_id,),
                )
                return await cur.fetchone()

    async def get_birthdays_for_region(
        self, region: str, month: int, day: int, year: int
    ) -> list[dict]:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT u.user_id, s.guild_id, gf.channel_id, %s AS _greet_year
                    FROM dbot_users u
                    JOIN dbot_user_birthday_status s ON s.user_id = u.user_id
                    JOIN dbot_guild_features gf
                        ON gf.guild_id = s.guild_id AND gf.feature_key = %s
                    JOIN dbot_features f ON f.feature_key = gf.feature_key
                    WHERE u.region = %s
                      AND u.birth_month = %s
                      AND u.birth_day = %s
                      AND s.opted_in = 1
                      AND gf.enabled = 1
                      AND f.is_globally_enabled = 1
                      AND (s.last_greeted_year IS NULL OR s.last_greeted_year != %s)
                    """,
                    (year, FEATURE_KEY, region, month, day, year),
                )
                return await cur.fetchall()

    async def mark_greeted(self, user_id: int, guild_id: int, year: int) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE dbot_user_birthday_status SET last_greeted_year = %s WHERE user_id = %s AND guild_id = %s",
                    (year, user_id, guild_id),
                )