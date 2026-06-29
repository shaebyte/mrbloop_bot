"""
Bot – centrale klasse die alles samenhoudt.
"""

import logging
import discord
from discord.ext import commands

from core.db import create_pool, close_pool
from core.scheduler import BotScheduler
from config import settings
from features.birthdays import BirthdayCog, BirthdayService, BirthdayRepository

logger = logging.getLogger(__name__)


class MrBloopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        self.scheduler = BotScheduler()
        self.birthday_repo = BirthdayRepository()
        self.birthday_service = BirthdayService(self, self.birthday_repo)

    async def setup_hook(self) -> None:
        logger.info("Loading cogs...")
        await self.add_cog(
            BirthdayCog(self, self.birthday_service, self.birthday_repo)
        )
        await self.tree.sync()
        logger.info("Slash commands synced")

    async def on_ready(self) -> None:
        logger.info("Online as %s (ID: %s) on %d servers", self.user, self.user.id, len(self.guilds))

        await create_pool()

        for guild in self.guilds:
            await self.birthday_repo.upsert_guild(guild.id, guild.name)

        self.scheduler.add_birthday_jobs(self.birthday_service.check_and_greet_birthdays)
        self.scheduler.start()

        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="Hello 🎂")
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.birthday_repo.upsert_guild(guild.id, guild.name)
        logger.info("New server: %s (%s)", guild.name, guild.id)

    async def close(self) -> None:
        logger.info("Bot is closing...")
        self.scheduler.stop()
        await close_pool()
        await super().close()

    async def on_error(self, event: str, *args, **kwargs) -> None:
        logger.exception("Unexpected error in event: %s", event)

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        self.tree.clear_commands(guild=discord.Object(id=ctx.guild.id))
        await self.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.send("✅ Commands cleared and resynced!")
