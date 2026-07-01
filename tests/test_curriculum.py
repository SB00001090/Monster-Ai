"""Tests for 36h AI curriculum."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from monster_ai.config import LearningSettings
from monster_ai.modules.learning.curriculum import build_36h_curriculum, build_curriculum, topic_count
from monster_ai.modules.learning.self_trainer import CurriculumRunner
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner


def test_curriculum_has_72_topics() -> None:
    assert topic_count("base") == 72
    phases = build_36h_curriculum()
    assert len(phases) == 6
    assert phases[0].topics[0].id == "transformer"


def test_extended_curriculum_includes_lang_and_cyber() -> None:
    assert topic_count("extended") > topic_count("base")
    assert topic_count("languages") >= 60
    assert topic_count("cybersec") >= 40
    phases = build_curriculum("extended")
    tracks = {t.track for p in phases for t in p.topics}
    assert tracks == {"ai", "lang", "cyber"}


def test_after_ai_curriculum_is_lang_plus_cyber() -> None:
    assert topic_count("after_ai") == topic_count("languages") + topic_count("cybersec")
    tracks = {t.track for p in build_curriculum("after_ai") for t in p.topics}
    assert tracks == {"lang", "cyber"}


@pytest.mark.asyncio
async def test_curriculum_process_topic(tmp_path) -> None:
    store = LearningStore(tmp_path)
    settings = LearningSettings(curriculum_enabled=True, curriculum_duration_hours=36)
    repair = MagicMock()
    repair.generate = AsyncMock(
        return_value='{"monster_insights":["GPT 使用 Transformer"],"training_pairs":[{"instruction":"什麼是GPT？","output":"GPT 是生成式預訓練模型。"}]}'
    )
    web = WebKnowledgeLearner(store, settings, repair)
    web.learn = AsyncMock(return_value={"ok": True, "summary": "GPT summary", "cached": False})
    web.retrieve_local = MagicMock(return_value=["fact1"])

    runner = CurriculumRunner(store, settings, web, repair)
    topic = build_36h_curriculum()[0].topics[0]
    await runner._process_topic(topic, 0)

    assert runner._state.completed_topics == 1
    train_file = runner._train_path()
    assert train_file.is_file()
    lines = train_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1


@pytest.mark.asyncio
async def test_curriculum_start_fast(tmp_path) -> None:
    store = LearningStore(tmp_path)
    settings = LearningSettings(curriculum_enabled=True)
    repair = MagicMock()
    repair.generate = AsyncMock(return_value='{"monster_insights":[],"training_pairs":[]}')
    web = WebKnowledgeLearner(store, settings, repair)
    web.learn = AsyncMock(return_value={"ok": True, "summary": "", "cached": True})

    runner = CurriculumRunner(store, settings, web, repair)
    result = await runner.start(duration_hours=1, resume=False, fast_mode=True)
    assert result["ok"]
    await runner.stop()