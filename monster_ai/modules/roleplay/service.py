"""Roleplay chat with character cards, memory, and self-repair."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from monster_ai.config import Settings
from monster_ai.core.generation_history import GenerationHistory
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.image.comfyui import ImageService
from monster_ai.modules.roleplay.character_card import (
    CharacterCard,
    find_card_path,
    load_card_file,
    save_card,
)
from monster_ai.modules.roleplay.memory import MemoryManager
from monster_ai.modules.roleplay.portrait import build_portrait_prompt
from monster_ai.persona.grok import GROK_ROLEPLAY_APPENDIX, resolve_persona
from monster_ai.modules.roleplay.session import RoleplaySession, SessionStore

if TYPE_CHECKING:
    from monster_ai.modules.learning.engine import LearningEngine


class RoleplayService:
    name = "roleplay"

    def __init__(
        self,
        settings: Settings,
        repair: SelfRepairEngine,
        image_service: ImageService | None = None,
        history: GenerationHistory | None = None,
        learning: LearningEngine | None = None,
    ) -> None:
        self.settings = settings
        self.repair = repair
        self.image = image_service
        self.history = history
        self.learning = learning
        self.memory = MemoryManager(settings, repair)
        self.characters_dir = Path(settings.modules.roleplay.characters_dir)
        self.avatars_dir = self.characters_dir / "avatars"
        self.avatars_dir.mkdir(parents=True, exist_ok=True)
        self.store = SessionStore(Path(settings.modules.roleplay.chats_dir))

    async def health(self) -> dict[str, Any]:
        if not self.settings.modules.roleplay.enabled:
            return {"enabled": False, "healthy": False, "message": "Module disabled"}
        chars = len(list(self.characters_dir.glob("*.json"))) if self.characters_dir.exists() else 0
        return {
            "enabled": True,
            "healthy": True,
            "characters": chars,
            "sessions": len(self.store.list_sessions()),
            "backend": self.repair.state.active_backend,
        }

    def list_characters(self) -> list[dict[str, Any]]:
        if not self.characters_dir.exists():
            return []
        result = []
        for path in self.characters_dir.glob("*.json"):
            try:
                card = CharacterCard.model_validate(json.loads(path.read_text(encoding="utf-8")))
                entry = {"id": card.id, "name": card.name, "file": path.name}
                if card.avatar:
                    entry["avatar_url"] = f"/api/roleplay/files/avatars/{Path(card.avatar).name}"
                result.append(entry)
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(result, key=lambda x: x["name"].lower())

    def get_character(self, character_id: str) -> CharacterCard | None:
        for path in self.characters_dir.glob("*.json"):
            try:
                card = CharacterCard.model_validate(json.loads(path.read_text(encoding="utf-8")))
                if card.id == character_id:
                    return card
            except (json.JSONDecodeError, OSError):
                continue
        return None

    def import_character(self, path: Path) -> CharacterCard:
        card = load_card_file(path)
        save_card(card, self.characters_dir)
        return card

    def import_character_json(self, data: dict[str, Any]) -> CharacterCard:
        card = CharacterCard.model_validate(data)
        save_card(card, self.characters_dir)
        return card

    def delete_character(self, character_id: str) -> bool:
        path = find_card_path(character_id, self.characters_dir)
        if not path:
            return False
        card = self.get_character(character_id)
        path.unlink(missing_ok=True)
        if card and card.avatar:
            avatar = Path(card.avatar)
            if not avatar.is_absolute():
                avatar = Path(".") / avatar
            if avatar.exists():
                avatar.unlink(missing_ok=True)
        return True

    def list_sessions(self) -> list[dict[str, Any]]:
        return self.store.list_sessions()

    def create_session(self, title: str = "New Session", character_id: str | None = None) -> RoleplaySession:
        character = self.get_character(character_id) if character_id else None
        return self.store.create(title=title, character=character)

    def get_session(self, session_id: str) -> RoleplaySession | None:
        return self.store.load(session_id)

    async def send_message(
        self,
        session_id: str,
        message: str,
        character_id: str | None = None,
        *,
        user_id: str | None = None,
        web_search: bool | None = None,
    ) -> dict[str, Any]:
        session = self.store.load(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        active_id = character_id or session.active_character_id
        character = self.get_character(active_id) if active_id else None
        if character:
            session.active_character_id = character.id
            if character.id not in session.participant_ids:
                session.participant_ids.append(character.id)

        session.messages.append({
            "role": "user",
            "content": message,
        })
        session.message_count += 1

        base = character.build_system_prompt() if character else "You are a helpful roleplay assistant."
        if self.settings.persona.enabled and self.settings.persona.default_mode == "grok":
            base = f"{base}\n{GROK_ROLEPLAY_APPENDIX}"
        system = self.memory.build_context_prompt(
            base,
            session.memory_summary,
            session.messages,
        )
        resolved = resolve_persona(
            self.settings.persona.default_mode if self.settings.persona.enabled else "off",
            system,
            chat_mode="roleplay",
            locale=self.settings.persona.response_locale,
        )
        effective_user = user_id or session_id
        quality_meta: dict[str, Any] | None = None
        web_lore_used = False
        if self.learning and self.learning.settings.enabled:
            gen = await self.learning.generate(
                user_message=message,
                system=resolved,
                user_id=effective_user,
                character_id=character.id if character else None,
                session_id=session_id,
                web_search=web_search,
                mode="roleplay",
                character_name=character.name if character else "",
                scenario=character.scenario if character else "",
                memory_summary=session.memory_summary,
            )
            reply = gen["content"]
            quality_meta = gen.get("quality")
            web_lore_used = bool(gen.get("web_knowledge_used"))
        else:
            enriched = resolved
            if self.learning:
                enriched = self.learning.enrich_system(
                    resolved,
                    user_id=effective_user,
                    character_id=character.id if character else None,
                )
            reply = await self.repair.generate(message, system=enriched)

        session.messages.append({
            "role": "assistant",
            "character_id": character.id if character else None,
            "character_name": character.name if character else "Assistant",
            "content": reply,
        })
        session.message_count += 1
        session.messages = self.memory.trim_messages(session.messages)
        session.memory_summary = await self.memory.maybe_summarize(
            session.messages,
            session.memory_summary,
            session.message_count,
        )
        self.store.save(session)

        out: dict[str, Any] = {
            "role": "assistant",
            "content": reply,
            "backend": self.repair.state.active_backend,
            "session_id": session.id,
            "character_name": character.name if character else "Assistant",
        }
        if quality_meta:
            out["quality"] = quality_meta
        if web_lore_used:
            out["web_lore_used"] = True
        return out

    async def learn_lore(
        self,
        query: str,
        *,
        character_id: str | None = None,
        session_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        if not self.learning:
            return {"ok": False, "reason": "learning_not_connected"}
        character = self.get_character(character_id) if character_id else None
        if not character and session_id:
            session = self.get_session(session_id)
            if session and session.active_character_id:
                character = self.get_character(session.active_character_id)
        return await self.learning.learn_roleplay_lore(
            query,
            character_id=character.id if character else character_id,
            character_name=character.name if character else "",
            scenario=character.scenario if character else "",
            force_refresh=force_refresh,
        )

    async def generate_portrait(
        self,
        character_id: str | None,
        *,
        description: str | None = None,
        quality_filter: bool | None = True,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        if not self.image:
            raise RuntimeError("Image service not available")
        card = self.get_character(character_id) if character_id else None
        prompt = build_portrait_prompt(card, description)
        result = await self.image.generate(
            prompt,
            width=width,
            height=height,
            quality_filter=quality_filter,
            record_history=False,
        )
        if self.history:
            self.history.record(
                "portrait",
                {**result, "character_id": character_id, "description": description},
            )
        return result

    def set_avatar(self, character_id: str, image_path: str) -> CharacterCard:
        card = self.get_character(character_id)
        if not card:
            raise ValueError(f"Character not found: {character_id}")
        src = Path(image_path)
        if not src.is_absolute():
            src = Path(".") / src
        if not src.exists():
            raise ValueError(f"Image not found: {image_path}")
        dest = self.avatars_dir / f"{character_id}.png"
        shutil.copy2(src, dest)
        card.avatar = str(dest.relative_to(Path(".")).as_posix())
        save_card(card, self.characters_dir)
        return card