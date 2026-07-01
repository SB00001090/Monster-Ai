"""Tests for MonsterGuard v2.0 reconnect manager."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from monster_ai.config import GuardSettings
from monster_ai.modules.discord.guard.resilience.reconnect import ReconnectManager


def _guard(**kwargs) -> GuardSettings:
    defaults = {"max_reconnect_attempts": 3, "self_heal_max_backoff_seconds": 10}
    defaults.update(kwargs)
    return GuardSettings(**defaults)


@pytest.mark.asyncio
async def test_standby_after_max_attempts() -> None:
    mgr = ReconnectManager(_guard(max_reconnect_attempts=2))
    stop = False
    starts = 0

    async def start_bot() -> None:
        nonlocal starts
        starts += 1
        raise ConnectionError("disconnect")

    async def close_bot() -> None:
        pass

    await mgr.run(
        stop_flag=lambda: stop,
        create_bot=lambda: None,
        start_bot=start_bot,
        close_bot=close_bot,
        on_running=lambda _: None,
        on_fatal_auth=lambda: None,
        get_fatal_auth=lambda: False,
        set_fatal_auth=lambda _: None,
        set_last_error=lambda _: None,
    )

    assert mgr.state.standby_mode is True
    assert mgr.state.reconnect_attempts >= 2
    assert starts == 2


@pytest.mark.asyncio
async def test_reset_clears_standby() -> None:
    mgr = ReconnectManager(_guard())
    mgr.state.standby_mode = True
    mgr.state.reconnect_attempts = 10
    mgr.reset()
    assert mgr.state.standby_mode is False
    assert mgr.state.reconnect_attempts == 0


@pytest.mark.asyncio
async def test_reconnect_manager_logs_events(tmp_path) -> None:
    log_path = tmp_path / "mg.jsonl"
    mgr = ReconnectManager(_guard(max_reconnect_attempts=1))
    mgr._log_path = log_path
    mgr.log_event("test_event", foo="bar")
    assert log_path.is_file()
    assert "test_event" in log_path.read_text(encoding="utf-8")