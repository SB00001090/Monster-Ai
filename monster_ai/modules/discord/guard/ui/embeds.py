"""Neon cyberpunk Discord embed builders — MonsterGuard v2.1（繁體中文）."""
from __future__ import annotations

from typing import Any

import discord

from monster_ai.modules.discord.constants import DEVELOPER_CREDIT, NEON_COLORS, PRODUCT_NAME, VERSION

_ANIM_FRAMES = ("◢◤", "◥◣", "▰▱", "▱▰")


def _yn(val: bool) -> str:
    return "是" if val else "否"


def neon_footer(frame_idx: int = 0) -> str:
    pulse = _ANIM_FRAMES[frame_idx % len(_ANIM_FRAMES)]
    return f"{pulse} {PRODUCT_NAME} v{VERSION} · {DEVELOPER_CREDIT}"


def status_embed(
    *,
    connected: bool,
    resilience: dict[str, Any] | None = None,
    monster_ai: dict[str, Any] | None = None,
    callguard: dict[str, Any] | None = None,
    guard_stats: dict[str, Any] | None = None,
    frame_idx: int = 0,
) -> discord.Embed:
    color = NEON_COLORS["green"] if connected else NEON_COLORS["alert"]
    state_zh = "在線" if connected else "離線 / 重連中"
    title = f"{'🟢' if connected else '🔴'} {PRODUCT_NAME} 狀態"
    embed = discord.Embed(title=title, color=color)
    embed.description = f"```ansi\n\u001b[0;36m{state_zh}\u001b[0m\n```"

    res = resilience or {}
    hb = res.get("heartbeat_ok")
    hb_text = "正常" if hb is True else ("異常" if hb is False else "—")
    embed.add_field(
        name="防斷線",
        value=(
            f"重試：`{res.get('reconnect_attempts', 0)}/{res.get('max_attempts', 10)}`\n"
            f"待機模式：`{_yn(bool(res.get('standby_mode')))}`\n"
            f"心跳：`{hb_text}`"
        ),
        inline=True,
    )

    ai = monster_ai or {}
    consent = "已授權" if ai.get("consent") else "待授權"
    linked = "已連線" if ai.get("connected") else "未連線"
    embed.add_field(
        name="Monster AI",
        value=(
            f"連線：`{linked}`\n"
            f"同意：`{consent}`\n"
            f"後端：`{ai.get('backend', 'local')}`"
        ),
        inline=True,
    )

    cg = callguard or {}
    embed.add_field(
        name="CallGuard 來電守衛",
        value=(
            f"橋接：`{'開啟' if cg.get('enabled') else '關閉'}`\n"
            f"狀態：`{cg.get('status', '未知')}`\n"
            f"已轉發：`{cg.get('forwarded', 0)}`"
        ),
        inline=True,
    )

    if guard_stats:
        embed.add_field(name="伺服器數", value=str(guard_stats.get("guilds", 0)), inline=True)
        embed.add_field(name="已掃描", value=str(guard_stats.get("scanned", 0)), inline=True)
        embed.add_field(name="規則版本", value=str(guard_stats.get("rules_version", "?")), inline=True)

    embed.set_footer(text=neon_footer(frame_idx))
    return embed


def about_embed() -> discord.Embed:
    embed = discord.Embed(
        title=f"{PRODUCT_NAME} v{VERSION}",
        description=(
            "**Monster AI 生態 Discord 橋樑**\n\n"
            "• 反詐騙訊息掃描\n"
            "• 本地 LLM 對話（`/ai`、`/chat`）\n"
            "• Monster CallGuard 警報（`/callguard`、`/防盜`）\n"
            "• 防斷線自修復（10 次重試 + 心跳）\n"
            "• 監控指令（`/status`、`/guard restart`）\n"
            "• Monster AI 動態自我介紹（`/intro`、`/monsterai`）\n"
            "• 新成員歡迎與個性化介紹\n\n"
            "🔒 本地優先 · 零信任 · 連線 Monster AI 需用戶同意"
        ),
        color=NEON_COLORS["cyan"],
    )
    embed.set_footer(text=DEVELOPER_CREDIT)
    return embed


def alert_embed(
    title: str,
    description: str,
    *,
    level: str = "warn",
) -> discord.Embed:
    colors = {"info": NEON_COLORS["cyan"], "warn": NEON_COLORS["magenta"], "critical": NEON_COLORS["alert"]}
    embed = discord.Embed(title=title, description=description, color=colors.get(level, NEON_COLORS["magenta"]))
    embed.set_footer(text=neon_footer())
    return embed


def intro_embed(
    description: str,
    *,
    style: str = "guardian",
    color: int | None = None,
    title: str = "Monster AI · 自我介紹",
) -> discord.Embed:
    style_labels = {
        "guardian": "🛡️ 正式守衛者",
        "cyberpunk": "◢◤ 幽默 Cyberpunk",
        "privacy": "🔒 隱私守護者",
    }
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or NEON_COLORS.get("cyan", 0x00F5FF),
    )
    embed.set_author(name=f"Monster AI — {style_labels.get(style, style)}")
    embed.set_footer(text=neon_footer())
    return embed


def callguard_alert_embed(report: dict[str, Any]) -> discord.Embed:
    score = report.get("score", 0)
    number = report.get("number", "unknown")
    category = report.get("category", "suspicious")
    embed = discord.Embed(
        title="📞 CallGuard 高風險來電警報",
        description=f"**號碼：** `{number}`\n**風險分數：** `{score}`\n**類別：** `{category}`",
        color=NEON_COLORS["alert"] if score >= 80 else NEON_COLORS["magenta"],
    )
    signals = report.get("signals") or []
    if signals:
        embed.add_field(name="特徵", value=", ".join(str(s) for s in signals[:6]), inline=False)
    embed.set_footer(text=neon_footer())
    return embed