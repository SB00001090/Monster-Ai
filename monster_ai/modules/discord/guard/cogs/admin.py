"""MonsterGuard admin commands — status, restart, logs."""
from __future__ import annotations

import asyncio
import json

import discord

from monster_ai.modules.discord.guard.cogs.guard_group import guard_group
from monster_ai.modules.discord.guard.ui.embeds import status_embed


@guard_group.command(name="status", description="查看 MonsterGuard 保護狀態（v2.0）")
async def guard_status(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    bot = interaction.client
    status = bot.status_dict()  # type: ignore[attr-defined]
    store = bot.guild_store  # type: ignore[attr-defined]
    guild_id = interaction.guild_id or 0
    cfg = await store.get(guild_id)
    blocked_24h = await asyncio.to_thread(
        bot.privacy_log.count_recent, guild_id, 24  # type: ignore[attr-defined]
    )

    svc = getattr(bot, "discord_service", None)
    connected = bot.is_ready()
    resilience = {}
    monster_ai = {}
    callguard = {}
    if svc:
        gs = svc.guard_status()
        connected = gs.get("connected", connected)
        resilience = gs.get("resilience", {})
        monster_ai = gs.get("monster_ai", {})
        callguard = gs.get("callguard_bridge", {})

    embed = status_embed(
        connected=connected,
        resilience=resilience,
        monster_ai=monster_ai,
        callguard=callguard,
        guard_stats={**status, "blocked_24h": blocked_24h},
    )
    embed.add_field(name="保護強度", value=cfg.protection_level, inline=True)
    embed.add_field(name="設定完成", value="是" if cfg.setup_complete else "否", inline=True)
    await interaction.followup.send(embed=embed, ephemeral=True)


@guard_group.command(name="restart", description="重啟 MonsterGuard Bot（需管理伺服器）")
async def guard_restart(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("需要「管理伺服器」權限。", ephemeral=True)
        return
    svc = getattr(interaction.client, "discord_service", None)
    if not svc:
        await interaction.response.send_message("僅 embedded 模式支援重啟。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    result = await svc.restart_guard()
    if result.get("ok"):
        await interaction.followup.send(
            f"MonsterGuard 重啟中…（累計 restarts: {result.get('restarts')}）",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(f"重啟失敗: {result.get('error')}", ephemeral=True)


@guard_group.command(name="logs", description="最近 MonsterGuard 結構化日誌")
async def guard_logs(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("需要「管理伺服器」權限。", ephemeral=True)
        return
    from monster_ai.modules.discord.bot import DiscordService

    logs = DiscordService.read_logs(limit=20)
    if not logs:
        await interaction.response.send_message("尚無日誌。", ephemeral=True)
        return
    lines = [json.dumps(row, ensure_ascii=False)[:120] for row in logs[-10:]]
    text = "```json\n" + "\n".join(lines) + "\n```"
    if len(text) > 1900:
        text = text[:1900] + "…```"
    await interaction.response.send_message(text, ephemeral=True)


@guard_group.command(name="config", description="查看目前伺服器設定（需管理伺服器）")
async def guard_config(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("需要「管理伺服器」權限。", ephemeral=True)
        return
    store = interaction.client.guild_store  # type: ignore[attr-defined]
    cfg = await store.get(interaction.guild_id or 0)
    lines = [
        f"保護強度: {cfg.protection_level}",
        f"動作模式: {cfg.action_mode}",
        f"攔截門檻: {cfg.block_threshold}",
        f"AI 增強: {'是' if cfg.ai_enabled else '否'}",
        f"Mod 頻道: <#{cfg.mod_channel_id}>" if cfg.mod_channel_id else "Mod 頻道: 未設定",
    ]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: discord.Client) -> None:
    pass