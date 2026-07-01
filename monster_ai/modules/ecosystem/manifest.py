"""Load ecosystem bundle manifests."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = ROOT / "data" / "ecosystem" / "bundles.yaml"


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_MANIFEST
    if not p.is_file():
        return {"bundles": {}, "checkpoints": {}, "ollama_models": {}, "comfy_custom_nodes": []}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def list_bundles(manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data = manifest or load_manifest()
    out: list[dict[str, Any]] = []
    for bid, spec in (data.get("bundles") or {}).items():
        out.append(
            {
                "id": bid,
                "label": spec.get("label", bid),
                "label_en": spec.get("label_en", bid),
                "estimated_minutes": spec.get("estimated_minutes", 30),
                "step_count": len(spec.get("steps") or []),
            }
        )
    return out


def bundle_steps(bundle_id: str, manifest: dict[str, Any] | None = None) -> list[str]:
    data = manifest or load_manifest()
    spec = (data.get("bundles") or {}).get(bundle_id)
    if not spec:
        return []
    return list(spec.get("steps") or [])