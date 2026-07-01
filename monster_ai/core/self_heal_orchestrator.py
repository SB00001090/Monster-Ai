"""Unified self-heal orchestrator — L1-L4 ops layer (Phase A)."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from monster_ai.config import OrchestratorSettings

logger = logging.getLogger(__name__)


@dataclass
class HealIncident:
    domain: str
    level: str
    message: str
    action: str
    ok: bool
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "level": self.level,
            "message": self.message,
            "action": self.action,
            "ok": self.ok,
            "ts": self.ts,
        }


class SelfHealOrchestrator:
    """Coordinates health monitoring and recovery across Monster AI subsystems."""

    def __init__(self, settings: OrchestratorSettings, root: Path) -> None:
        self.settings = settings
        self.root = root
        self.log_path = root / "data" / "logs" / "heal_events.jsonl"
        self.incidents: list[HealIncident] = []
        self.checks = 0
        self.recoveries = 0
        self._task: asyncio.Task | None = None
        self._repair = None
        self._watchdog = None
        self._discord = None
        self._learning = None
        self._monsterlock_dir = root / "data" / "monsterlock"

    def bind(
        self,
        *,
        repair: Any = None,
        watchdog: Any = None,
        discord: Any = None,
        learning: Any = None,
    ) -> None:
        self._repair = repair
        self._watchdog = watchdog
        self._discord = discord
        self._learning = learning

    async def start(self) -> None:
        if not self.settings.enabled:
            return
        await self.run_cycle()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.interval_seconds)
            await self.run_cycle()

    def _log(self, incident: HealIncident) -> None:
        self.incidents.append(incident)
        self.incidents = self.incidents[-200:]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(incident.to_dict(), ensure_ascii=False) + "\n")
        if self._learning is not None:
            ingest = getattr(self._learning, "ingest_ops_incident", None)
            if callable(ingest):
                ingest(incident.to_dict())

    async def _ping(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(url)
                return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def run_cycle(self) -> dict[str, Any]:
        self.checks += 1
        results: list[HealIncident] = []

        if self._repair:
            ok = self._repair.state.primary_ok
            if not ok:
                inc = HealIncident("llm", "warn", self._repair.state.last_error or "llm_down", "heal_once", False)
                try:
                    await self._repair._heal_once()  # noqa: SLF001
                    inc.ok = self._repair.state.primary_ok
                    if inc.ok:
                        self.recoveries += 1
                except Exception as exc:  # noqa: BLE001
                    inc.message = str(exc)
                results.append(inc)
                self._log(inc)

        if self.settings.check_ollama and self._watchdog:
            if not self._watchdog.state.ollama_ok:
                inc = HealIncident("ollama", "warn", "ollama_offline", "watchdog_notify", False)
                results.append(inc)
                self._log(inc)

        if self.settings.check_discord and self._discord:
            status = self._discord.guard_status()
            if not status.get("running"):
                inc = HealIncident("discord", "warn", "guard_bot_offline", "ensure_guard_running", False)
                try:
                    await self._discord.ensure_guard_running()
                    inc.ok = self._discord.guard_status().get("running", False)
                    if inc.ok:
                        self.recoveries += 1
                except Exception as exc:  # noqa: BLE001
                    inc.message = str(exc)
                results.append(inc)
                self._log(inc)

        if self.settings.check_monsterlock:
            locked = self._monsterlock_dir / "LOCKED"
            if locked.is_file():
                inc = HealIncident("monsterlock", "critical", "LOCKED", "recover_script", False)
                if self.settings.auto_recover_monsterlock:
                    try:
                        script = self.root / "scripts" / "monsterlock" / "recover_from_self_destruct.py"
                        proc = subprocess.run(
                            [sys.executable, str(script)],
                            cwd=str(self.root),
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        inc.ok = proc.returncode == 0 and not locked.exists()
                        if inc.ok:
                            self.recoveries += 1
                        else:
                            inc.message = (proc.stderr or proc.stdout or "")[:500]
                    except Exception as exc:  # noqa: BLE001
                        inc.message = str(exc)
                results.append(inc)
                self._log(inc)

        if self.settings.check_api:
            api_ok = await self._ping("http://127.0.0.1:7860/api/callguard/status")
            if not api_ok:
                inc = HealIncident("api", "critical", "monster_ai_api_down", "supervisor_restart", False)
                results.append(inc)
                self._log(inc)

        return {"checks": self.checks, "recoveries": self.recoveries, "incidents": [i.to_dict() for i in results]}

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "checks": self.checks,
            "recoveries": self.recoveries,
            "recent_incidents": [i.to_dict() for i in self.incidents[-20:]],
            "layers": {
                "L1_monitoring": True,
                "L2_detection": True,
                "L3_recovery": True,
                "L4_learning": {
                    "heal_log": str(self.log_path),
                    "learning_ingest": self._learning is not None,
                },
            },
        }