"""Tests for MonsterGuard Discord self-heal loop."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monster_ai.config import GuardSettings, Settings
from monster_ai.modules.discord.bot import DiscordService


def _settings(*, self_heal_enabled: bool = True) -> Settings:
    guard = GuardSettings(
        enabled=True,
        self_heal_enabled=self_heal_enabled,
        self_heal_interval_seconds=1,
    )
    return Settings(
        modules={
            "discord": {
                "enabled": True,
                "token_env": "MONSTER_DISCORD_TOKEN",
                "guard": guard.model_dump(),
            }
        }
    )


@pytest.mark.asyncio
async def test_ensure_guard_running_restarts_dead_task(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = DiscordService(_settings())
    svc._repair = MagicMock()
    svc._chat = MagicMock()
    svc._roleplay = None
    svc._token = "test-token"
    svc._heal_stats.token_fingerprint = svc._token_fingerprint("test-token")
    svc._offline_streak = 2
    svc._task = asyncio.create_task(asyncio.sleep(60))
    svc._task.cancel()
    try:
        await svc._task
    except asyncio.CancelledError:
        pass
    svc._task = None
    svc._running = False

    started: list[str] = []

    async def fake_start(token: str) -> None:
        started.append(token)
        svc._running = True
        svc._task = asyncio.create_task(asyncio.sleep(3600))

    monkeypatch.setattr(svc, "_start_bot_task", fake_start)
    await svc.restart_guard(force_token="test-token")

    assert started == ["test-token"]
    assert svc._heal_stats.restarts == 1


@pytest.mark.asyncio
async def test_token_file_change_clears_fatal_auth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    token_file = tmp_path / "discord.token.local"
    token_file.write_text("token-a\n", encoding="utf-8")
    monkeypatch.setattr(
        "monster_ai.modules.discord.bot._PROJECT_ROOT",
        tmp_path,
    )

    svc = DiscordService(_settings())
    svc._fatal_auth_error = True
    svc._heal_stats.token_fingerprint = svc._token_fingerprint("old-token")

    assert svc._sync_token() == "token-a"
    assert svc._fatal_auth_error is False

    token_file.write_text("token-b\n", encoding="utf-8")
    svc._fatal_auth_error = True
    assert svc._sync_token() == "token-b"
    assert svc._fatal_auth_error is False


@pytest.mark.asyncio
async def test_self_heal_disabled_skips_heal_loop() -> None:
    svc = DiscordService(_settings(self_heal_enabled=False))
    svc._stop = False
    svc._start_heal_loop()
    assert svc._heal_task is None


@pytest.mark.asyncio
async def test_guard_status_includes_self_heal() -> None:
    svc = DiscordService(_settings())
    status = svc.guard_status()
    assert "self_heal" in status
    assert status["self_heal"]["enabled"] is True
    assert status["self_heal"]["restarts"] == 0


@pytest.mark.asyncio
async def test_guard_status_includes_v2_resilience() -> None:
    svc = DiscordService(_settings())
    status = svc.guard_status()
    assert status.get("version") == "2.1.0"
    assert "resilience" in status
    assert "monster_ai" in status
    assert "callguard_bridge" in status