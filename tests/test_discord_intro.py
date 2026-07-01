"""Tests for Monster AI intro generator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from monster_ai.modules.discord.guard.integration.intro_generator import (
    INTRO_STYLES,
    build_status_context,
    generate_intro,
)


def _mock_bot(*, repair_text: str | None = None, with_repair: bool = True) -> MagicMock:
    bot = MagicMock()
    bot.is_ready.return_value = True
    bot.is_closed.return_value = False
    bot.status_dict.return_value = {
        "guilds": 2,
        "rules_version": "v2026.06",
        "scanned": 10,
        "blocked": 3,
        "warned": 1,
    }
    bot.discord_service = MagicMock()
    bot.discord_service.guard_status.return_value = {
        "connected": True,
        "resilience": {"heartbeat_ok": True, "standby_mode": False, "reconnect_attempts": 0},
        "monster_ai": {"connected": True},
        "callguard_bridge": {"enabled": True, "status": "ok", "forwarded": 2},
    }
    bot.chat = None
    if with_repair:
        bot.repair = MagicMock()
        bot.repair.state.primary_ok = True
        bot.repair.generate = AsyncMock(return_value=repair_text or "我是 Monster AI，連線穩定。")
    else:
        bot.repair = None
    return bot


def test_intro_styles_defined() -> None:
    assert "guardian" in INTRO_STYLES
    assert "cyberpunk" in INTRO_STYLES
    assert "privacy" in INTRO_STYLES


def test_build_status_context() -> None:
    ctx = build_status_context(_mock_bot())
    assert ctx["connected"] is True
    assert ctx["blocked"] == 3
    assert ctx["callguard_bridge"] is True


@pytest.mark.asyncio
async def test_generate_intro_uses_llm() -> None:
    bot = _mock_bot(repair_text="Cyber neon guardian online.")
    text, color = await generate_intro(bot, style="cyberpunk", member_name="Alice")
    assert "Cyber neon" in text or len(text) > 20
    assert color == 0x00F5FF
    bot.repair.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_intro_fallback_without_llm() -> None:
    bot = _mock_bot(with_repair=False)
    text, _ = await generate_intro(bot, style="privacy", member_name="Bob")
    assert "Bob" in text or "隱私" in text or "Monster AI" in text


@pytest.mark.asyncio
async def test_generate_intro_fallback_on_llm_error() -> None:
    bot = _mock_bot()
    bot.repair.generate = AsyncMock(side_effect=RuntimeError("ollama down"))
    text, _ = await generate_intro(bot, style="guardian")
    assert "Monster AI" in text or "MonsterGuard" in text