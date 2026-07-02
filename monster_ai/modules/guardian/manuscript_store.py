"""Manuscript version history — OC cards and backstory rollback."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ManuscriptStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "manuscripts"
        self.root.mkdir(parents=True, exist_ok=True)

    def _oc_dir(self, oc_id: str) -> Path:
        safe = hashlib.sha256(oc_id.encode()).hexdigest()[:16]
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _index_path(self, oc_id: str) -> Path:
        return self._oc_dir(oc_id) / "index.json"

    def _load_index(self, oc_id: str) -> list[dict[str, Any]]:
        path = self._index_path(oc_id)
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_index(self, oc_id: str, index: list[dict[str, Any]]) -> None:
        self._index_path(oc_id).write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_version(
        self,
        oc_id: str,
        *,
        content: dict[str, Any],
        author: str = "local",
        label: str = "auto",
        parent_version: int | None = None,
    ) -> dict[str, Any]:
        index = self._load_index(oc_id)
        version = len(index) + 1
        content_hash = hashlib.sha256(
            json.dumps(content, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:16]
        meta = {
            "version": version,
            "oc_id": oc_id,
            "label": label,
            "author": author,
            "parent_version": parent_version or (version - 1 if version > 1 else None),
            "content_hash": content_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        blob_path = self._oc_dir(oc_id) / f"v{version:03d}.json"
        blob_path.write_text(
            json.dumps({"meta": meta, "content": content}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        index.append(meta)
        self._save_index(oc_id, index)
        return meta

    def list_versions(self, oc_id: str) -> list[dict[str, Any]]:
        return self._load_index(oc_id)

    def get_version(self, oc_id: str, version: int) -> dict[str, Any] | None:
        path = self._oc_dir(oc_id) / f"v{version:03d}.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def restore_version(self, oc_id: str, version: int) -> dict[str, Any]:
        blob = self.get_version(oc_id, version)
        if blob is None:
            return {"ok": False, "reason": "version_not_found"}
        content = blob.get("content")
        if not isinstance(content, dict):
            return {"ok": False, "reason": "invalid_content"}
        new_meta = self.save_version(
            oc_id,
            content=content,
            author="restore",
            label=f"restored_from_v{version}",
            parent_version=version,
        )
        return {
            "ok": True,
            "restored_from": version,
            "new_version": new_meta["version"],
            "content": content,
        }

    def diff_versions(self, oc_id: str, v1: int, v2: int) -> dict[str, Any]:
        a = self.get_version(oc_id, v1)
        b = self.get_version(oc_id, v2)
        if a is None or b is None:
            return {"ok": False, "reason": "version_not_found"}
        ca = a.get("content") if isinstance(a.get("content"), dict) else {}
        cb = b.get("content") if isinstance(b.get("content"), dict) else {}
        keys = sorted(set(ca.keys()) | set(cb.keys()))
        changes: list[dict[str, Any]] = []
        for key in keys:
            va, vb = ca.get(key), cb.get(key)
            if va != vb:
                changes.append({"field": key, "from": va, "to": vb})
        return {
            "ok": True,
            "oc_id": oc_id,
            "v1": v1,
            "v2": v2,
            "change_count": len(changes),
            "changes": changes,
        }