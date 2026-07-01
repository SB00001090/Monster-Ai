"""Optional commercial trial reminders — disabled by default."""
from __future__ import annotations

import discord
from discord import app_commands

from monster_ai.modules.discord.guard.ui.embeds import alert_embed

PRICING = {
    "HK": "HKD 88/mo · 7-day free trial",
    "TW": "TWD 299/mo · 7-day free trial",
    "GLOBAL": "USD 12/mo · 7-day free trial",
}


@app_commands.command(name="pricing", description="MonsterGuard 區域定價（商業推廣）")
@app_commands.describe(region="HK / TW / GLOBAL")
async def pricing_cmd(interaction: discord.Interaction, region: str = "HK") -> None:
    key = region.upper()
    price = PRICING.get(key, PRICING["GLOBAL"])
    embed = alert_embed(
        f"MonsterGuard Pricing — {key}",
        f"{price}\n\n7 日免費試用後將收到提醒。本地部署無需訂閱。",
        level="info",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: discord.Client) -> None:
    bot.tree.add_command(pricing_cmd)