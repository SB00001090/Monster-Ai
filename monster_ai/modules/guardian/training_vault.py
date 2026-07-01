"""Encrypted training asset vault — good/bad images, templates, prompts, LoRA datasets."""
from __future__ import annotations

import base64
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from monster_ai.modules.guardian.crypto import EncryptedBlob, decrypt_payload, encrypt_payload

if TYPE_CHECKING:
    from monster_ai.modules.guardian.key_manager import TrainingKeyManager

MAGIC = b"MGTR\x01"
EXT = ".mgtrain"
LABELS = frozenset({"good", "bad", "template", "prompt", "lora"})


class TrainingVault:
    """All training assets stored as AES-256-GCM encrypted blobs — no plaintext on disk."""

    def __init__(self, data_dir: Path, key_manager: TrainingKeyManager) -> None:
        self.root = data_dir / "training_vault"
        self.key_manager = key_manager
        for label in LABELS:
            (self.root / label).mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.enc"

    def _key(self) -> bytes:
        key = self.key_manager.get_session_key()
        if key is None:
            raise PermissionError("Training vault locked — unlock with passphrase or hardware key")
        return key

    def _encrypt_bundle(self, bundle: dict[str, Any]) -> EncryptedBlob:
        return encrypt_payload(bundle, self._key())

    def _decrypt_bundle(self, blob: EncryptedBlob) -> dict[str, Any]:
        data = decrypt_payload(blob, self._key())
        return data if isinstance(data, dict) else {"payload": data}

    def store_image_asset(
        self,
        src: Path,
        *,
        label: str,
        metadata: dict[str, Any],
    ) -> Path:
        if label not in LABELS:
            raise ValueError(f"Invalid label: {label}")
        stem = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        image_bytes = src.read_bytes()
        bundle = {
            "id": stem,
            "label": label,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
            "image_b64": base64.b64encode(image_bytes).decode("ascii"),
            "content_type": "image/png",
        }
        blob = self._encrypt_bundle(bundle)
        out = self.root / label / f"{stem}{EXT}"
        out.write_text(json.dumps(blob.to_dict(), ensure_ascii=False), encoding="utf-8")
        self._append_index({"id": stem, "label": label, "path": str(out.relative_to(self.root))})
        return out

    def store_text_asset(
        self,
        *,
        label: str,
        name: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        if label not in {"template", "prompt", "lora"}:
            raise ValueError(f"Text assets require template|prompt|lora label, got {label}")
        stem = f"{name}_{uuid.uuid4().hex[:6]}"
        bundle = {
            "id": stem,
            "label": label,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "text": content,
            "content_type": "text/plain",
        }
        blob = self._encrypt_bundle(bundle)
        out = self.root / label / f"{stem}{EXT}"
        out.write_text(json.dumps(blob.to_dict(), ensure_ascii=False), encoding="utf-8")
        self._append_index({"id": stem, "label": label, "path": str(out.relative_to(self.root))})
        return out

    def _append_index(self, entry: dict[str, str]) -> None:
        index = self._read_index()
        index.append(entry)
        blob = self._encrypt_bundle({"entries": index})
        self._index_path.write_text(json.dumps(blob.to_dict(), ensure_ascii=False), encoding="utf-8")

    def _read_index(self) -> list[dict[str, str]]:
        if not self._index_path.is_file():
            return []
        try:
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
            blob = EncryptedBlob.from_dict(raw)
            data = self._decrypt_bundle(blob)
            entries = data.get("entries", [])
            return entries if isinstance(entries, list) else []
        except Exception:  # noqa: BLE001
            return []

    def read_asset_metadata(self, asset_id: str) -> dict[str, Any] | None:
        """Return decrypted metadata only — image bytes stay in encrypted file until explicit decrypt."""
        for entry in self._read_index():
            if entry.get("id") != asset_id:
                continue
            path = self.root / str(entry["path"])
            if not path.is_file():
                return None
            blob = EncryptedBlob.from_dict(json.loads(path.read_text(encoding="utf-8")))
            data = self._decrypt_bundle(blob)
            meta = dict(data.get("metadata") or {})
            meta.update({"id": data.get("id"), "label": data.get("label"), "stored_at": data.get("stored_at")})
            return meta
        return None

    def decrypt_asset_to_memory(self, asset_id: str) -> dict[str, Any] | None:
        """Decrypt full asset in memory — never writes plaintext to disk."""
        for entry in self._read_index():
            if entry.get("id") != asset_id:
                continue
            path = self.root / str(entry["path"])
            if not path.is_file():
                return None
            blob = EncryptedBlob.from_dict(json.loads(path.read_text(encoding="utf-8")))
            return self._decrypt_bundle(blob)
        return None

    def list_assets(self, label: str | None = None) -> list[dict[str, str]]:
        entries = self._read_index()
        if label:
            entries = [e for e in entries if e.get("label") == label]
        return entries

    def quality_log_records(self, limit: int = 2000) -> list[dict[str, Any]]:
        """Build quality log from encrypted good/bad metadata for learning engine."""
        records: list[dict[str, Any]] = []
        for entry in self._read_index():
            if entry.get("label") not in {"good", "bad"}:
                continue
            meta = self.read_asset_metadata(str(entry.get("id", "")))
            if meta:
                records.append(meta)
        return records[-limit:]

    def export_encrypted_bundle(self) -> dict[str, Any]:
        """E2E cloud sync — export all encrypted blobs without decryption."""
        assets: list[dict[str, Any]] = []
        for entry in self._read_index():
            path = self.root / str(entry["path"])
            if path.is_file():
                assets.append(
                    {
                        "id": entry.get("id"),
                        "label": entry.get("label"),
                        "ciphertext": json.loads(path.read_text(encoding="utf-8")),
                    }
                )
        index_blob = None
        if self._index_path.is_file():
            index_blob = json.loads(self._index_path.read_text(encoding="utf-8"))
        return {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "index": index_blob,
            "assets": assets,
        }

    def import_encrypted_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """Restore E2E encrypted training vault from cloud — still ciphertext on disk."""
        imported = 0
        for asset in bundle.get("assets") or []:
            label = str(asset.get("label", "good"))
            aid = str(asset.get("id", uuid.uuid4().hex[:8]))
            ct = asset.get("ciphertext")
            if not ct:
                continue
            out = self.root / label / f"{aid}{EXT}"
            out.write_text(json.dumps(ct, ensure_ascii=False), encoding="utf-8")
            self._append_index({"id": aid, "label": label, "path": str(out.relative_to(self.root))})
            imported += 1
        if bundle.get("index"):
            self._index_path.write_text(
                json.dumps(bundle["index"], ensure_ascii=False),
                encoding="utf-8",
            )
        return {"ok": True, "imported": imported}

    def migrate_plaintext_dir(
        self,
        src_dir: Path,
        *,
        label: str,
        delete_plaintext: bool = True,
    ) -> dict[str, Any]:
        """Encrypt legacy plaintext PNG+JSON pairs into vault."""
        migrated = 0
        if not src_dir.is_dir():
            return {"ok": True, "migrated": 0}
        for png in src_dir.glob("*.png"):
            meta_path = src_dir / f"{png.stem}.json"
            metadata: dict[str, Any] = {"label": label, "legacy": True}
            if meta_path.is_file():
                try:
                    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            self.store_image_asset(png, label=label, metadata=metadata)
            migrated += 1
            if delete_plaintext:
                png.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
        return {"ok": True, "migrated": migrated, "label": label}

    def status(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for entry in self._read_index():
            lbl = str(entry.get("label", "unknown"))
            counts[lbl] = counts.get(lbl, 0) + 1
        return {
            "encrypted": True,
            "plaintext_forbidden": True,
            "extension": EXT,
            "counts": counts,
            "total": sum(counts.values()),
            "key": self.key_manager.status(),
        }