"""Tests for MonsterGuard heartbeat monitor."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from monster_ai.config import GuardSettings
from monster_ai.modules.discord.guard.resilience.heartbeat import HeartbeatMonitor
from monster_ai.modules.discord.guard.resilience.reconnect import ReconnectManager


def _guard() -> GuardSettings:
    return GuardSettings(
        heartbeat_interval_seconds=1,
        heartbeat_max_latency_seconds=1.0,
        heartbeat_fail_threshold=2,
    )


@pytest.mark.asyncio
async def test_heartbeat_failure_triggers_callback() -> None:
    reconnect = ReconnectManager(_guard())
    bot = MagicMock()
    bot.is_closed.return_value = False
    bot.is_ready.return_value = False
    bot.latency = 0.1

    called = False

    async def on_failure() -> None:
        nonlocal called
        called = True

    hb = HeartbeatMonitor(
        _guard(),
        reconnect,
        get_bot=lambda: bot,
        on_failure=on_failure,
    )
    await hb._tick()
    assert reconnect.state.heartbeat_fail_streak == 1
    await hb._tick()
    assert called is True


@pytest.mark.asyncio
async def test_heartbeat_ok_resets_streak() -> None:
    reconnect = ReconnectManager(_guard())
    bot = MagicMock()
    bot.is_closed.return_value = False
    bot.is_ready.return_value = True
    bot.latency = 0.05
    reconnect.state.heartbeat_fail_streak = 2

    hb = HeartbeatMonitor(_guard(), reconnect, get_bot=lambda: bot)
    await hb._tick()
    assert reconnect.state.heartbeat_ok is True
    assert reconnect.state.heartbeat_fail_streak == 0