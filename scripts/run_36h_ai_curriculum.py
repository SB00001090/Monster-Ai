#!/usr/bin/env python3
"""Monster AI curriculum — GPT/AI + 全球語言 + 資安反制（連接網絡學習）.

Usage:
  python scripts/run_36h_ai_curriculum.py                    # AI 36h only
  python scripts/run_36h_ai_curriculum.py --chain            # AI 36h → 語言+資安 48h（推薦）
  python scripts/run_36h_ai_curriculum.py --extended         # AI + 語言 + 資安 72h
  python scripts/run_36h_ai_curriculum.py --after-ai         # 完成 AI 後學語言+資安
  python scripts/run_36h_ai_curriculum.py --languages-only   # 僅全球語言
  python scripts/run_36h_ai_curriculum.py --cybersec-only    # 僅資安反制
  python scripts/run_36h_ai_curriculum.py --fast --chain     # 快速測試
  python scripts/run_36h_ai_curriculum.py --list --extended  # 列出全部主題
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from monster_ai.config import load_settings
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.learning.curriculum import (
    build_curriculum,
    default_hours_for_mode,
    topic_count,
)
from monster_ai.modules.learning.self_trainer import CurriculumRunner
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner


def _resolve_mode(args: argparse.Namespace) -> str:
    if args.extended:
        return "extended"
    if args.after_ai:
        return "after_ai"
    if args.languages_only:
        return "languages"
    if args.cybersec_only:
        return "cybersec"
    return "base"


LABELS = {
    "base": "GPT/AI 36h",
    "extended": "GPT/AI + 全球語言 + 資安反制",
    "after_ai": "語言 + 資安（AI 完成後）",
    "languages": "全球語言",
    "cybersec": "資安反制",
}


async def _poll_progress(runner: CurriculumRunner) -> None:
    while runner._task and not runner._task.done():  # noqa: SLF001
        await asyncio.sleep(30)
        st = runner.status()
        print(
            f"[{st['progress_pct']}%] "
            f"{st['completed_topics']}/{st['total_topics']} | "
            f"mode={st['mode']} | "
            f"pairs={st['pairs_on_disk']} | "
            f"{st['current_phase']}/{st['current_topic_id']} | "
            f"ETA {st['eta_hours']}h"
        )


async def _run_phase(
    runner: CurriculumRunner,
    *,
    mode: str,
    hours: float,
    fast: bool,
    resume: bool,
) -> dict:
    print("=" * 60)
    print(f"Monster AI 網絡自主學習 — {LABELS.get(mode, mode)}")
    print("=" * 60)
    print(f"Topics: {topic_count(mode)} | Duration: {hours}h | Fast: {fast}")
    if not fast:
        sec_per = (hours * 3600) / max(topic_count(mode), 1)
        print(f"Pace: ~{sec_per / 60:.1f} min/topic")
    print("Output: data/training/curriculum/monster_ai_train.jsonl")
    print("Ctrl+C 暫停（進度自動保存）\n")

    result = await runner.start(
        duration_hours=hours,
        resume=resume,
        fast_mode=fast,
        mode=mode,
    )
    if not result.get("ok"):
        reason = result.get("reason", "")
        if reason == "lock_held":
            print(f"課程已在 PID {result.get('lock_pid')} 執行中，請勿重複啟動。")
            st = result.get("status", {})
            print(
                f"進度 {st.get('progress_pct', 0)}% | "
                f"{st.get('completed_topics', 0)}/{st.get('total_topics', 0)} | "
                f"mode={st.get('mode')}"
            )
            return {"ok": False, "reason": "lock_held", **result}
        print("Start failed:", result)
        return {"ok": False, **result}

    await _poll_progress(runner)
    final = runner.status()
    print(
        f"\nPhase done: {final['completed_topics']}/{final['total_topics']} | "
        f"pairs={final['pairs_on_disk']}"
    )
    return {"ok": True, "status": final}


async def main() -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="Monster AI 網絡自主學習課程")
    parser.add_argument("--hours", type=float, default=None, help="總學習時數（預設依模式）")
    parser.add_argument("--fast", action="store_true", help="快速測試（2 秒/主題）")
    parser.add_argument("--no-resume", action="store_true", help="重新開始，忽略進度")
    parser.add_argument("--list", action="store_true", help="列出課程主題")
    parser.add_argument(
        "--extended",
        action="store_true",
        help="完整課程：GPT/AI 36h + 全球語言 + 資安反制（預設 72h）",
    )
    parser.add_argument(
        "--after-ai",
        action="store_true",
        help="AI 36h 完成後：僅學語言 + 資安反制",
    )
    parser.add_argument("--languages-only", action="store_true", help="僅學全球語言與程式語言")
    parser.add_argument("--cybersec-only", action="store_true", help="僅學資安反制技術")
    parser.add_argument(
        "--chain",
        action="store_true",
        help="先 AI 36h，完成後自動接語言+資安（網絡學習，共 ~84h）",
    )
    parser.add_argument("--status", action="store_true", help="僅顯示課程進度後退出")
    args = parser.parse_args()

    if args.chain and any((args.extended, args.after_ai, args.languages_only, args.cybersec_only)):
        print("Error: --chain 不可與 --extended / --after-ai / --languages-only / --cybersec-only 同時使用")
        return 2

    mode = _resolve_mode(args)
    hours = args.hours or default_hours_for_mode(mode)

    if args.list:
        for phase in build_curriculum(mode):
            print(f"\n=== {phase.title} ({phase.hours}) [{len(phase.topics)} topics] ===")
            for t in phase.topics:
                print(f"  [{t.track}:{t.id}] {t.query_zh}")
        print(f"\nMode={mode} | Total topics: {topic_count(mode)} | Default hours: {hours}")
        return 0

    settings = load_settings()
    store = LearningStore(settings.learning.data_dir)
    repair = SelfRepairEngine(settings, root=ROOT)
    web = WebKnowledgeLearner(store, settings.learning, repair)
    runner = CurriculumRunner(store, settings.learning, web, repair)

    if args.status:
        st = runner.status()
        lock = store.read_json(store.root / "curriculum" / "runner.lock", {})
        pid = lock.get("pid")
        on_disk = store.read_json(store.root / "curriculum" / "state.json", {})
        alive = bool(pid) and __import__("monster_ai.modules.learning.self_trainer", fromlist=["_pid_alive"])._pid_alive(int(pid))
        running = bool(on_disk.get("running")) and alive
        print(f"running={running} | pid={pid or '—'}")
        print(
            f"[{st.get('progress_pct', 0)}%] "
            f"{st.get('completed_topics', 0)}/{st.get('total_topics', 0)} | "
            f"mode={st.get('mode')} | pairs={st.get('pairs_on_disk', 0)} | "
            f"ETA {st.get('eta_hours', 0)}h"
        )
        print(f"phase={st.get('current_phase') or '—'} | topic={st.get('current_topic_id') or '—'}")
        return 0

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(runner.stop()))
        except NotImplementedError:
            pass

    resume = not args.no_resume
    if args.chain:
        ai_hours = settings.learning.curriculum_duration_hours
        follow_hours = default_hours_for_mode("after_ai")
        print("=" * 60)
        print("Monster AI 連續課程：AI 36h → 全球語言 + 資安反制")
        print(f"Phase 1: {topic_count('base')} topics / {ai_hours}h")
        print(f"Phase 2: {topic_count('after_ai')} topics / {follow_hours}h")
        print("=" * 60 + "\n")

        phase1 = await _run_phase(
            runner,
            mode="base",
            hours=ai_hours,
            fast=args.fast,
            resume=resume,
        )
        if not phase1.get("ok"):
            return 0 if phase1.get("reason") == "lock_held" else 1
        if runner._stop.is_set():  # noqa: SLF001
            print("\nStopped before phase 2.")
            return 0

        print("\n>>> AI 課程完成，開始全球語言 + 資安反制（連接網絡）...\n")
        phase2 = await _run_phase(
            runner,
            mode="after_ai",
            hours=follow_hours,
            fast=args.fast,
            resume=resume,
        )
        if not phase2.get("ok"):
            return 0 if phase2.get("reason") == "lock_held" else 1
        final = phase2["status"]
    else:
        result = await _run_phase(
            runner,
            mode=mode,
            hours=hours,
            fast=args.fast,
            resume=resume,
        )
        if not result.get("ok"):
            return 0 if result.get("reason") == "lock_held" else 1
        final = result["status"]

    print("\n" + "=" * 60)
    print("Done.")
    print(f"Completed: {final['completed_topics']}/{final['total_topics']}")
    print(f"Training pairs: {final['pairs_on_disk']}")
    print("\nNext:")
    print("  ollama create monster-learned -f data/training/curriculum/MonsterAI_learned.Modelfile")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))