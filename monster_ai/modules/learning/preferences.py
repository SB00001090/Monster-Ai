"""User preference learning (Phase C)."""
from __future__ import annotations

import re
from typing import Any

from monster_ai.modules.learning.store import LearningStore


class PreferenceLearner:
    def __init__(self, store: LearningStore) -> None:
        self.store = store

    def get(self, user_id: str) -> dict[str, Any]:
        default = {
            "userId": user_id,
            "preferences": {
                "topicPreferences": {},
                "tonePreference": "casual",
                "responseLength": "medium",
                "interactionStyle": "playful",
            },
            "learningHistory": [],
            "satisfactionScore": 0.75,
        }
        return self.store.read_json(self.store.user_path(user_id), default)

    def _infer_style_updates(self, comment: str) -> dict[str, str]:
        text = (comment or "").lower()
        updates: dict[str, str] = {}
        short_markers = (
            "簡短", "太短", "短一點", "简短", "太短", "shorter", "too long", "太長", "太长",
        )
        long_markers = (
            "詳細", "详细", "長一點", "长一点", "more detail", "longer", "展開", "展开",
        )
        formal_markers = ("正式", "專業", "专业", "formal", "严肃", "嚴肅")
        casual_markers = ("輕鬆", "轻松", "幽默", "casual", "playful", "俏皮")
        if any(m in text for m in short_markers):
            updates["responseLength"] = "short"
        elif any(m in text for m in long_markers):
            updates["responseLength"] = "long"
        if any(m in text for m in formal_markers):
            updates["tonePreference"] = "formal"
            updates["interactionStyle"] = "direct"
        elif any(m in text for m in casual_markers):
            updates["tonePreference"] = "casual"
            updates["interactionStyle"] = "playful"
        return updates

    def update_from_feedback(
        self,
        user_id: str,
        *,
        rating: int | None = None,
        thumbs: str | None = None,
        topics: list[str] | None = None,
        session_id: str = "",
        comment: str = "",
    ) -> dict[str, Any]:
        model = self.get(user_id)
        hist = {
            "sessionId": session_id,
            "rating": rating,
            "thumbs": thumbs,
            "topicsDiscussed": topics or [],
        }
        model["learningHistory"] = (model.get("learningHistory") or [])[-49:] + [hist]

        if rating is not None:
            prev = float(model.get("satisfactionScore", 0.75))
            model["satisfactionScore"] = round(prev * 0.8 + (rating / 5.0) * 0.2, 3)
        elif thumbs == "up":
            prev = float(model.get("satisfactionScore", 0.75))
            model["satisfactionScore"] = round(min(1.0, prev + 0.03), 3)
        elif thumbs == "down":
            prev = float(model.get("satisfactionScore", 0.75))
            model["satisfactionScore"] = round(max(0.0, prev - 0.05), 3)

        prefs = model.setdefault("preferences", {})
        topics_map = prefs.setdefault("topicPreferences", {})
        for topic in topics or []:
            key = topic.lower().strip()
            if key:
                topics_map[key] = round(min(1.0, float(topics_map.get(key, 0.5)) + 0.08), 3)

        style_updates = self._infer_style_updates(comment)
        for key, value in style_updates.items():
            prefs[key] = value

        self.store.write_json(self.store.user_path(user_id), model)
        return model

    def extract_topics(self, text: str) -> list[str]:
        keywords = {
            "anime": r"\b(anime|manga|otaku)\b",
            "gaming": r"\b(game|gaming|steam|playstation|xbox)\b",
            "coding": r"\b(code|python|program|api|bug)\b",
            "music": r"\b(music|song|band)\b",
        }
        found = []
        for name, pattern in keywords.items():
            if re.search(pattern, text, re.I):
                found.append(name)
        return found

    def context_hint(self, user_id: str) -> str:
        model = self.get(user_id)
        prefs = model.get("preferences", {})
        topics = prefs.get("topicPreferences", {})
        top = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
        parts = []
        if top:
            parts.append("User topic interests: " + ", ".join(f"{k}({v:.1f})" for k, v in top))
        sat = model.get("satisfactionScore")
        if sat is not None:
            parts.append(f"User satisfaction trend: {sat:.2f}")
        tone = prefs.get("tonePreference")
        length = prefs.get("responseLength")
        style = prefs.get("interactionStyle")
        if tone:
            parts.append(f"Preferred tone: {tone}")
        if length:
            parts.append(f"Preferred response length: {length}")
        if style:
            parts.append(f"Preferred interaction style: {style}")
        if sat is not None and sat < 0.55:
            parts.append("User recently dissatisfied — prioritize clarity and usefulness.")
        return "\n".join(parts)