"""Top-level /status and /about commands."""
from __future__ import annotations

import discord
from discord import app_commands

from monster_ai.modules.discord.guard.ui.embeds import about_embed, status_embed


@app_commands.command(name="status", description="MonsterGuard v2.0 健康儀表板")
async def global_status(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    bot = interaction.client
    svc = getattr(bot, "discord_service", None)
    connected = bot.is_ready() and not bot.is_closed()

    resilience = {}
    monster_ai = {}
    callguard = {}
    if svc:
        gs = svc.guard_status()
        resilience = gs.get("resilience", {})
        monster_ai = gs.get("monster_ai", {})
        callguard = gs.get("callguard_bridge", {})
        connected = gs.get("connected", connected)

    guard_stats = bot.status_dict() if hasattr(bot, "status_dict") else {}
    embed = status_embed(
        connected=connected,
        resilience=resilience,
        monster_ai=monster_ai,
        callguard=callguard,
        guard_stats=guard_stats,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@app_commands.command(name="about", description="MonsterGuard 版本與開發者資訊")
async def about_cmd(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(embed=about_embed(), ephemeral=True)


async def setup(bot: discord.Client) -> None:
    bot.tree.add_command(global_status)
    bot.tree.add_command(about_cmd)