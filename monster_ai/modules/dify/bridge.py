"""Bridge Monster AI image gen ↔ Dify workflow outputs."""
from __future__ import annotations

import os
from typing import Any

from monster_ai.config import DifySettings
from monster_ai.modules.dify.client import DifyClient


class DifyBridge:
    def __init__(self, settings: DifySettings) -> None:
        self.settings = settings
        api_key = os.environ.get(settings.api_key_env, "")
        self.client = DifyClient(settings.api_url, api_key)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "configured": self.client.enabled,
            "workflow_image": self.settings.workflow_image_id or None,
            "workflow_multimodal": self.settings.workflow_multimodal_id or None,
            "min_quality_score": self.settings.min_quality_score,
        }

    async def health(self) -> dict[str, Any]:
        base = self.status()
        if self.client.enabled:
            base["dify"] = await self.client.health()
        return base

    async def generate_image(
        self,
        *,
        prompt: str,
        template_id: str = "stable",
        locale: str = "zh-TW",
        fallback_fn: Any,
    ) -> dict[str, Any]:
        """Run Dify workflow; on failure or missing config, call Monster fallback."""
        if not self.settings.enabled or not self.client.enabled:
            return await fallback_fn()

        wf_id = self.settings.workflow_image_id
        if not wf_id:
            return await fallback_fn()

        try:
            raw = await self.client.run_workflow(
                wf_id,
                inputs={
                    "prompt": prompt,
                    "template_id": template_id,
                    "locale": locale,
                    "min_quality": self.settings.min_quality_score,
                },
            )
            outputs = (raw.get("data") or {}).get("outputs") or raw.get("outputs") or {}
            if isinstance(outputs, dict) and outputs.get("image_url"):
                return {
                    "ok": True,
                    "provider": "dify",
                    "url": outputs["image_url"],
                    "quality": outputs.get("quality"),
                    "dify": raw,
                }
        except Exception as exc:  # noqa: BLE001
            if not self.settings.fallback_to_monster:
                raise
            result = await fallback_fn()
            result["dify_fallback_reason"] = str(exc)
            return result

        result = await fallback_fn()
        result["dify_fallback_reason"] = "empty_workflow_output"
        return result