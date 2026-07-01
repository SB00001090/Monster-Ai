"""Learning + reflect orchestration — autonomous evolution loop."""
from __future__ import annotations

from typing import Any

from monster_ai.config import LearningSettings
from monster_ai.core.reflect_loop import run_reflect_loop
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.learning.failure_analyzer import FailureAnalyzer
from monster_ai.modules.learning.feedback import FeedbackCollector
from monster_ai.modules.learning.knowledge import KnowledgeBase
from monster_ai.modules.learning.preferences import PreferenceLearner
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.text_quality import evaluate_text_response
from monster_ai.modules.learning.text_refiner import TextRefiner
from monster_ai.modules.learning.image_knowledge import ImageKnowledgeLearner
from monster_ai.modules.learning.roleplay_web import RoleplayWebLearner
from monster_ai.modules.learning.self_trainer import CurriculumRunner
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner

EVOLUTION_DIRECTIVE = (
    "[Autonomous learning] Use stored user preferences and knowledge. "
    "Improve with each turn — be more helpful, accurate, and aligned with user style."
)


class LearningEngine:
    name = "learning"

    def __init__(self, settings: LearningSettings, repair: SelfRepairEngine) -> None:
        self.settings = settings
        self.repair = repair
        self.store = LearningStore(settings.data_dir)
        self.feedback = FeedbackCollector(self.store)
        self.preferences = PreferenceLearner(self.store)
        self.knowledge = KnowledgeBase(self.store, repair if settings.knowledge_extraction else None)
        self.refiner = TextRefiner(repair)
        self.failure_analyzer = FailureAnalyzer(self.store)
        self.web = WebKnowledgeLearner(self.store, settings, repair)
        self.roleplay_web = RoleplayWebLearner(self.store, settings, self.web, self.knowledge)
        self.curriculum = CurriculumRunner(self.store, settings, self.web, repair)
        self.image: ImageKnowledgeLearner | None = None
        self.evolution_log = self.store.root / "evolution.jsonl"
        self._ops_incidents = 0

    async def health(self) -> dict[str, Any]:
        snapshot = self.evolution_snapshot()
        return {
            "enabled": self.settings.enabled,
            "healthy": True,
            "reflect_enabled": self.settings.reflect_enabled,
            "feedback_enabled": self.settings.feedback_enabled,
            "evolution": snapshot,
            "web": self.web.status(),
            "image": self.image.status() if self.image else {"enabled": False},
        }

    def bind_image_learner(self, learner: ImageKnowledgeLearner) -> None:
        self.image = learner

    async def learn_perfect_images(self) -> dict[str, Any]:
        if not self.image:
            return {"ok": False, "reason": "image_learner_not_bound"}
        result = self.image.learn_from_quality_store()
        if result.get("ok"):
            self._log_evolution(event="image_learn", **result)
        return result

    def build_learning_context(self, *, user_id: str, character_id: str | None = None) -> str:
        parts: list[str] = []
        if self.settings.preference_learning and user_id:
            hint = self.preferences.context_hint(user_id)
            if hint:
                parts.append(hint)
        if character_id and self.settings.knowledge_extraction:
            hint = self.knowledge.context_hint(character_id)
            if hint:
                parts.append(hint)
        if self.settings.inject_context_always:
            failure_hint = self.failure_analyzer.context_hint()
            if failure_hint:
                parts.append(failure_hint)
            parts.append(EVOLUTION_DIRECTIVE)
        return "\n\n".join(parts)

    def enrich_system(
        self,
        system: str | None,
        *,
        user_id: str,
        character_id: str | None = None,
        extra: str = "",
    ) -> str:
        base = (system or "").strip()
        ctx = self.build_learning_context(user_id=user_id, character_id=character_id)
        chunks = [c for c in (base, ctx, extra.strip()) if c]
        return "\n\n".join(chunks) if chunks else EVOLUTION_DIRECTIVE

    def _effective_min_quality(self) -> float:
        base = self.settings.min_quality_score
        if not self.settings.auto_tune_quality:
            return base
        adjusted = self.failure_analyzer.suggest_min_quality_adjustment(base)
        return adjusted if adjusted is not None else base

    async def generate(
        self,
        *,
        user_message: str,
        system: str | None,
        user_id: str = "default",
        character_id: str | None = None,
        session_id: str = "",
        extra_system: str = "",
        web_search: bool | None = None,
        mode: str = "chat",
        character_name: str = "",
        scenario: str = "",
        memory_summary: str = "",
    ) -> dict[str, Any]:
        web_ctx = ""
        if mode == "roleplay" and self.settings.roleplay_web_enabled:
            force_web = web_search is True
            auto = web_search is not False and self.settings.roleplay_web_auto_search
            if force_web or auto:
                web_ctx = await self.roleplay_web.context_for_roleplay(
                    user_message,
                    character_id=character_id,
                    character_name=character_name,
                    scenario=scenario,
                    memory_summary=memory_summary,
                    force=force_web,
                )
        elif self.settings.web_learning_enabled:
            force_web = web_search is True
            auto = web_search is not False and self.settings.web_auto_search
            if force_web or auto:
                web_ctx = await self.web.context_for_message(
                    user_message,
                    force=force_web,
                )
        merged_extra = "\n\n".join(x for x in (extra_system, web_ctx) if x)
        full_system = self.enrich_system(
            system,
            user_id=user_id,
            character_id=character_id,
            extra=merged_extra,
        )
        state = {"user_message": user_message, "system": full_system}

        async def _gen() -> str:
            return await self.repair.generate(state["user_message"], system=state["system"])

        async def _validate(output: str) -> tuple[bool, dict[str, Any]]:
            report = evaluate_text_response(
                output,
                user_message=user_message,
                min_score=self._effective_min_quality(),
            )
            return report.passed, report.to_dict()

        async def _reflect(output: str, report: dict[str, Any], attempt: int) -> str:
            improved = await self.refiner.reflect(
                user_message=user_message,
                failed_output=output,
                report=report,
                system=full_system,
            )
            state["user_message"] = (
                f"{user_message}\n\n[Quality retry {attempt + 1}: improve relevance and depth]"
            )
            return improved

        if self.settings.reflect_enabled:
            loop = await run_reflect_loop(
                generate=_gen,
                validate=_validate,
                reflect=_reflect,
                max_retries=self.settings.reflect_max_retries,
                context=state,
            )
            content = loop.output
            result_passed = loop.passed
            attempts = loop.attempts
            reports = loop.reports
            if not result_passed:
                self.store.append_jsonl(
                    self.store.failures_log,
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "character_id": character_id,
                        "reports": reports,
                    },
                )
        else:
            content = await _gen()
            report = evaluate_text_response(
                content,
                user_message=user_message,
                min_score=self._effective_min_quality(),
            )
            result_passed = report.passed
            attempts = 1
            reports = [report.to_dict()]

        if self.settings.knowledge_extraction and character_id:
            await self.knowledge.extract_from_turn(character_id, user_message, content)

        self._log_evolution(
            event="generate",
            user_id=user_id,
            session_id=session_id,
            passed=result_passed,
            attempts=attempts,
        )

        return {
            "content": content,
            "backend": self.repair.state.active_backend,
            "quality": {
                "passed": result_passed,
                "attempts": attempts,
                "reports": reports,
            },
            "web_knowledge_used": bool(web_ctx),
        }

    async def learn_from_web(self, query: str, *, force_refresh: bool = False) -> dict[str, Any]:
        result = await self.web.learn(query, force_refresh=force_refresh)
        if result.get("ok"):
            self._log_evolution(event="web_learn", query=query, facts_added=result.get("facts_added", 0))
        return result

    async def search_web(self, query: str) -> dict[str, Any]:
        return await self.web.search(query)

    async def learn_roleplay_lore(
        self,
        query: str,
        *,
        character_id: str | None = None,
        character_name: str = "",
        scenario: str = "",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        result = await self.roleplay_web.learn_lore(
            query,
            character_id=character_id,
            character_name=character_name,
            scenario=scenario,
            force_refresh=force_refresh,
        )
        if result.get("ok"):
            self._log_evolution(event="roleplay_web_learn", character_id=character_id, query=query[:80])
        return result

    async def start_curriculum(
        self,
        *,
        duration_hours: float | None = None,
        resume: bool = True,
        fast_mode: bool = False,
        mode: str = "base",
    ) -> dict[str, Any]:
        if not self.settings.curriculum_enabled:
            return {"ok": False, "reason": "curriculum_disabled"}
        result = await self.curriculum.start(
            duration_hours=duration_hours,
            resume=resume,
            fast_mode=fast_mode,
            mode=mode,
        )
        if result.get("ok"):
            self._log_evolution(event="curriculum_start", duration_hours=duration_hours or 36)
        return result

    async def stop_curriculum(self) -> dict[str, Any]:
        return await self.curriculum.stop()

    def curriculum_status(self) -> dict[str, Any]:
        return self.curriculum.status()

    async def generate_with_reflect(
        self,
        *,
        user_message: str,
        system: str,
        user_id: str = "default",
        character_id: str | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Backward-compatible alias."""
        return await self.generate(
            user_message=user_message,
            system=system,
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
        )

    def record_feedback(
        self,
        *,
        user_id: str,
        session_id: str,
        rating: int | None = None,
        thumbs: str | None = None,
        comment: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        if not self.settings.feedback_enabled:
            return {"ok": False, "message": "feedback disabled"}
        topics = self.preferences.extract_topics(message) if message else []
        rec = self.feedback.record(
            user_id=user_id,
            session_id=session_id,
            rating=rating,
            thumbs=thumbs,
            comment=comment,
            extra={"topics": topics},
        )
        if self.settings.preference_learning:
            self.preferences.update_from_feedback(
                user_id,
                rating=rating,
                thumbs=thumbs,
                topics=topics,
                session_id=session_id,
                comment=comment,
            )
        self._log_evolution(
            event="feedback",
            user_id=user_id,
            session_id=session_id,
            thumbs=thumbs,
            rating=rating,
        )
        return {"ok": True, "record": rec}

    async def record_feedback_and_regenerate(
        self,
        *,
        user_id: str,
        session_id: str,
        thumbs: str | None,
        comment: str = "",
        message: str = "",
        last_user_message: str = "",
        system: str | None = None,
        character_id: str | None = None,
    ) -> dict[str, Any]:
        result = self.record_feedback(
            user_id=user_id,
            session_id=session_id,
            thumbs=thumbs,
            comment=comment,
            message=message,
        )
        if (
            not result.get("ok")
            or thumbs != "down"
            or not self.settings.regenerate_on_negative_feedback
            or not last_user_message.strip()
        ):
            return result

        extra = (
            "[User rejected the previous answer. Regenerate with better depth, accuracy, "
            f"and tone. Comment: {comment or 'none'}]"
        )
        regen = await self.generate(
            user_message=last_user_message,
            system=system,
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
            extra_system=extra,
        )
        result["regenerated"] = regen
        self._log_evolution(event="regenerate_after_feedback", user_id=user_id, session_id=session_id)
        return result

    def ingest_ops_incident(self, incident: dict[str, Any]) -> None:
        self._ops_incidents += 1
        if not self.settings.evolution_log_enabled:
            return
        self.store.append_jsonl(
            self.evolution_log,
            {"event": "ops_incident", "incident": incident},
        )

    def evolution_snapshot(self) -> dict[str, Any]:
        failures = self.failure_analyzer.summarize()
        feedback_count = 0
        if self.store.feedback_log.is_file():
            feedback_count = len(self.store.feedback_log.read_text(encoding="utf-8").strip().splitlines())
        return {
            "feedback_events": feedback_count,
            "quality_failures": failures,
            "ops_incidents_ingested": self._ops_incidents,
            "min_quality_score": self._effective_min_quality(),
            "configured_min_quality": self.settings.min_quality_score,
            "reflect_enabled": self.settings.reflect_enabled,
            "inject_context_always": self.settings.inject_context_always,
            "web": self.web.status(),
            "image": self.image.status() if self.image else {},
            "roleplay_web": self.roleplay_web.status(),
            "curriculum": self.curriculum.status(),
        }

    def _log_evolution(self, **fields: Any) -> None:
        if not self.settings.evolution_log_enabled:
            return
        self.store.append_jsonl(self.evolution_log, fields)