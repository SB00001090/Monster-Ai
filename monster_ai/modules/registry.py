"""Register and manage optional feature modules."""
from __future__ import annotations

from typing import Any, Protocol

from monster_ai.config import Settings


class ModuleService(Protocol):
    name: str

    async def health(self) -> dict[str, Any]:
        ...


class ModuleRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._modules: dict[str, ModuleService] = {}

    def register(self, module: ModuleService) -> None:
        self._modules[module.name] = module

    def get_enabled(self) -> list[ModuleService]:
        m = self.settings.modules
        flags = {
            "chat": m.chat.enabled,
            "roleplay": m.roleplay.enabled,
            "image": m.image.enabled,
            "video": m.video.enabled,
            "discord": m.discord.enabled,
            "tts": m.tts.enabled,
            "training": m.training.enabled,
            "mini": m.mini.enabled,
        }
        return [mod for name, mod in self._modules.items() if flags.get(name, False)]

    async def health_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {}
        for name, module in self._modules.items():
            report[name] = await module.health()
        return report