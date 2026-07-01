"""Training vault key — user passphrase + hardware binding (MonsterLock fingerprint)."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from monster_ai.config import GuardianSettings

SALT_SIZE = 16


class TrainingKeyManager:
    """Derives AES-256 keys from user passphrase and/or device hardware fingerprint."""

    def __init__(
        self,
        settings: GuardianSettings,
        root: Path,
        *,
        hardware_fingerprint: str = "",
    ) -> None:
        self.settings = settings
        self.root = root
        self._hw = hardware_fingerprint
        self._meta_path = Path(settings.data_dir) / "training_vault" / "key_meta.json"
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)
        self._session_key: bytes | None = None

    def set_hardware_fingerprint(self, fp: str) -> None:
        self._hw = fp

    def _load_meta(self) -> dict[str, Any]:
        if not self._meta_path.is_file():
            return {}
        try:
            return json.loads(self._meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_meta(self, meta: dict[str, Any]) -> None:
        self._meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_salt(self) -> bytes:
        meta = self._load_meta()
        if meta.get("salt_b64"):
            return base64.b64decode(str(meta["salt_b64"]))
        salt = secrets.token_bytes(SALT_SIZE)
        meta["salt_b64"] = base64.b64encode(salt).decode("ascii")
        meta["hardware_bound"] = self.settings.bind_hardware_key
        self._save_meta(meta)
        return salt

    def derive_key(self, passphrase: str | None = None) -> bytes:
        salt = self.ensure_salt()
        material_parts: list[str] = []
        if self.settings.bind_hardware_key and self._hw:
            material_parts.append(f"hw:{self._hw}")
        if passphrase:
            material_parts.append(f"pw:{passphrase}")
        elif self.settings.require_user_passphrase:
            raise ValueError("User passphrase required for training vault")
        if not material_parts:
            material_parts.append(f"local:{self.settings.data_dir}")
        material = "|".join(material_parts)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"monster-guardian-training-v1",
        )
        return hkdf.derive(material.encode("utf-8"))

    def unlock(self, passphrase: str | None = None) -> dict[str, Any]:
        key = self.derive_key(passphrase)
        self._session_key = key
        fp = hashlib.sha256(key).hexdigest()[:16]
        return {"ok": True, "unlocked": True, "key_fingerprint": fp}

    def lock(self) -> None:
        if self._session_key:
            self._session_key = b"\x00" * len(self._session_key)
        self._session_key = None

    @property
    def is_unlocked(self) -> bool:
        return self._session_key is not None

    def get_session_key(self) -> bytes | None:
        if self._session_key:
            return self._session_key
        if self.settings.bind_hardware_key and not self.settings.require_user_passphrase:
            try:
                self._session_key = self.derive_key(None)
                return self._session_key
            except ValueError:
                return None
        return None

    def status(self) -> dict[str, Any]:
        meta = self._load_meta()
        return {
            "training_encryption_enabled": self.settings.training_encryption_enabled,
            "bind_hardware_key": self.settings.bind_hardware_key,
            "require_user_passphrase": self.settings.require_user_passphrase,
            "hardware_bound": bool(self._hw),
            "unlocked": self.is_unlocked or self.get_session_key() is not None,
            "key_meta_present": bool(meta.get("salt_b64")),
        }