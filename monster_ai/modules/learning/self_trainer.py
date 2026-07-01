"""36-hour autonomous curriculum — network learn GPT/AI knowledge and self-train Monster AI."""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from monster_ai.config import LearningSettings
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.learning.curriculum import (
    DEFAULT_DURATION_HOURS,
    CurriculumTopic,
    build_curriculum,
    default_hours_for_mode,
    flat_topics,
    topic_count,
)
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner

SYNTHESIS_SYSTEM = """You are training Monster AI — a local autonomous assistant.
From web research about AI/GPT topics, create training examples for Monster AI to learn.
Output JSON only:
{
  "monster_insights": ["insight in Traditional Chinese", "..."],
  "training_pairs": [
    {"instruction": "user question zh-TW", "output": "Monster AI answer zh-TW"}
  ]
}
Create 3-5 high-quality pairs. Answers should be witty, direct, Grok-style, 繁體中文.
Teach Monster AI to rival GPT while running fully local."""

LANG_SYNTHESIS_SYSTEM = """You are training Monster AI to master world languages and programming languages.
From web research, create training examples for multilingual Monster AI.
Output JSON only:
{
  "monster_insights": ["insight in Traditional Chinese about the language"],
  "training_pairs": [
    {"instruction": "question about the language zh-TW", "output": "helpful multilingual answer"}
  ]
}
Create 3-5 pairs. Include practical phrases, cultural notes, and how Monster AI should respond in that language context."""

CYBER_SYNTHESIS_SYSTEM = """You are training Monster AI as a defensive cybersecurity guardian (blue team only).
From web research on DEFENSIVE countermeasures and protection techniques, create training examples.
Focus: detection, prevention, hardening, incident response — NEVER offensive hacking instructions.
Output JSON only:
{
  "monster_insights": ["defensive insight 繁體中文"],
  "training_pairs": [
    {"instruction": "how to defend against X", "output": "defensive guidance for Monster AI users"}
  ]
}
Create 3-5 pairs. Relate to MonsterGuard, CallGuard, CrimeGuard when relevant."""

STATE_FILE = "state.json"
LOCK_FILE = "runner.lock"
TRAIN_FILE = "monster_ai_train.jsonl"
PROGRESS_LOG = "progress.jsonl"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@dataclass
class CurriculumState:
    running: bool = False
    started_at: float = 0.0
    duration_hours: float = DEFAULT_DURATION_HOURS
    completed_topics: int = 0
    total_topics: int = 0
    current_topic_id: str = ""
    current_phase: str = ""
    errors: int = 0
    training_pairs: int = 0
    elapsed_hours: float = 0.0
    eta_hours: float = 0.0
    last_error: str = ""
    mode: str = "base"

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "started_at": self.started_at,
            "duration_hours": self.duration_hours,
            "completed_topics": self.completed_topics,
            "total_topics": self.total_topics,
            "current_topic_id": self.current_topic_id,
            "current_phase": self.current_phase,
            "errors": self.errors,
            "training_pairs": self.training_pairs,
            "elapsed_hours": round(self.elapsed_hours, 2),
            "eta_hours": round(self.eta_hours, 2),
            "progress_pct": round(
                100.0 * self.completed_topics / max(self.total_topics, 1), 1
            ),
            "last_error": self.last_error,
            "mode": self.mode,
        }


class CurriculumRunner:
    def __init__(
        self,
        store: LearningStore,
        settings: LearningSettings,
        web: WebKnowledgeLearner,
        repair: SelfRepairEngine,
    ) -> None:
        self.store = store
        self.settings = settings
        self.web = web
        self.repair = repair
        self.curriculum_dir = store.root / "curriculum"
        self.train_dir = Path("./data/training/curriculum")
        self.curriculum_dir.mkdir(parents=True, exist_ok=True)
        self.train_dir.mkdir(parents=True, exist_ok=True)
        self._state = CurriculumState()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._load_state()

    def _state_path(self) -> Path:
        return self.curriculum_dir / STATE_FILE

    def _train_path(self) -> Path:
        return self.train_dir / TRAIN_FILE

    def _progress_path(self) -> Path:
        return self.curriculum_dir / PROGRESS_LOG

    def _lock_path(self) -> Path:
        return self.curriculum_dir / LOCK_FILE

    def _read_lock(self) -> dict[str, Any]:
        return self.store.read_json(self._lock_path(), {})

    def _acquire_lock(self) -> tuple[bool, int]:
        lock = self._read_lock()
        holder = int(lock.get("pid", 0) or 0)
        if holder and holder != os.getpid() and _pid_alive(holder):
            return False, holder
        self.store.write_json(
            self._lock_path(),
            {"pid": os.getpid(), "started_at": time.time()},
        )
        return True, os.getpid()

    def _release_lock(self) -> None:
        lock = self._read_lock()
        if int(lock.get("pid", 0) or 0) == os.getpid() and self._lock_path().is_file():
            self._lock_path().unlink(missing_ok=True)

    def _load_state(self) -> None:
        data = self.store.read_json(self._state_path(), self._state.to_dict())
        self._state = CurriculumState(
            running=bool(data.get("running", False)),
            started_at=float(data.get("started_at", 0)),
            duration_hours=float(data.get("duration_hours", DEFAULT_DURATION_HOURS)),
            completed_topics=int(data.get("completed_topics", 0)),
            total_topics=int(data.get("total_topics", topic_count(data.get("mode", "base")))),
            current_topic_id=str(data.get("current_topic_id", "")),
            current_phase=str(data.get("current_phase", "")),
            errors=int(data.get("errors", 0)),
            training_pairs=int(data.get("training_pairs", 0)),
            elapsed_hours=float(data.get("elapsed_hours", 0)),
            eta_hours=float(data.get("eta_hours", 0)),
            last_error=str(data.get("last_error", "")),
            mode=str(data.get("mode", "base")),
        )
        if self._state.running:
            self._state.running = False

    def _save_state(self) -> None:
        self.store.write_json(self._state_path(), self._state.to_dict())

    def status(self) -> dict[str, Any]:
        train_path = self._train_path()
        pairs_on_disk = 0
        if train_path.is_file():
            pairs_on_disk = len(train_path.read_text(encoding="utf-8").strip().splitlines())
        return {
            **self._state.to_dict(),
            "training_file": str(train_path),
            "pairs_on_disk": pairs_on_disk,
            "curriculum_topics": topic_count(self._state.mode),
            "phases": len(build_curriculum(self._state.mode)),
            "mode": self._state.mode,
        }

    async def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._state.running = False
        self._save_state()
        self._release_lock()
        return {"ok": True, "message": "curriculum stopped", "status": self.status()}

    async def start(
        self,
        *,
        duration_hours: float | None = None,
        resume: bool = True,
        fast_mode: bool = False,
        mode: str = "base",
    ) -> dict[str, Any]:
        if self._task and not self._task.done():
            return {"ok": False, "reason": "already_running", "status": self.status()}

        acquired, lock_pid = self._acquire_lock()
        if not acquired:
            return {
                "ok": False,
                "reason": "lock_held",
                "lock_pid": lock_pid,
                "status": self.status(),
            }

        duration = duration_hours or default_hours_for_mode(mode)
        if mode == "base" and duration_hours is None:
            duration = self.settings.curriculum_duration_hours
        self._stop.clear()
        if not resume or self._state.completed_topics == 0 or self._state.mode != mode:
            self._state = CurriculumState(
                duration_hours=duration,
                total_topics=topic_count(mode),
                mode=mode,
            )
        self._state.running = True
        self._state.started_at = time.time()
        self._state.duration_hours = duration
        self._state.total_topics = topic_count(mode)
        self._state.mode = mode
        self._save_state()

        self._task = asyncio.create_task(self._run_loop(fast_mode=fast_mode, mode=mode))
        labels = {
            "base": "AI 36h",
            "extended": "AI+語言+資安 72h",
            "full": "AI+語言+資安 72h",
            "languages": "全球語言",
            "after_ai": "語言+資安（AI 完成後）",
            "cybersec": "資安反制",
        }
        label = labels.get(mode, mode)
        return {"ok": True, "message": f"Curriculum started: {label} ({duration}h)", "status": self.status()}

    def _seconds_per_topic(self, fast_mode: bool) -> float:
        if fast_mode:
            return 2.0
        total = max(self._state.total_topics, 1)
        return (self._state.duration_hours * 3600) / total

    async def _synthesize_training(
        self, topic: CurriculumTopic, web_summary: str, snippets: list[str]
    ) -> dict[str, Any]:
        blob = f"Topic: {topic.query_zh}\nFocus: {topic.focus}\n\n"
        if web_summary:
            blob += f"Summary:\n{web_summary}\n\n"
        if snippets:
            blob += "Snippets:\n" + "\n".join(f"- {s}" for s in snippets[:6])

        system = SYNTHESIS_SYSTEM
        if topic.track == "lang":
            system = LANG_SYNTHESIS_SYSTEM
        elif topic.track == "cyber":
            system = CYBER_SYNTHESIS_SYSTEM
        raw = await self.repair.generate(blob, system=system)
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {"monster_insights": [], "training_pairs": []}
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {"monster_insights": [], "training_pairs": []}

    def _append_training_pair(self, topic: CurriculumTopic, pair: dict[str, Any]) -> None:
        record = {
            "instruction": str(pair.get("instruction", "")).strip(),
            "input": str(pair.get("input", "")).strip(),
            "output": str(pair.get("output", "")).strip(),
            "topic_id": topic.id,
            "phase": topic.phase,
            "source": f"curriculum_{topic.track}",
            "track": topic.track,
            "ts": time.time(),
        }
        if len(record["instruction"]) < 4 or len(record["output"]) < 8:
            return
        with self._train_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._state.training_pairs += 1

    async def _process_topic(self, topic: CurriculumTopic, idx: int) -> None:
        self._state.current_topic_id = topic.id
        self._state.current_phase = topic.phase
        self._save_state()

        learned = await self.web.learn(topic.query_zh, force_refresh=False)
        if not learned.get("ok"):
            self._state.errors += 1
            self._state.last_error = str(learned.get("reason", "web_learn_failed"))
            return

        summary = str(learned.get("summary", ""))
        snippets = self.web.retrieve_local(topic.query_zh, limit=6)
        synth = await self._synthesize_training(topic, summary, snippets)

        for insight in synth.get("monster_insights") or []:
            ins = str(insight).strip()
            if ins:
                self._append_training_pair(
                    topic,
                    {
                        "instruction": f"關於{topic.query_zh}，Monster AI 應知道什麼？",
                        "output": ins,
                    },
                )

        for pair in synth.get("training_pairs") or []:
            self._append_training_pair(topic, pair)

        self._state.completed_topics = idx + 1
        elapsed = (time.time() - self._state.started_at) / 3600
        self._state.elapsed_hours = elapsed
        remaining = max(self._state.total_topics - self._state.completed_topics, 0)
        per_topic_h = self._state.duration_hours / max(self._state.total_topics, 1)
        self._state.eta_hours = remaining * per_topic_h

        self.store.append_jsonl(
            self._progress_path(),
            {
                "topic_id": topic.id,
                "phase": topic.phase,
                "query": topic.query_zh,
                "pairs_added": len(synth.get("training_pairs") or []),
                "web_ok": learned.get("ok"),
                "track": topic.track,
            },
        )
        self._save_state()

    async def _run_loop(self, *, fast_mode: bool = False, mode: str = "base") -> None:
        topics = flat_topics(mode=mode)
        start_idx = self._state.completed_topics
        interval = self._seconds_per_topic(fast_mode)

        try:
            for idx in range(start_idx, len(topics)):
                if self._stop.is_set():
                    break
                await self._process_topic(topics[idx], idx)
                if idx < len(topics) - 1 and not self._stop.is_set():
                    await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self._state.running = False
            self._save_state()
            raise
        except Exception as exc:  # noqa: BLE001
            self._state.errors += 1
            self._state.last_error = str(exc)
        finally:
            self._state.running = False
            self._save_state()
            self._release_lock()
            self._export_modelfile_hint()

    def _export_modelfile_hint(self) -> None:
        """Write Ollama Modelfile snippet referencing learned system context."""
        train_path = self._train_path()
        if not train_path.is_file():
            return
        lines = train_path.read_text(encoding="utf-8").strip().splitlines()
        samples = [json.loads(ln) for ln in lines[-20:] if ln.strip()]
        insights = [s.get("output", "")[:200] for s in samples if s.get("output")]
        modelfile = self.train_dir / "MonsterAI_learned.Modelfile"
        body = (
            "# Auto-generated from 36h curriculum — append to your Ollama Modelfile\n"
            "FROM llama3.2:latest\n\n"
            "SYSTEM \"\"\"\n"
            "你是 Monster AI — 本地自主學習助手，已從 GPT、全球語言、資安反制技術持續進化。\n"
            "機智、直率、多語言、資安防護。以下為學習精華：\n"
            + "\n".join(f"- {i}" for i in insights[:12])
            + "\n\"\"\"\n"
        )
        modelfile.write_text(body, encoding="utf-8")