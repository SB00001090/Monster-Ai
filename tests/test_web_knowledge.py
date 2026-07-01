"""Tests for network web knowledge learning."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monster_ai.config import LearningSettings
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner


def test_should_auto_search_detects_questions(tmp_path) -> None:
    settings = LearningSettings(web_auto_search=True)
    store = LearningStore(tmp_path)
    learner = WebKnowledgeLearner(store, settings)
    assert learner.should_auto_search("什麼是量子計算？")
    assert learner.should_auto_search("How does Python work?")
    assert not learner.should_auto_search("hi")


@pytest.mark.asyncio
async def test_learn_stores_facts_from_search(tmp_path) -> None:
    settings = LearningSettings(
        web_learning_enabled=True,
        web_search_langs=["zh"],
        web_max_results=2,
    )
    store = LearningStore(tmp_path)
    repair = MagicMock()
    repair.generate = AsyncMock(return_value='{"facts":[{"fact":"量子計算是利用量子力學的計算方式","source":"wiki"}],"summary":"量子計算簡介"}')
    learner = WebKnowledgeLearner(store, settings, repair)

    fake_results = {
        "ok": True,
        "query": "量子計算",
        "results": [
            {
                "title": "量子計算",
                "snippet": "量子計算利用量子位元進行運算。",
                "url": "https://zh.wikipedia.org/wiki/量子計算",
                "source": "wikipedia:zh",
            }
        ],
    }
    with patch.object(learner, "search", AsyncMock(return_value=fake_results)):
        result = await learner.learn("量子計算")

    assert result["ok"]
    assert result["facts_added"] >= 1
    local = learner.retrieve_local("量子計算")
    assert any("量子" in f for f in local)


@pytest.mark.asyncio
async def test_network_guard_blocks_search(tmp_path) -> None:
    settings = LearningSettings(web_learning_enabled=True)
    store = LearningStore(tmp_path)
    learner = WebKnowledgeLearner(store, settings)
    learner.set_network_guard(lambda: (False, "network_locked"))
    result = await learner.search("test")
    assert not result["ok"]
    assert result["reason"] == "network_locked"


def test_retrieve_local_keyword_match(tmp_path) -> None:
    settings = LearningSettings()
    store = LearningStore(tmp_path)
    learner = WebKnowledgeLearner(store, settings)
    data = learner._load_facts()  # noqa: SLF001
    data["facts"] = [
        {"fact": "Python 是一種高階程式語言", "confidence": 0.8},
        {"fact": "JavaScript 用於網頁開發", "confidence": 0.7},
    ]
    learner._save_facts(data)  # noqa: SLF001
    hits = learner.retrieve_local("Python 程式")
    assert any("Python" in h for h in hits)