"""Roleplay + network knowledge — world lore learning per character."""
from __future__ import annotations

import re
from typing import Any

from monster_ai.config import LearningSettings
from monster_ai.modules.learning.knowledge import KnowledgeBase
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner

ROLEPLAY_SEARCH_MARKERS = (
    r"世界觀",
    r"設定",
    r"背景",
    r"歷史",
    r"地理",
    r"魔法",
    r"科技",
    r"種族",
    r"帝國",
    r"王國",
    r"星球",
    r"賽博",
    r"武俠",
    r"仙俠",
    r"lore",
    r"worldbuilding",
    r"setting",
    r"backstory",
    r"universe",
    r"timeline",
    r"faction",
    r"搜尋",
    r"查一下",
    r"上網",
    r"網路",
    r"資料",
    r"根據.*現實",
    r"真實的",
    r"\?",
    r"什麼是",
    r"為何",
    r"如何",
)

ROLEPLAY_CONTEXT_PREFIX = (
    "[Roleplay world research] Use these facts to enrich the scene while staying fully in character. "
    "Weave lore naturally — no out-of-character Wikipedia tone."
)


class RoleplayWebLearner:
    def __init__(
        self,
        store: LearningStore,
        settings: LearningSettings,
        web: WebKnowledgeLearner,
        knowledge: KnowledgeBase,
    ) -> None:
        self.store = store
        self.settings = settings
        self.web = web
        self.knowledge = knowledge
        self.roleplay_dir = store.root / "roleplay"
        self.roleplay_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return (
            self.settings.enabled
            and self.settings.web_learning_enabled
            and self.settings.roleplay_web_enabled
        )

    def _character_lore_path(self, character_id: str) -> Any:
        safe = character_id.replace("/", "_").replace("\\", "_")
        return self.roleplay_dir / f"{safe}_lore.json"

    def should_search(self, message: str, scenario: str = "") -> bool:
        if not self.settings.roleplay_web_auto_search:
            return False
        text = f"{message} {scenario}".strip()
        if len(text) < 3:
            return False
        if re.search(r"^(搜尋|查|learn|search)[:：]", message.strip(), re.I):
            return True
        return any(re.search(p, text, re.I) for p in ROLEPLAY_SEARCH_MARKERS)

    def _build_query(
        self,
        message: str,
        *,
        character_name: str = "",
        scenario: str = "",
        memory_summary: str = "",
    ) -> str:
        if re.search(r"^(搜尋|查|learn|search)[:：]\s*", message.strip(), re.I):
            message = re.sub(r"^(搜尋|查|learn|search)[:：]\s*", "", message.strip(), flags=re.I)
        parts = [message.strip()]
        if character_name:
            parts.append(f"character: {character_name}")
        if scenario:
            parts.append(f"scenario: {scenario[:200]}")
        if memory_summary:
            parts.append(f"story context: {memory_summary[:300]}")
        return " | ".join(p for p in parts if p)

    def _merge_into_character_kb(self, character_id: str, facts: list[str], source: str) -> int:
        if not character_id or not facts:
            return 0
        kb = self.knowledge.get(character_id)
        existing = kb.setdefault("knowledgeBase", {}).setdefault("facts", [])
        seen = {str(f.get("fact", "")).lower() for f in existing}
        added = 0
        for fact in facts:
            f = fact.strip()
            if len(f) < 6 or f.lower() in seen:
                continue
            existing.append(
                {
                    "fact": f,
                    "confidence": 0.72,
                    "source": source,
                }
            )
            seen.add(f.lower())
            added += 1
        kb["knowledgeBase"]["facts"] = existing[-120:]
        self.knowledge.store.write_json(self.knowledge.store.knowledge_path(character_id), kb)
        lore = self.store.read_json(
            self._character_lore_path(character_id),
            {"characterId": character_id, "lore_facts": [], "topics": []},
        )
        lore_facts = lore.setdefault("lore_facts", [])
        for fact in facts:
            if fact.strip() and fact not in lore_facts:
                lore_facts.append(fact.strip())
        lore["lore_facts"] = lore_facts[-80:]
        topics = lore.setdefault("topics", [])
        if source not in topics:
            topics.append(source)
        self.store.write_json(self._character_lore_path(character_id), lore)
        return added

    async def learn_lore(
        self,
        query: str,
        *,
        character_id: str | None = None,
        character_name: str = "",
        scenario: str = "",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "reason": "roleplay_web_disabled"}

        q = self._build_query(query, character_name=character_name, scenario=scenario)
        result = await self.web.learn(q, force_refresh=force_refresh)
        if not result.get("ok"):
            return result

        facts: list[str] = []
        summary = str(result.get("summary", "")).strip()
        if summary:
            facts.append(summary)
        local = self.web.retrieve_local(q, limit=8)
        facts.extend(local)

        added = 0
        if character_id:
            added = self._merge_into_character_kb(character_id, facts, source=f"web:{q[:60]}")

        self.store.append_jsonl(
            self.roleplay_dir / "learn.jsonl",
            {
                "character_id": character_id,
                "query": q,
                "facts_added": added,
                "web_facts": len(facts),
            },
        )
        return {
            **result,
            "character_id": character_id,
            "kb_facts_added": added,
            "lore_facts": facts[:6],
        }

    async def context_for_roleplay(
        self,
        message: str,
        *,
        character_id: str | None = None,
        character_name: str = "",
        scenario: str = "",
        memory_summary: str = "",
        force: bool = False,
    ) -> str:
        if not self.enabled:
            return ""
        if not force and not self.should_search(message, scenario):
            local_hint = self.knowledge.context_hint(character_id) if character_id else ""
            return local_hint

        learned = await self.learn_lore(
            message,
            character_id=character_id,
            character_name=character_name,
            scenario=scenario,
        )
        if not learned.get("ok"):
            return ""

        parts = [ROLEPLAY_CONTEXT_PREFIX]
        summary = str(learned.get("summary", "")).strip()
        if summary:
            parts.append(summary)
        for fact in learned.get("lore_facts") or []:
            parts.append(f"- {fact}")
        if character_id:
            kb_hint = self.knowledge.context_hint(character_id)
            if kb_hint:
                parts.append(kb_hint)
        return "\n\n".join(parts)

    def status(self, character_id: str | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {
            "enabled": self.enabled,
            "auto_search": self.settings.roleplay_web_auto_search,
        }
        if character_id:
            lore = self.store.read_json(
                self._character_lore_path(character_id),
                {"lore_facts": [], "topics": []},
            )
            data["character_id"] = character_id
            data["lore_count"] = len(lore.get("lore_facts", []))
            data["topics"] = lore.get("topics", [])
        return data