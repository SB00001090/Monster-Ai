"""Auto error reporting → targeted fix suggestions → learning ingestion."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIX_TEMPLATES: dict[str, str] = {
    "econnrefused": (
        "Check Python API on :7860 and Node tRPC on :3000. "
        "Run `python main.py` and `pnpm dev`. Retry Cloudflare Tunnel if remote."
    ),
    "unauthorized": "Enable guest mode or complete Google/GitHub OAuth login.",
    "quality_below_threshold": (
        "Raise ComfyUI steps/CFG or switch checkpoint. "
        "Guardian rejects outputs below 70% quality — see /api/guardian/quality/gate."
    ),
    "tunnel_invalid": "Use Cloudflare Tunnel HTTPS URL only — Tailscale and QR codes are removed.",
    "decrypt_failed": "Cloud sync passphrase mismatch — only you can decrypt E2E blobs.",
}


class ErrorLearningStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "error_learning"
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "cases.jsonl"

    def ingest(
        self,
        *,
        error_type: str,
        message: str,
        stack: str | None = None,
        context: str | None = None,
        source: str = "api",
        fix_suggestion: str | None = None,
        code_snippet: str | None = None,
    ) -> dict[str, Any]:
        suggestion = fix_suggestion or self._suggest(message, context or "")
        snippet = code_snippet or self._code_snippet(message, context or "")
        record = {
            "error_type": error_type,
            "message": message,
            "stack": (stack or "")[:4000],
            "context": context,
            "source": source,
            "fix_suggestion": suggestion,
            "code_snippet": snippet,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def _suggest(self, message: str, context: str) -> str:
        blob = f"{message} {context}".lower()
        for key, hint in FIX_TEMPLATES.items():
            if key in blob:
                return hint
        return "Logged to Guardian learning — Grok supervisor will prioritize if recurring."

    def _code_snippet(self, message: str, context: str) -> str:
        blob = f"{message} {context}".lower()
        if "tunnel" in blob or "tailscale" in blob:
            return (
                "# Cloudflare Tunnel only\n"
                "MONSTER_TUNNEL_URL=https://xxx.trycloudflare.com\n"
                "# scripts/callguard/run-tunnel.bat"
            )
        if "quality" in blob or "70" in blob:
            return (
                "# Guardian quality gate\n"
                "learning:\n  min_quality_score: 0.70\n"
                "modules:\n  image:\n    quality:\n      min_alive_score: 0.70"
            )
        if "sync" in blob or "decrypt" in blob:
            return (
                "// E2E cloud sync — passphrase never sent to server\n"
                "await guardianApi.uploadSync({ provider, providerSub, passphrase, bundleType, payload });"
            )
        return ""

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.log_path.is_file():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def summarize(self) -> dict[str, Any]:
        records = self.recent(100)
        counts: dict[str, int] = {}
        for rec in records:
            key = rec.get("error_type", "unknown")
            counts[key] = counts.get(key, 0) + 1
        top = sorted(counts.items(), key=lambda x: -x[1])[:5]
        return {
            "total_cases": len(records),
            "top_error_types": [{"type": t, "count": c} for t, c in top],
        }