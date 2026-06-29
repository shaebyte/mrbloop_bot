import logging
from datetime import datetime
from core.db import get_pool

logger = logging.getLogger(__name__)


class BirthdayRepository:

    async def upsert_guild(self, guild_id: int, guild_name: str) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_guilds (guild_id, guild_name)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE guild_name = VALUES(guild_name)
                    """,
                    (guild_id, guild_name),
                )

    async def set_birthday_channel(self, guild_id: int, channel_id: int) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE dbot_guilds SET birthday_channel_id = %s WHERE guild_id = %s",
                    (channel_id, guild_id),
                )

    async def get_guild(self, guild_id: int) -> dict | None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM dbot_guilds WHERE guild_id = %s", (guild_id,))
                return await cur.fetchone()

    async def set_birthday(
        self, user_id: int, guild_id: int,
        birth_month: int, birth_day: int, timezone: str,
    ) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_user_birthdays
                        (user_id, guild_id, birth_month, birth_day, timezone)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        birth_month       = VALUES(birth_month),
                        birth_day         = VALUES(birth_day),
                        timezone          = VALUES(timezone),
                        last_greeted_year = NULL
                    """,
                    (user_id, guild_id, birth_month, birth_day, timezone),
                )
        logger.info("Birthday saved: user=%s guild=%s %s/%s tz=%s",
                    user_id, guild_id, birth_month, birth_day, timezone)

    async def get_birthday(self, user_id: int, guild_id: int) -> dict | None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM dbot_user_birthdays WHERE user_id = %s AND guild_id = %s",
                    (user_id, guild_id),
                )
                return await cur.fetchone()

    async def delete_birthday(self, user_id: int, guild_id: int) -> bool:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM dbot_user_birthdays WHERE user_id = %s AND guild_id = %s",
                    (user_id, guild_id),
                )
                return cur.rowcount > 0

    async def get_all_birthdays_with_timezone(self) -> list[dict]:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT ub.*, g.birthday_channel_id
                    FROM dbot_user_birthdays ub
                    JOIN dbot_guilds g ON g.guild_id = ub.guild_id
                    """
                )
                return await cur.fetchall()

    async def mark_greeted(self, birthday_id: int, year: int) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE dbot_user_birthdays SET last_greeted_year = %s WHERE id = %s",
                    (year, birthday_id),
                )
