"""Dify API client — workflow run + chat."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DifyClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "reason": "dify_not_configured"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.base_url}/v1/parameters",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return {"ok": r.status_code < 400, "status": r.status_code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    async def run_workflow(
        self,
        workflow_id: str,
        *,
        inputs: dict[str, Any],
        user: str = "monster-ai",
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("dify_not_configured")
        payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/v1/workflows/{workflow_id}/run",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if r.status_code >= 400:
                raise RuntimeError(f"dify_error:{r.status_code}:{r.text[:500]}")
            return r.json()