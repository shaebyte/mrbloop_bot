import logging

import discord

from config import settings
from utils import Region, get_region_date
from .repository import BirthdayRepository

logger = logging.getLogger(__name__)


class BirthdayService:
    def __init__(self, bot: discord.Client, repo: BirthdayRepository):
        self.bot = bot
        self.repo = repo

    async def check_and_greet_birthdays(self, region: str) -> None:
        date = get_region_date(Region(region))
        logger.debug("Birthday check: region=%s date=%s", region, date)

        entries = await self.repo.get_birthdays_for_region(
            region=region,
            month=date.month,
            day=date.day,
            year=date.year,
        )
        for entry in entries:
            try:
                await self._process_entry(entry)
            except Exception as exc:
                logger.error(
                    "Error processing entry user=%s guild=%s: %s",
                    entry.get("user_id"), entry.get("guild_id"), exc, exc_info=True,
                )

    async def _process_entry(self, entry: dict) -> None:
        guild = self.bot.get_guild(entry["guild_id"])
        if not guild:
            return

        channel = await self._resolve_channel(guild, entry.get("channel_id"))
        if not channel:
            return

        member = guild.get_member(entry["user_id"])
        if not member:
            return

        await self._send_birthday_message(channel, member)
        await self.repo.mark_greeted(entry["user_id"], entry["guild_id"], entry["_greet_year"])
        logger.info("Congratulated: %s in %s", member.display_name, guild.name)

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
        await channel.send(content=f"@everyone 🎊 Happy Birthday {member.mention}! 🎊", embed=embed)