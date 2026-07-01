"""Grok supervision layer for Monster Guardian AI learning."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from monster_ai.core.self_repair import SelfRepairEngine


from monster_ai.modules.guardian.privacy_firewall import topic_anonymous_id

NETWORK_REVIEW_SYSTEM = """You are Grok approving Guardian autonomous network learning runs.
Only approve public tech/news/art-quality topics. Deny any OC names, chat excerpts, or private paths.
Output JSON only: {"approved":true|false,"topics":["..."],"reason":"..."}"""

SUPERVISOR_SYSTEM = """You are Grok supervising Monster Guardian AI's learning system.
Prioritize: (1) recurring errors, (2) user safety/privacy regressions, (3) quality below 70%.
Avoid bias toward over-censorship — this is a local-first, user-owned platform.
Output JSON only: {"priorities":[{"id","action","reason","urgency"}],"bias_warnings":[],"strategy_note":""}"""


class GrokSupervisor:
    def __init__(self, data_dir: Path, repair: SelfRepairEngine | None = None) -> None:
        self.root = data_dir / "grok_supervision"
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "directives.jsonl"
        self.network_log_path = self.root / "network_directives.jsonl"
        self._repair = repair

    async def review(
        self,
        *,
        error_summary: dict[str, Any],
        learning_snapshot: dict[str, Any],
        feedback_count: int = 0,
    ) -> dict[str, Any]:
        directive = self._rule_based_directive(error_summary, learning_snapshot, feedback_count)
        llm_note = await self._llm_enhance(directive, error_summary, learning_snapshot)
        if llm_note:
            directive["strategy_note"] = llm_note
        directive["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(directive, ensure_ascii=False) + "\n")
        return directive

    def _rule_based_directive(
        self,
        error_summary: dict[str, Any],
        learning_snapshot: dict[str, Any],
        feedback_count: int,
    ) -> dict[str, Any]:
        priorities: list[dict[str, str]] = []
        top = error_summary.get("top_error_types") or []
        for idx, item in enumerate(top[:3]):
            priorities.append(
                {
                    "id": f"err-{item.get('type', 'unknown')}",
                    "action": f"Patch recurring {item.get('type')} ({item.get('count')} cases)",
                    "reason": "Error learning ingestion flagged repeat pattern",
                    "urgency": "high" if idx == 0 else "medium",
                }
            )

        failures = (learning_snapshot.get("failure_analysis") or {}).get("failure_count", 0)
        if failures >= 5:
            priorities.append(
                {
                    "id": "quality-gate",
                    "action": "Tune min_quality_score and ComfyUI retry workflow",
                    "reason": f"{failures} recent quality failures",
                    "urgency": "high",
                }
            )

        if feedback_count > 10:
            priorities.append(
                {
                    "id": "preference-drift",
                    "action": "Rebalance preference weights — check for single-user bias",
                    "reason": f"{feedback_count} feedback events in window",
                    "urgency": "medium",
                }
            )

        return {
            "supervisor": "grok",
            "priorities": priorities,
            "bias_warnings": [
                "Do not auto-upload OC plaintext to cloud — E2E only",
                "Do not re-enable Tailscale or QR code connection paths",
            ],
            "strategy_note": "Rule-based supervision active; LLM enhancement optional.",
        }

    async def _llm_enhance(
        self,
        directive: dict[str, Any],
        error_summary: dict[str, Any],
        learning_snapshot: dict[str, Any],
    ) -> str:
        if self._repair is None:
            return ""
        prompt = (
            f"{SUPERVISOR_SYSTEM}\n\n"
            f"errors={json.dumps(error_summary, ensure_ascii=False)}\n"
            f"learning={json.dumps(learning_snapshot, ensure_ascii=False)[:2000]}\n"
            f"current_priorities={json.dumps(directive.get('priorities', []), ensure_ascii=False)}"
        )
        try:
            text = await self._repair.chat(prompt, system=SUPERVISOR_SYSTEM, temperature=0.3)
            if text and "{" in text:
                return text.strip()[:1500]
        except Exception:  # noqa: BLE001
            pass
        return ""

    async def review_network_learning(
        self,
        *,
        topics: list[str],
        window_ok: bool,
        user_consented: bool,
        max_topics: int = 3,
    ) -> dict[str, Any]:
        if not user_consented:
            return self._network_denied("consent_required", topics)
        if not window_ok:
            return self._network_denied("outside_schedule_window", topics)

        approved_topics = [t.strip() for t in topics if len(t.strip()) >= 3][:max_topics]
        if not approved_topics:
            return self._network_denied("no_topics", topics)

        directive: dict[str, Any] = {
            "supervisor": "grok",
            "approved": True,
            "topics": approved_topics,
            "topic_ids": [topic_anonymous_id(t) for t in approved_topics],
            "reason": "Rule-based approval — public topics only; no OC or vault data",
            "bias_warnings": [
                "Never include OC names, chat content, or training image paths in outbound requests",
                "Outbound metrics must be anonymous aggregates only",
            ],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        llm_note = await self._llm_network_review(directive, approved_topics)
        if llm_note:
            directive["strategy_note"] = llm_note
        with self.network_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(directive, ensure_ascii=False) + "\n")
        return directive

    def _network_denied(self, reason: str, topics: list[str]) -> dict[str, Any]:
        return {
            "supervisor": "grok",
            "approved": False,
            "topics": [],
            "topic_ids": [topic_anonymous_id(t) for t in topics],
            "reason": reason,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _llm_network_review(
        self,
        directive: dict[str, Any],
        topics: list[str],
    ) -> str:
        if self._repair is None:
            return ""
        prompt = (
            f"{NETWORK_REVIEW_SYSTEM}\n\n"
            f"topics={json.dumps(topics, ensure_ascii=False)}\n"
            f"directive={json.dumps(directive, ensure_ascii=False)}"
        )
        try:
            text = await self._repair.chat(prompt, system=NETWORK_REVIEW_SYSTEM, temperature=0.2)
            if text and "{" in text:
                return text.strip()[:1200]
        except Exception:  # noqa: BLE001
            pass
        return ""

    def latest_directives(self, limit: int = 5) -> list[dict[str, Any]]:
        if not self.log_path.is_file():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out