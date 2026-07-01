"""User-controlled E2E encryption for Guardian cloud sync and chat vault."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAGIC = b"MGAE\x01"  # Monster Guardian AI Encrypted v1
NONCE_SIZE = 12
SALT_SIZE = 16


@dataclass
class EncryptedBlob:
    ciphertext_b64: str
    salt_b64: str
    nonce_b64: str
    algorithm: str = "AES-256-GCM"
    kdf: str = "HKDF-SHA256"

    def to_dict(self) -> dict[str, str]:
        return {
            "ciphertext": self.ciphertext_b64,
            "salt": self.salt_b64,
            "nonce": self.nonce_b64,
            "algorithm": self.algorithm,
            "kdf": self.kdf,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncryptedBlob:
        return cls(
            ciphertext_b64=str(data["ciphertext"]),
            salt_b64=str(data["salt"]),
            nonce_b64=str(data["nonce"]),
            algorithm=str(data.get("algorithm", "AES-256-GCM")),
            kdf=str(data.get("kdf", "HKDF-SHA256")),
        )


def derive_user_key(passphrase: str, salt: bytes, *, info: bytes = b"guardian-e2e-v1") -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info)
    return hkdf.derive(passphrase.encode("utf-8"))


def derive_oauth_key(
    provider: str,
    provider_sub: str,
    user_passphrase: str,
    salt: bytes,
) -> bytes:
    """Combine OAuth identity + user passphrase — server never sees plaintext key."""
    material = f"{provider}:{provider_sub}:{user_passphrase}"
    return derive_user_key(material, salt, info=b"guardian-oauth-e2e-v1")


def oauth_user_hash(provider: str, provider_sub: str) -> str:
    digest = hashlib.sha256(f"{provider}:{provider_sub}".encode()).hexdigest()
    return digest[:32]


def encrypt_payload(payload: dict[str, Any] | list[Any], key: bytes) -> EncryptedBlob:
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    aes = AESGCM(key)
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ct = aes.encrypt(nonce, plaintext, MAGIC)
    return EncryptedBlob(
        ciphertext_b64=base64.b64encode(ct).decode("ascii"),
        salt_b64=base64.b64encode(salt).decode("ascii"),
        nonce_b64=base64.b64encode(nonce).decode("ascii"),
    )


def decrypt_payload(blob: EncryptedBlob, key: bytes) -> dict[str, Any] | list[Any]:
    aes = AESGCM(key)
    nonce = base64.b64decode(blob.nonce_b64)
    ct = base64.b64decode(blob.ciphertext_b64)
    plaintext = aes.decrypt(nonce, ct, MAGIC)
    return json.loads(plaintext.decode("utf-8"))