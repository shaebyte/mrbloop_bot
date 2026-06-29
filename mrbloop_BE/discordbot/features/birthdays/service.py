import logging
from datetime import datetime

import discord

from config import settings
from utils import is_birthday_time
from .repository import BirthdayRepository

logger = logging.getLogger(__name__)


class BirthdayService:
    def __init__(self, bot: discord.Client, repo: BirthdayRepository):
        self.bot = bot
        self.repo = repo

    async def check_and_greet_birthdays(self) -> None:
        """Polls every minute. Congratulates users who are celebrating their birthday at local 00:15."""
        logger.debug("Birthday check...")
        for entry in await self.repo.get_all_birthdays_with_timezone():
            try:
                await self._process_entry(entry)
            except Exception as exc:
                logger.error("Error processing entry id=%s: %s", entry.get("id"), exc, exc_info=True)

    async def _process_entry(self, entry: dict) -> None:
        if not is_birthday_time(
            tz_name=entry["timezone"],
            birth_month=entry["birth_month"],
            birth_day=entry["birth_day"],
            greet_hour=settings.BIRTHDAY_GREET_HOUR,
            greet_minute=settings.BIRTHDAY_GREET_MINUTE,
        ):
            return

        guild = self.bot.get_guild(entry["guild_id"])
        if not guild:
            return

        channel = await self._resolve_channel(guild, entry.get("birthday_channel_id"))
        if not channel:
            return

        member = guild.get_member(entry["user_id"])
        if not member:
            return

        await self._send_birthday_message(channel, member)
        await self.repo.mark_greeted(entry["id"], datetime.utcnow().year)
        logger.info("Congratulated: %s in %s (%s)", member.display_name, guild.name, entry["timezone"])

    async def _resolve_channel(
        self, guild: discord.Guild, channel_id: int | None
    ) -> discord.TextChannel | None:
        if channel_id:
            ch = guild.get_channel(channel_id)
            if isinstance(ch, discord.TextChannel):
                return ch
        return next(
            (c for c in guild.text_channels if c.name.lower() == settings.BIRTHDAY_CHANNEL_NAME.lower()),
            None,
        )

    @staticmethod
    async def _send_birthday_message(channel: discord.TextChannel, member: discord.Member) -> None:
        embed = discord.Embed(
            title="🎂 Happy Birthday!",
            description=f"Today is the birthday of {member.mention}! 🎉\nWish them a happy birthday!",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"🎈 Hope you have a great day, {member.display_name}!")
        await channel.send(content=f"🎊 Happy Birthday {member.mention}! 🎊", embed=embed)
