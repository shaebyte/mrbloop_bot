import logging
from core.db import get_pool

logger = logging.getLogger(__name__)


class GuildRepository:
    """Guild-identiteit + generieke feature-toggles, gedeeld door alle features."""

    async def upsert_guild(self, guild_id: int, guild_name: str) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_guilds (guild_id, guild_name, is_active)
                    VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE guild_name = VALUES(guild_name), is_active = 1
                    """,
                    (guild_id, guild_name),
                )

    async def deactivate_guild(self, guild_id: int) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE dbot_guilds SET is_active = 0 WHERE guild_id = %s",
                    (guild_id,),
                )

    async def get_feature(self, guild_id: int, feature_key: str) -> dict | None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM dbot_guild_features WHERE guild_id = %s AND feature_key = %s",
                    (guild_id, feature_key),
                )
                return await cur.fetchone()

    async def is_feature_enabled(self, guild_id: int, feature_key: str) -> bool:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT gf.enabled
                    FROM dbot_guild_features gf
                    JOIN dbot_features f ON f.feature_key = gf.feature_key
                    WHERE gf.guild_id = %s AND gf.feature_key = %s AND f.is_globally_enabled = 1
                    """,
                    (guild_id, feature_key),
                )
                row = await cur.fetchone()
                return bool(row and row["enabled"])

    async def set_feature_channel(self, guild_id: int, feature_key: str, channel_id: int) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_guild_features (guild_id, feature_key, enabled, channel_id)
                    VALUES (%s, %s, 1, %s)
                    ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id), enabled = 1
                    """,
                    (guild_id, feature_key, channel_id),
                )

    async def set_feature_enabled(self, guild_id: int, feature_key: str, enabled: bool) -> None:
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dbot_guild_features (guild_id, feature_key, enabled)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)
                    """,
                    (guild_id, feature_key, enabled),
                )

    async def get_guilds_with_feature_enabled(self, feature_key: str) -> list[dict]:
        """Voor scheduled jobs: gebruikt idx_feature_enabled i.p.v. een full scan."""
        async with get_pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT gf.guild_id, gf.channel_id
                    FROM dbot_guild_features gf
                    JOIN dbot_features f ON f.feature_key = gf.feature_key
                    WHERE gf.feature_key = %s AND gf.enabled = 1 AND f.is_globally_enabled = 1
                    """,
                    (feature_key,),
                )
                return await cur.fetchall()