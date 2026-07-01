"""OC anti-plagiarism — local fingerprint, watermark metadata, network shield."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _canonical_oc(card: dict[str, Any]) -> str:
    fields = {
        "name": card.get("name", ""),
        "description": card.get("description", ""),
        "personality": card.get("personality", ""),
        "worldview": card.get("worldview", ""),
        "scenario": card.get("scenario", ""),
        "first_mes": card.get("first_mes", card.get("openingLine", "")),
    }
    return json.dumps(fields, ensure_ascii=False, sort_keys=True)


def generate_fingerprint(card: dict[str, Any], *, owner_id: str = "local") -> dict[str, Any]:
    canonical = _canonical_oc(card)
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    salt = secrets.token_hex(8)
    fingerprint = hashlib.sha256(f"{owner_id}:{content_hash}:{salt}".encode()).hexdigest()[:32]
    return {
        "fingerprint": fingerprint,
        "content_hash": content_hash,
        "salt": salt,
        "owner_id": owner_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "network_learning_allowed": False,
        "watermark": f"MGA-{fingerprint[:8].upper()}",
    }


def verify_ownership(
    card: dict[str, Any],
    record: dict[str, Any],
    *,
    owner_id: str = "local",
) -> bool:
    canonical = _canonical_oc(card)
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if content_hash != record.get("content_hash"):
        return False
    expected = hashlib.sha256(
        f"{owner_id}:{content_hash}:{record.get('salt', '')}".encode()
    ).hexdigest()[:32]
    return expected == record.get("fingerprint")


def embed_watermark(card: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    out = dict(card)
    meta = dict(out.get("extensions", {}).get("monster_guardian", {}))
    meta.update(
        {
            "watermark": record.get("watermark"),
            "fingerprint": record.get("fingerprint"),
            "network_learning_allowed": record.get("network_learning_allowed", False),
        }
    )
    ext = dict(out.get("extensions", {}))
    ext["monster_guardian"] = meta
    out["extensions"] = ext
    return out


class OCFingerprintStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "oc_fingerprints"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, character_id: str) -> Path:
        safe = hashlib.sha256(character_id.encode()).hexdigest()[:16]
        return self.root / f"{safe}.json"

    def save(self, character_id: str, record: dict[str, Any]) -> None:
        self._path(character_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, character_id: str) -> dict[str, Any] | None:
        path = self._path(character_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))