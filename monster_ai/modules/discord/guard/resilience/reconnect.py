"""Reconnect manager with exponential backoff and standby mode."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from monster_ai.config import GuardSettings
from monster_ai.modules.discord.constants import LOG_PATH

if TYPE_CHECKING:
    from monster_ai.modules.discord.guard.resilience.notifier import DisconnectNotifier

logger = logging.getLogger(__name__)


@dataclass
class ResilienceState:
    reconnect_attempts: int = 0
    standby_mode: bool = False
    last_disconnect_at: float | None = None
    last_reconnect_at: float | None = None
    heartbeat_ok: bool = True
    heartbeat_fail_streak: int = 0
    last_error: str | None = None

    def to_dict(self, guard: GuardSettings) -> dict[str, Any]:
        return {
            "reconnect_attempts": self.reconnect_attempts,
            "max_attempts": guard.max_reconnect_attempts,
            "standby_mode": self.standby_mode,
            "heartbeat_ok": self.heartbeat_ok,
            "heartbeat_fail_streak": self.heartbeat_fail_streak,
            "last_error": self.last_error,
            "last_disconnect_at": self.last_disconnect_at,
            "last_reconnect_at": self.last_reconnect_at,
        }


@dataclass
class ReconnectManager:
    guard: GuardSettings
    notifier: DisconnectNotifier | None = None
    state: ResilienceState = field(default_factory=ResilienceState)
    _log_path: Path = field(default_factory=lambda: Path(LOG_PATH))

    def reset(self) -> None:
        self.state.reconnect_attempts = 0
        self.state.standby_mode = False
        self.state.heartbeat_fail_streak = 0
        self.state.last_error = None

    def log_event(self, event: str, **extra: Any) -> None:
        record = {
            "ts": time.time(),
            "event": event,
            **extra,
        }
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.debug("Resilience log write failed: %s", exc)

    async def run(
        self,
        *,
        stop_flag: Callable[[], bool],
        create_bot: Callable[[], None],
        start_bot: Callable[[], Awaitable[None]],
        close_bot: Callable[[], Awaitable[None]],
        on_running: Callable[[bool], None],
        on_fatal_auth: Callable[[], None],
        get_fatal_auth: Callable[[], bool],
        set_fatal_auth: Callable[[bool], None],
        set_last_error: Callable[[str | None], None],
    ) -> None:
        delay = 5.0
        max_delay = float(self.guard.self_heal_max_backoff_seconds)

        while not stop_flag() and not self.state.standby_mode:
            create_bot()
            on_running(True)
            error_class = ""
            try:
                await start_bot()
                if stop_flag():
                    break
                error_class = "disconnect"
                self.state.last_disconnect_at = time.time()
                self.log_event("disconnect", attempt=self.state.reconnect_attempts)
                if self.notifier:
                    await self.notifier.notify_disconnect(self.state.reconnect_attempts)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                error_class = exc.__class__.__name__
                self.state.last_error = error_class
                set_last_error(error_class)
                self.log_event("error", error_class=error_class)
                if error_class == "LoginFailure":
                    set_fatal_auth(True)
                    logger.error("MonsterGuard token invalid — update discord.token.local")
                    break
                if error_class == "PrivilegedIntentsRequired":
                    logger.error("Enable MESSAGE CONTENT INTENT in Discord Developer Portal")
                    break
                logger.exception("MonsterGuard bot crashed: %s", exc)
            finally:
                on_running(False)
                await close_bot()

            if stop_flag() or get_fatal_auth():
                break

            self.state.reconnect_attempts += 1
            if self.state.reconnect_attempts >= self.guard.max_reconnect_attempts:
                self.state.standby_mode = True
                self.log_event("standby_entered", attempts=self.state.reconnect_attempts)
                logger.error(
                    "MonsterGuard entered standby after %s reconnect attempts",
                    self.state.reconnect_attempts,
                )
                if self.notifier:
                    await self.notifier.notify_standby(self.state.reconnect_attempts)
                break

            logger.warning(
                "MonsterGuard disconnected; reconnect %s/%s in %.0fs",
                self.state.reconnect_attempts,
                self.guard.max_reconnect_attempts,
                delay,
            )
            self.log_event(
                "reconnect_scheduled",
                attempt=self.state.reconnect_attempts,
                delay_seconds=delay,
                reason=error_class or "unknown",
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

        on_running(False)

    def on_connect_success(self) -> None:
        prev_attempts = self.state.reconnect_attempts
        self.state.reconnect_attempts = 0
        self.state.standby_mode = False
        self.state.last_reconnect_at = time.time()
        self.state.last_error = None
        self.log_event("reconnect_success")
        if prev_attempts > 0 and self.notifier:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.notifier.notify_reconnect_success())
            except RuntimeError:
                pass