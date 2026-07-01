"""Tests for roleplay network lore learning."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from monster_ai.config import LearningSettings
from monster_ai.modules.learning.knowledge import KnowledgeBase
from monster_ai.modules.learning.roleplay_web import RoleplayWebLearner
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner


@pytest.mark.asyncio
async def test_learn_lore_merges_character_kb(tmp_path) -> None:
    store = LearningStore(tmp_path)
    settings = LearningSettings(
        enabled=True,
        web_learning_enabled=True,
        roleplay_web_enabled=True,
    )
    repair = MagicMock()
    web = WebKnowledgeLearner(store, settings, repair)
    knowledge = KnowledgeBase(store, repair)
    learner = RoleplayWebLearner(store, settings, web, knowledge)

    web.learn = AsyncMock(
        return_value={
            "ok": True,
            "summary": "賽博龐克世界充滿霓虹與企業統治。",
            "facts_added": 1,
            "cached": False,
        }
    )
    web.retrieve_local = MagicMock(return_value=["夜之城是核心都市"])

    result = await learner.learn_lore(
        "賽博龐克世界觀",
        character_id="char-1",
        character_name="V",
        scenario="夜之城街頭",
    )

    assert result["ok"]
    assert result["kb_facts_added"] >= 1
    kb = knowledge.get("char-1")
    facts = kb.get("knowledgeBase", {}).get("facts", [])
    assert len(facts) >= 1


def test_should_search_roleplay_lore(tmp_path) -> None:
    store = LearningStore(tmp_path)
    settings = LearningSettings(roleplay_web_enabled=True, roleplay_web_auto_search=True)
    web = WebKnowledgeLearner(store, settings)
    knowledge = KnowledgeBase(store)
    learner = RoleplayWebLearner(store, settings, web, knowledge)

    assert learner.should_search("這個世界的魔法體系是什麼？")
    assert learner.should_search("搜尋: 中世紀封建制度")
    assert not learner.should_search("你好")