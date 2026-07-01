"""CallGuard slash commands — /callguard and /防盜."""
from __future__ import annotations

import discord
from discord import app_commands

from monster_ai.modules.discord.guard.ui.embeds import alert_embed, callguard_alert_embed

callguard_group = app_commands.Group(name="callguard", description="Monster CallGuard 來電防護")
fangdao_group = app_commands.Group(name="防盜", description="Monster CallGuard 防盜警報（中文）")


def _client(interaction: discord.Interaction):
    svc = getattr(interaction.client, "discord_service", None)
    if svc:
        return svc._monster_client  # noqa: SLF001
    return None


async def _cg_status_impl(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    client = _client(interaction)
    if not client:
        await interaction.followup.send("CallGuard client 未連接。", ephemeral=True)
        return
    data = await client.callguard_status()
    enabled = data.get("enabled", False)
    embed = alert_embed(
        "CallGuard 狀態",
        f"**已啟用：** `{'是' if enabled else '否'}`\n"
        f"**狀態：** `{data.get('status', '未知')}`\n"
        f"**威脅資料庫：** `{data.get('threat_db_version', '—')}`",
        level="info" if enabled else "warn",
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


async def _cg_reports_impl(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    client = _client(interaction)
    if not client:
        await interaction.followup.send("CallGuard client 未連接。", ephemeral=True)
        return
    reports = await client.callguard_reports(limit=5)
    if not reports:
        embed = alert_embed("CallGuard 報告", "尚無報告。", level="info")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    embeds = [callguard_alert_embed(r) for r in reports[:3]]
    await interaction.followup.send(embeds=embeds, ephemeral=True)


@callguard_group.command(name="status", description="CallGuard 引擎狀態")
async def cg_status(interaction: discord.Interaction) -> None:
    await _cg_status_impl(interaction)


@callguard_group.command(name="reports", description="最近 CallGuard 報告")
async def cg_reports(interaction: discord.Interaction) -> None:
    await _cg_reports_impl(interaction)


@fangdao_group.command(name="status", description="CallGuard 引擎狀態")
async def fangdao_status(interaction: discord.Interaction) -> None:
    await _cg_status_impl(interaction)


@fangdao_group.command(name="reports", description="最近 CallGuard 報告")
async def fangdao_reports(interaction: discord.Interaction) -> None:
    await _cg_reports_impl(interaction)


async def setup(bot: discord.Client) -> None:
    bot.tree.add_command(callguard_group)
    bot.tree.add_command(fangdao_group)