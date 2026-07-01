"""Monster AI dynamic self-introduction — Developed by Suckbob | Monster AI Ecosystem."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from monster_ai.modules.discord.constants import DEVELOPER_CREDIT, PRODUCT_NAME, VERSION

if TYPE_CHECKING:
    from monster_ai.modules.discord.guard.bot import MonsterGuardBot

logger = logging.getLogger(__name__)

INTRO_STYLES: dict[str, str] = {
    "guardian": "正式守衛者：莊重、可靠、強調 24/7 保護與穩定連線",
    "cyberpunk": "幽默 cyberpunk：霓虹、俏皮、賽博梗，但仍專業",
    "privacy": "專業隱私守護者：零信任、本地優先、資料不上雲",
}

_STYLE_COLORS = {
    "guardian": 0x39FF14,
    "cyberpunk": 0x00F5FF,
    "privacy": 0x9D4EDD,
}


def build_status_context(bot: MonsterGuardBot) -> dict[str, Any]:
    stats = bot.status_dict()
    resilience: dict[str, Any] = {}
    monster_ai: dict[str, Any] = {}
    callguard: dict[str, Any] = {}
    connected = bot.is_ready() and not bot.is_closed()

    svc = bot.discord_service
    if svc:
        gs = svc.guard_status()
        connected = gs.get("connected", connected)
        resilience = gs.get("resilience", {})
        monster_ai = gs.get("monster_ai", {})
        callguard = gs.get("callguard_bridge", {})

    return {
        "version": VERSION,
        "connected": connected,
        "guilds": stats.get("guilds", 0),
        "scanned": stats.get("scanned", 0),
        "blocked": stats.get("blocked", 0),
        "rules_version": stats.get("rules_version", "?"),
        "heartbeat_ok": resilience.get("heartbeat_ok", True),
        "standby": resilience.get("standby_mode", False),
        "reconnect_attempts": resilience.get("reconnect_attempts", 0),
        "monster_ai_linked": monster_ai.get("connected", False),
        "callguard_bridge": callguard.get("enabled", False),
        "callguard_status": callguard.get("status", "unknown"),
        "callguard_forwarded": callguard.get("forwarded", 0),
    }


def _fallback_intro(style: str, ctx: dict[str, Any], member_name: str | None) -> str:
    greet = f"歡迎 {member_name}！" if member_name else "你好！"
    stability = "連線穩定" if ctx["connected"] and ctx["heartbeat_ok"] else "正在守護連線中"
    cg = (
        f"CallGuard 橋接：`{'開啟' if ctx['callguard_bridge'] else '關閉'}` · "
        f"狀態 `{ctx['callguard_status']}`"
    )
    base = (
        f"{greet} 我是 **Monster AI** 生態的 Discord 守衛節點（{PRODUCT_NAME} v{ctx['version']}）。\n\n"
        f"• {stability} · 已掃描 `{ctx['scanned']}` 則 · 攔截 `{ctx['blocked']}`\n"
        f"• 規則版本 `{ctx['rules_version']}` · Monster AI `{'已連線' if ctx['monster_ai_linked'] else '待授權'}`\n"
        f"• {cg}\n\n"
        f"指令：`/intro` `/status` `/ai` `/callguard` `/防盜` `/guard setup`\n"
        f"🔒 本地優先 · 零信任 · {DEVELOPER_CREDIT}"
    )
    if style == "cyberpunk":
        return (
            f"{greet} ◢◤ **Monster AI online** — neon shields engaged.\n\n"
            f"Uptime vibe: **{stability}** | Blocks today: `{ctx['blocked']}` | Rules: `{ctx['rules_version']}`\n"
            f"{cg}\n\n"
            "Try `/intro` for style swaps · `/ai` to chat with your local LLM.\n"
            f"{DEVELOPER_CREDIT}"
        )
    if style == "privacy":
        return (
            f"{greet} 我是您伺服器內的**隱私守護節點**。\n\n"
            "所有分析預設在您的 Monster AI 本地環境完成；Discord 僅作橋接，不將資料送往第三方雲端。\n"
            f"目前狀態：{stability} · 規則 `{ctx['rules_version']}` · {cg}\n\n"
            f"{DEVELOPER_CREDIT}"
        )
    return base


async def generate_intro(
    bot: MonsterGuardBot,
    *,
    style: str = "guardian",
    member_name: str | None = None,
) -> tuple[str, int]:
    """Return (intro_text, embed_color)."""
    style_key = style if style in INTRO_STYLES else "guardian"
    ctx = build_status_context(bot)
    context_block = (
        f"version={ctx['version']}, connected={ctx['connected']}, heartbeat={ctx['heartbeat_ok']}, "
        f"scanned={ctx['scanned']}, blocked={ctx['blocked']}, rules={ctx['rules_version']}, "
        f"callguard_bridge={ctx['callguard_bridge']}, callguard_status={ctx['callguard_status']}, "
        f"callguard_forwarded={ctx['callguard_forwarded']}, monster_ai_linked={ctx['monster_ai_linked']}"
    )
    member_line = f"The greeting is for Discord member: {member_name}." if member_name else ""
    system = (
        "You are Monster AI speaking through MonsterGuard Discord bot. "
        f"Style: {INTRO_STYLES[style_key]}. "
        "Write 120-220 words in Traditional Chinese (mix English cyber terms OK). "
        "Include current status metrics provided. Mention CallGuard integration if enabled. "
        "End with one line inviting /guard setup or /status. No markdown headers."
    )
    prompt = (
        f"Generate a personalized self-introduction.\n{member_line}\n"
        f"Live status: {context_block}\n"
        f"Developer credit: {DEVELOPER_CREDIT}"
    )

    text: str | None = None
    if bot.repair and getattr(bot.repair, "state", None) and bot.repair.state.primary_ok:
        try:
            text = await bot.repair.generate(prompt, system=system)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intro LLM failed: %s", exc)
    if not text and bot.chat:
        try:
            result = await bot.chat.send(
                f"{system}\n\n{prompt}",
                persona_mode="grok",
            )
            text = (result.get("content") or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intro chat bridge failed: %s", exc)

    if not text or len(text) < 40:
        text = _fallback_intro(style_key, ctx, member_name)

    if len(text) > 1900:
        text = text[:1900] + "…"
    return text, _STYLE_COLORS.get(style_key, 0x00F5FF)