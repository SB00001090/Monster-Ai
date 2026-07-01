"""Privacy firewall for Guardian autonomous network learning."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

DENIED_READ_PREFIXES = frozenset(
    {
        "oc_fingerprints",
        "chat_vault",
        "training_vault",
    }
)

FORBIDDEN_OUTBOUND_KEYS = frozenset(
    {
        "owner_id",
        "passphrase",
        "vault_key",
        "image_b64",
        "text",
        "card",
        "fingerprint",
        "watermark",
        "session_id",
        "message",
        "stack",
        "content",
        "description",
    }
)

SENSITIVE_PATTERNS = (
    re.compile(r"MGA-[A-Z0-9-]+", re.I),
    re.compile(r"-----BEGIN", re.I),
)


def is_denied_read_path(path: Path | str, guardian_root: Path) -> bool:
    """Block reads of OC fingerprints, chat vault, and training plaintext paths."""
    try:
        rel = Path(path).resolve().relative_to(guardian_root.resolve())
    except ValueError:
        return False
    if not rel.parts:
        return False
    return rel.parts[0] in DENIED_READ_PREFIXES


def topic_anonymous_id(topic: str) -> str:
    return hashlib.sha256(topic.strip().lower().encode()).hexdigest()[:16]


def _looks_sensitive(text: str) -> bool:
    return any(p.search(text) for p in SENSITIVE_PATTERNS)


def sanitize_outbound(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip private fields; emit anonymous topic IDs and aggregate stats only."""
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key in FORBIDDEN_OUTBOUND_KEYS:
            continue
        if key == "topics" and isinstance(value, list):
            out["topic_ids"] = [
                topic_anonymous_id(item) if isinstance(item, str) else item for item in value
            ]
            continue
        if key == "query" and isinstance(value, str):
            out["topic_id"] = topic_anonymous_id(value)
            continue
        if isinstance(value, dict):
            nested = sanitize_outbound(value)
            if nested:
                out[key] = nested
        elif isinstance(value, list):
            out[key] = [
                sanitize_outbound(item) if isinstance(item, dict) else item
                for item in value
                if not (isinstance(item, str) and _looks_sensitive(item))
            ]
        elif not (isinstance(value, str) and _looks_sensitive(value)):
            out[key] = value
    return out


def assert_outbound_safe(payload: dict[str, Any]) -> tuple[bool, str]:
    for key in FORBIDDEN_OUTBOUND_KEYS:
        if key in payload:
            return False, f"forbidden_key:{key}"
    blob = str(payload).lower()
    if "oc_fingerprints" in blob or "chat_vault" in blob:
        return False, "path_leak"
    return True, ""