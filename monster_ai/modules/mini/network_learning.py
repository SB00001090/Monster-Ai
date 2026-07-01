"""Optional consent-based network learning for Mini Monster AI."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from monster_ai.modules.learning.store import LearningStore


class MiniNetworkLearner:
    """Safe optional network: model metadata fetch + anonymous metrics export."""

    def __init__(
        self,
        store: LearningStore,
        *,
        enabled: bool = False,
        consent_file: str = "./data/mini/network_consent.json",
        allow_downloads: bool = False,
        allow_metrics_upload: bool = False,
        metrics_endpoint: str = "",
        civitai_enabled: bool = True,
        huggingface_enabled: bool = True,
        network_guard: Callable[[], tuple[bool, str]] | None = None,
    ) -> None:
        self.store = store
        self.enabled = enabled
        self.consent_path = Path(consent_file)
        self.allow_downloads = allow_downloads
        self.allow_metrics_upload = allow_metrics_upload
        self.metrics_endpoint = metrics_endpoint.rstrip("/")
        self.civitai_enabled = civitai_enabled
        self.huggingface_enabled = huggingface_enabled
        self._guard = network_guard
        self.cache_dir = Path(consent_file).parent / "network_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _network_ok(self) -> tuple[bool, str]:
        if not self.enabled:
            return False, "network_disabled"
        if self._guard:
            return self._guard()
        return True, ""

    def consent_status(self) -> dict[str, Any]:
        data = self.store.read_json(self.consent_path, {})
        return {
            "enabled": self.enabled,
            "user_consented": bool(data.get("consented")),
            "consented_at": data.get("consented_at"),
            "allow_downloads": self.allow_downloads and bool(data.get("consented")),
            "allow_metrics_upload": self.allow_metrics_upload and bool(data.get("consented")),
        }

    def grant_consent(self, *, downloads: bool = False, metrics: bool = False) -> dict[str, Any]:
        self.store.write_json(
            self.consent_path,
            {
                "consented": True,
                "consented_at": time.time(),
                "downloads": downloads,
                "metrics": metrics,
            },
        )
        return self.consent_status()

    def revoke_consent(self) -> dict[str, Any]:
        if self.consent_path.is_file():
            self.consent_path.unlink(missing_ok=True)
        return self.consent_status()

    async def fetch_model_catalog_hint(self, query: str) -> dict[str, Any]:
        """Read-only metadata — does not download weights without explicit consent."""
        ok, reason = self._network_ok()
        if not ok:
            return {"ok": False, "reason": reason}

        consent = self.consent_status()
        if not consent["user_consented"]:
            return {"ok": False, "reason": "consent_required"}

        hints: list[dict[str, str]] = []
        q = query.strip().lower()
        if self.civitai_enabled:
            hints.append(
                {
                    "source": "civitai",
                    "hint": f"Search CivitAI for: {query}",
                    "url": f"https://civitai.com/models?query={query.replace(' ', '%20')}",
                }
            )
        if self.huggingface_enabled:
            hints.append(
                {
                    "source": "huggingface",
                    "hint": f"Search HuggingFace for: {query}",
                    "url": f"https://huggingface.co/models?search={query.replace(' ', '+')}",
                }
            )

        cache_key = hashlib.sha256(q.encode()).hexdigest()[:16]
        cache_file = self.cache_dir / f"catalog_{cache_key}.json"
        payload = {"ok": True, "query": query, "hints": hints, "cached_at": time.time()}
        cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    async def upload_likeness_feedback(
        self,
        *,
        similarity_score: float,
        template_id: str,
        ok: bool,
    ) -> dict[str, Any]:
        ok_net, reason = self._network_ok()
        if not ok_net:
            return {"ok": False, "reason": reason}
        consent = self.consent_status()
        if not consent.get("allow_metrics_upload"):
            return {"ok": False, "reason": "metrics_upload_not_consented"}
        anon = {
            "ts": time.time(),
            "type": "likeness_feedback",
            "similarity_score": round(similarity_score, 3),
            "template_id": template_id,
            "ok": ok,
        }
        queue = self.cache_dir / "likeness_feedback_queue.jsonl"
        with queue.open("a", encoding="utf-8") as f:
            f.write(json.dumps(anon, ensure_ascii=False) + "\n")
        return {"ok": True, "queued_local": True}

    async def upload_anonymous_metrics(self, summary: dict[str, Any]) -> dict[str, Any]:
        ok, reason = self._network_ok()
        if not ok:
            return {"ok": False, "reason": reason}
        consent = self.consent_status()
        if not consent.get("allow_metrics_upload"):
            return {"ok": False, "reason": "metrics_upload_not_consented"}
        if not self.metrics_endpoint:
            # Local-only queue for future sync
            queue = self.cache_dir / "metrics_queue.jsonl"
            anon = {
                "ts": time.time(),
                "success_rate": summary.get("success_rate"),
                "window_size": summary.get("window_size"),
                "template_stats": summary.get("by_template"),
            }
            with queue.open("a", encoding="utf-8") as f:
                f.write(json.dumps(anon, ensure_ascii=False) + "\n")
            return {"ok": True, "queued_local": True}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(self.metrics_endpoint, json=summary)
                return {"ok": r.status_code < 400, "status": r.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "reason": str(exc)}