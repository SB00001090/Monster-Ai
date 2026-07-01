"""Guardian autonomous network learning — opt-in, scheduled, Grok-supervised."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

from monster_ai.config import GuardianNetworkLearningSettings
from monster_ai.modules.guardian.learning_scheduler import LearningScheduler
from monster_ai.modules.guardian.privacy_firewall import (
    assert_outbound_safe,
    is_denied_read_path,
    sanitize_outbound,
    topic_anonymous_id,
)

if TYPE_CHECKING:
    from monster_ai.modules.guardian.grok_supervisor import GrokSupervisor
    from monster_ai.modules.guardian.training_vault import TrainingVault
    from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner

DEFAULT_TOPICS = (
    "AI 技術新聞",
    "diffusion model research paper",
    "digital art anatomy quality",
)


class GuardianNetworkLearner:
    """Decides when to connect, learns public topics, never leaks private vault data."""

    def __init__(
        self,
        settings: GuardianNetworkLearningSettings,
        *,
        data_dir: Path,
        web_learner: WebKnowledgeLearner,
        supervisor: GrokSupervisor,
        training_vault: TrainingVault | None = None,
    ) -> None:
        self.settings = settings
        self.root = data_dir / "network_learning"
        self.root.mkdir(parents=True, exist_ok=True)
        self.guardian_root = data_dir
        self.consent_path = self.root / "network_consent.json"
        self.runs_path = self.root / "runs.jsonl"
        self.directives_path = self.root / "directives.jsonl"
        self._web = web_learner
        self._supervisor = supervisor
        self._vault = training_vault
        self._scheduler = LearningScheduler(settings.schedule_windows)
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def network_gate(self) -> tuple[bool, str]:
        if not self.settings.enabled:
            return False, "network_learning_disabled"
        consent = self.consent_status()
        if not consent.get("user_consented"):
            return False, "consent_required"
        return True, ""

    def consent_status(self) -> dict[str, Any]:
        data = self._read_json(self.consent_path, {})
        return {
            "enabled": self.settings.enabled,
            "user_consented": bool(data.get("consented")),
            "consented_at": data.get("consented_at"),
            "allow_anonymous_metrics": self.settings.allow_anonymous_metrics
            and bool(data.get("consented")),
            "require_grok_approval": self.settings.require_grok_approval,
        }

    def grant_consent(self, *, metrics: bool = False) -> dict[str, Any]:
        self._write_json(
            self.consent_path,
            {
                "consented": True,
                "consented_at": time.time(),
                "metrics": metrics,
            },
        )
        return self.consent_status()

    def revoke_consent(self) -> dict[str, Any]:
        if self.consent_path.is_file():
            self.consent_path.unlink(missing_ok=True)
        return self.consent_status()

    def status(self) -> dict[str, Any]:
        last_run = self._last_run()
        consent = self.consent_status()
        return {
            **consent,
            "art_triage_enabled": self.settings.art_triage_enabled,
            "max_topics_per_run": self.settings.max_topics_per_run,
            "schedule": self._scheduler.status(),
            "last_run_at": last_run.get("finished_at") if last_run else None,
            "last_run_ok": last_run.get("ok") if last_run else None,
            "topics_learned_total": self._topics_learned_count(),
            "active_session": self._active,
        }

    def latest_directives(self, limit: int = 5) -> list[dict[str, Any]]:
        if not self.directives_path.is_file():
            return []
        lines = self.directives_path.read_text(encoding="utf-8").strip().splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    async def trigger(self, *, force: bool = False, topics: list[str] | None = None) -> dict[str, Any]:
        consent = self.consent_status()
        last_at = self._last_run_timestamp()
        ok, reason = self._scheduler.should_run(
            consented=bool(consent.get("user_consented")),
            enabled=self.settings.enabled,
            last_run_at=last_at,
            force=force,
        )
        if not ok:
            return {"ok": False, "reason": reason}

        candidate_topics = topics or list(DEFAULT_TOPICS)
        window_ok = force or self._scheduler.in_window()
        review: dict[str, Any]
        if self.settings.require_grok_approval:
            review = await self._supervisor.review_network_learning(
                topics=candidate_topics,
                window_ok=window_ok,
                user_consented=bool(consent.get("user_consented")),
                max_topics=self.settings.max_topics_per_run,
            )
            if not review.get("approved"):
                self._append_directive(review)
                return {"ok": False, "reason": review.get("reason", "grok_denied"), "review": review}
            run_topics = list(review.get("topics") or [])
        else:
            run_topics = candidate_topics[: self.settings.max_topics_per_run]
            review = {
                "approved": True,
                "topics": run_topics,
                "reason": "grok_approval_disabled",
            }

        self._active = True
        results: list[dict[str, Any]] = []
        try:
            for topic in run_topics:
                if is_denied_read_path(self.root / topic, self.guardian_root):
                    results.append({"topic_id": topic_anonymous_id(topic), "ok": False, "reason": "denied_path"})
                    continue
                learned = await self._web.learn(topic, force_refresh=True, network_override=True)
                safe = sanitize_outbound(
                    {
                        "topic_id": topic_anonymous_id(topic),
                        "ok": learned.get("ok"),
                        "facts_added": learned.get("facts_added", 0),
                        "cached": learned.get("cached", False),
                    }
                )
                ok_safe, leak_reason = assert_outbound_safe(safe)
                if not ok_safe:
                    results.append({"topic_id": topic_anonymous_id(topic), "ok": False, "reason": leak_reason})
                    continue
                results.append(safe)
                self._maybe_store_vault(topic, learned, safe)
        finally:
            self._active = False

        run_record = sanitize_outbound(
            {
                "ok": all(r.get("ok") for r in results) if results else False,
                "topics": run_topics,
                "results": results,
                "review": review,
                "force": force,
                "finished_at": time.time(),
            }
        )
        self._append_run(run_record)
        self._append_directive(
            sanitize_outbound(
                {
                    "approved": True,
                    "topics": run_topics,
                    "facts_added": sum(int(r.get("facts_added", 0)) for r in results),
                    "run_ok": run_record.get("ok"),
                    "reviewed_at": time.time(),
                }
            )
        )
        return {"ok": run_record.get("ok", False), "results": results, "review": review}

    def _maybe_store_vault(self, topic: str, learned: dict[str, Any], safe: dict[str, Any]) -> None:
        if self._vault is None or not learned.get("ok"):
            return
        summary = str(learned.get("summary", "")).strip()
        if not summary:
            summary = json.dumps(safe, ensure_ascii=False)
        try:
            self._vault.store_text_asset(
                label="prompt",
                name=f"netlearn_{topic_anonymous_id(topic)}",
                content=summary[:4000],
                metadata={
                    "source": "network_learning",
                    "topic_id": topic_anonymous_id(topic),
                    "facts_added": safe.get("facts_added", 0),
                },
            )
        except PermissionError:
            pass

    def _read_json(self, path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.is_file():
            return default
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else default
        except json.JSONDecodeError:
            return default

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_run(self, record: dict[str, Any]) -> None:
        with self.runs_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_directive(self, record: dict[str, Any]) -> None:
        with self.directives_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _last_run_timestamp(self) -> float | None:
        last = self._last_run()
        if not last:
            return None
        finished = last.get("finished_at")
        return float(finished) if finished is not None else None

    def _last_run(self) -> dict[str, Any] | None:
        if not self.runs_path.is_file():
            return None
        lines = self.runs_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None
        try:
            data = json.loads(lines[-1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def _topics_learned_count(self) -> int:
        if not self.runs_path.is_file():
            return 0
        count = 0
        for line in self.runs_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("ok"):
                count += len(row.get("topic_ids") or row.get("topics") or [])
        return count