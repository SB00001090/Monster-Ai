"""Chat and roleplay message handling."""
from __future__ import annotations

from typing import Any

from typing import TYPE_CHECKING

from monster_ai.config import Settings
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.persona.grok import resolve_persona

if TYPE_CHECKING:
    from monster_ai.modules.learning.engine import LearningEngine


class ChatService:
    name = "chat"

    def __init__(
        self,
        repair: SelfRepairEngine,
        settings: Settings,
        learning: LearningEngine | None = None,
    ) -> None:
        self.repair = repair
        self.settings = settings
        self.learning = learning

    async def health(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "backend": self.repair.state.active_backend,
            "primary_ok": self.repair.state.primary_ok,
        }

    async def send(
        self,
        message: str,
        system: str | None = None,
        persona_mode: str | None = None,
        *,
        user_id: str = "default",
        session_id: str = "chat",
    ) -> dict[str, Any]:
        persona = self.settings.persona
        mode = persona_mode or (persona.default_mode if persona.enabled else "off")
        if persona_mode and not persona.allow_user_override:
            mode = persona.default_mode if persona.enabled else "off"
        resolved = resolve_persona(
            mode,
            system,
            chat_mode="chat",
            locale=self.settings.persona.response_locale,
        )
        if self.learning and self.learning.settings.enabled:
            result = await self.learning.generate(
                user_message=message,
                system=resolved,
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "role": "assistant",
                "content": result["content"],
                "backend": result["backend"],
                "quality": result.get("quality"),
            }
        enriched = resolved
        if self.learning:
            enriched = self.learning.enrich_system(resolved, user_id=user_id)
        content = await self.repair.generate(message, system=enriched)
        return {
            "role": "assistant",
            "content": content,
            "backend": self.repair.state.active_backend,
        }