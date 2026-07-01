"""Tests for autonomous learning evolution loop."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from monster_ai.config import LearningSettings
from monster_ai.modules.learning.engine import LearningEngine
from monster_ai.modules.learning.failure_analyzer import FailureAnalyzer
from monster_ai.modules.learning.preferences import PreferenceLearner
from monster_ai.modules.learning.store import LearningStore


def test_preference_learns_tone_from_comment(tmp_path) -> None:
    store = LearningStore(tmp_path)
    learner = PreferenceLearner(store)
    model = learner.update_from_feedback(
        "u1",
        thumbs="down",
        comment="請更詳細一點",
        session_id="s1",
    )
    assert model["preferences"]["responseLength"] == "long"


def test_failure_analyzer_context_hint(tmp_path) -> None:
    store = LearningStore(tmp_path)
    store.append_jsonl(
        store.failures_log,
        {
            "reports": [
                {"reasons": ["too_short", "off_topic"]},
                {"reasons": ["too_short"]},
            ]
        },
    )
    analyzer = FailureAnalyzer(store)
    hint = analyzer.context_hint()
    assert "too_short" in hint


@pytest.mark.asyncio
async def test_learning_generate_injects_context(tmp_path) -> None:
    settings = LearningSettings(
        enabled=True,
        data_dir=str(tmp_path),
        reflect_enabled=False,
        inject_context_always=True,
        knowledge_extraction=False,
    )
    repair = MagicMock()
    repair.generate = AsyncMock(return_value="好的，這是繁體中文回答。")
    repair.state = MagicMock(active_backend="ollama")

    engine = LearningEngine(settings, repair)
    engine.preferences.update_from_feedback(
        "user42",
        thumbs="up",
        topics=["coding"],
        session_id="chat",
        comment="輕鬆一點",
    )

    result = await engine.generate(
        user_message="你好",
        system="You are helpful.",
        user_id="user42",
        session_id="chat",
    )

    assert result["content"]
    called_system = repair.generate.await_args.kwargs["system"]
    assert "coding" in called_system or "Preferred" in called_system
    assert "Autonomous learning" in called_system


@pytest.mark.asyncio
async def test_negative_feedback_regenerates(tmp_path) -> None:
    settings = LearningSettings(
        enabled=True,
        data_dir=str(tmp_path),
        reflect_enabled=False,
        regenerate_on_negative_feedback=True,
        knowledge_extraction=False,
    )
    repair = MagicMock()
    repair.generate = AsyncMock(return_value="improved answer with more detail")
    repair.state = MagicMock(active_backend="ollama")

    engine = LearningEngine(settings, repair)
    result = await engine.record_feedback_and_regenerate(
        user_id="u1",
        session_id="s1",
        thumbs="down",
        comment="太簡短",
        last_user_message="解釋 Python API",
        system="You are helpful.",
    )

    assert result.get("regenerated")
    assert "improved" in result["regenerated"]["content"]
    assert repair.generate.await_count == 1


def test_evolution_snapshot(tmp_path) -> None:
    settings = LearningSettings(enabled=True, data_dir=str(tmp_path))
    repair = MagicMock()
    engine = LearningEngine(settings, repair)
    snap = engine.evolution_snapshot()
    assert "feedback_events" in snap
    assert "min_quality_score" in snap