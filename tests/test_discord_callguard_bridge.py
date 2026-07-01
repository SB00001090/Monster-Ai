"""Tests for CallGuard Discord bridge."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from monster_ai.config import GuardSettings
from monster_ai.modules.discord.guard.integration.callguard_bridge import CallGuardBridge


def _guard() -> GuardSettings:
    return GuardSettings(
        callguard_bridge_enabled=True,
        callguard_alert_score_threshold=70,
    )


@pytest.mark.asyncio
async def test_bridge_forwards_high_risk_report() -> None:
    client = MagicMock()
    client.callguard_status = AsyncMock(return_value={"enabled": True, "status": "ok"})
    client.callguard_reports = AsyncMock(
        return_value=[{"id": "r1", "number": "+85212345678", "score": 85, "category": "scam"}]
    )

    channel = MagicMock()
    channel.send = AsyncMock()
    bot = MagicMock()
    bot.is_ready.return_value = True
    bot.get_channel.return_value = channel

    bridge = CallGuardBridge(
        _guard(),
        client,
        get_bot=lambda: bot,
        get_alert_channel_id=lambda: 12345,
    )
    await bridge._poll()
    channel.send.assert_called_once()
    assert bridge.forwarded == 1


@pytest.mark.asyncio
async def test_bridge_dedupes_reports() -> None:
    client = MagicMock()
    client.callguard_status = AsyncMock(return_value={"enabled": True})
    report = {"id": "r1", "number": "x", "score": 90, "category": "scam"}
    client.callguard_reports = AsyncMock(return_value=[report])

    channel = MagicMock()
    channel.send = AsyncMock()
    bot = MagicMock()
    bot.is_ready.return_value = True
    bot.get_channel.return_value = channel

    bridge = CallGuardBridge(_guard(), client, get_bot=lambda: bot, get_alert_channel_id=lambda: 1)
    await bridge._poll()
    await bridge._poll()
    assert channel.send.call_count == 1