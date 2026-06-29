import logging
import calendar

import discord
from discord import app_commands
from discord.ext import commands

from utils import Region, REGION_LABELS
from .repository import BirthdayRepository
from .service import BirthdayService

logger = logging.getLogger(__name__)

MONTH_CHOICES = [
    app_commands.Choice(name=calendar.month_name[i], value=i)
    for i in range(1, 13)
]

REGION_CHOICES = [
    app_commands.Choice(name=REGION_LABELS[Region.AMERICAS], value=Region.AMERICAS.value),
    app_commands.Choice(name=REGION_LABELS[Region.EMEA],     value=Region.EMEA.value),
    app_commands.Choice(name=REGION_LABELS[Region.APAC],     value=Region.APAC.value),
]


class BirthdayCog(commands.GroupCog, name="birthday"):
    def __init__(self, bot: commands.Bot, service: BirthdayService, repo: BirthdayRepository):
        self.bot = bot
        self.service = service
        self.repo = repo
        super().__init__()

    @app_commands.command(name="set", description="Save your birthday information.")
    @app_commands.describe(
        day="Day of your birthday (1-31)",
        month="Month of your birthday",
        region="Your region (determines when you receive the birthday message)",
    )
    @app_commands.choices(month=MONTH_CHOICES, region=REGION_CHOICES)
    async def set_birthday(
        self,
        interaction: discord.Interaction,
        day: app_commands.Range[int, 1, 31],
        month: app_commands.Choice[int],
        region: app_commands.Choice[str],
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        max_day = calendar.monthrange(2000, month.value)[1]
        if day > max_day:
            await interaction.followup.send(
                f"❌ {month.name} has a maximum of **{max_day}** days.", ephemeral=True
            )
            return

        await self.repo.upsert_guild(interaction.guild_id, interaction.guild.name)
        await self.repo.set_birthday(
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            birth_month=month.value,
            birth_day=day,
            region=region.value,
        )

        await interaction.followup.send(
            f"✅ Your birthday has been saved: **{day} {month.name}** "
            f"(region: `{region.name}`)",
            ephemeral=True,
        )

    @app_commands.command(name="delete", description="Delete your birthday information.")
    async def delete_birthday(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        deleted = await self.repo.delete_birthday(interaction.user.id, interaction.guild_id)
        if deleted:
            await interaction.followup.send("🗑️ Your birthday has been deleted.", ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ I don't have your birthday saved. Use `/birthday set` to add it.",
                ephemeral=True,
            )

    @app_commands.command(name="view", description="View your saved birthday.")
    async def view_birthday(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        entry = await self.repo.get_birthday(interaction.user.id, interaction.guild_id)

        if not entry:
            await interaction.followup.send(
                "❌ You haven't set your birthday yet. Use `/birthday set` to add it.",
                ephemeral=True,
            )
            return

        region_label = REGION_LABELS.get(Region(entry["region"]), entry["region"])
        embed = discord.Embed(title="🎂 Your Birthday", color=discord.Color.blurple())
        embed.add_field(name="Date", value=f"{entry['birth_day']} {calendar.month_name[entry['birth_month']]}", inline=True)
        embed.add_field(name="Region", value=region_label, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="channel", description="(Admin) Set the channel for birthday messages.")
    @app_commands.describe(channel="The text channel for congratulations")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.repo.upsert_guild(interaction.guild_id, interaction.guild.name)
        await self.repo.set_birthday_channel(interaction.guild_id, channel.id)
        await interaction.followup.send(
            f"✅ Birthday messages will now be sent to {channel.mention}.", ephemeral=True
        )

    @set_channel.error
    async def set_channel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Manage Server** permissions to use this command.", ephemeral=True
            )
