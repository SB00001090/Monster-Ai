"""Monster Guardian AI — unified privacy, sync, OC protection, and learning service."""
from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from monster_ai.config import GuardianSettings
from monster_ai.modules.guardian.chat_vault import ChatVault
from monster_ai.modules.guardian.cloud_sync import CloudSyncStore
from monster_ai.modules.guardian.crypto import derive_user_key, encrypt_payload
from monster_ai.modules.guardian.disclaimer import DEVELOPER, get_disclaimer
from monster_ai.modules.guardian.error_learning import ErrorLearningStore
from monster_ai.modules.guardian.grok_supervisor import GrokSupervisor
from monster_ai.modules.guardian.key_manager import TrainingKeyManager
from monster_ai.modules.guardian.oc_fingerprint import OCFingerprintStore, embed_watermark, generate_fingerprint
from monster_ai.modules.guardian.training_vault import TrainingVault

if TYPE_CHECKING:
    from monster_ai.core.self_repair import SelfRepairEngine
    from monster_ai.modules.learning.engine import LearningEngine


class GuardianService:
    name = "guardian"

    def __init__(
        self,
        settings: GuardianSettings,
        repair: SelfRepairEngine | None = None,
        learning: LearningEngine | None = None,
        *,
        repo_root: Path | None = None,
        hardware_fingerprint: str = "",
    ) -> None:
        self.settings = settings
        self.repair = repair
        self.learning = learning
        root = Path(settings.data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.cloud = CloudSyncStore(root)
        self.vault = ChatVault(root)
        self.oc_store = OCFingerprintStore(root)
        self.errors = ErrorLearningStore(root)
        self.supervisor = GrokSupervisor(root, repair)
        self.key_manager = TrainingKeyManager(
            settings,
            repo_root or Path("."),
            hardware_fingerprint=hardware_fingerprint,
        )
        self.training_vault: TrainingVault | None = None
        if settings.training_encryption_enabled:
            self.training_vault = TrainingVault(root, self.key_manager)
            if settings.bind_hardware_key and not settings.require_user_passphrase:
                try:
                    self.key_manager.unlock(None)
                except ValueError:
                    pass

    async def health(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "healthy": True,
            "developer": DEVELOPER,
            "cloud_sync": self.settings.cloud_sync_enabled,
            "e2e_required": self.settings.e2e_encryption_required,
            "ephemeral_default": self.settings.ephemeral_chat_default,
            "oc_fingerprint": self.settings.oc_fingerprint_enabled,
            "grok_supervision": self.settings.grok_supervision_enabled,
            "min_quality_score": self.settings.min_quality_score,
            "oauth_providers": self.settings.oauth_providers,
            "no_tailscale": True,
            "no_qr_code": True,
            "connection_mode": "cloudflare_tunnel",
            "training_encryption": self.settings.training_encryption_enabled,
            "training_vault": self.training_vault.status() if self.training_vault else None,
        }

    def unlock_training_vault(self, passphrase: str | None = None) -> dict[str, Any]:
        return self.key_manager.unlock(passphrase)

    def lock_training_vault(self) -> dict[str, Any]:
        self.key_manager.lock()
        return {"ok": True, "locked": True}

    def migrate_training_assets(self, quality_data_dir: Path) -> dict[str, Any]:
        if self.training_vault is None:
            return {"ok": False, "reason": "training_vault_disabled"}
        base = Path(quality_data_dir)
        results = []
        for label in ("good", "bad"):
            r = self.training_vault.migrate_plaintext_dir(
                base / label,
                label=label,
                delete_plaintext=self.settings.delete_plaintext_after_encrypt,
            )
            results.append(r)
        return {"ok": True, "migrated": results}

    def export_training_for_sync(self) -> dict[str, Any]:
        if self.training_vault is None:
            return {"ok": False, "reason": "training_vault_disabled"}
        return {"ok": True, "bundle": self.training_vault.export_encrypted_bundle()}

    def import_training_from_sync(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if self.training_vault is None:
            return {"ok": False, "reason": "training_vault_disabled"}
        return self.training_vault.import_encrypted_bundle(bundle)

    def disclaimer(self, locale: str = "zh-TW") -> dict[str, str]:
        return get_disclaimer(locale)

    def quality_gate(self, score: float) -> dict[str, Any]:
        passed = score >= self.settings.min_quality_score
        return {
            "score": score,
            "threshold": self.settings.min_quality_score,
            "passed": passed,
            "status": "pass" if passed else "fail",
            "action": None if passed else "retry_generation",
        }

    def protect_oc(self, card: dict[str, Any], *, owner_id: str = "local") -> dict[str, Any]:
        if not self.settings.oc_fingerprint_enabled:
            return {"ok": True, "protected": False, "card": card}
        record = generate_fingerprint(card, owner_id=owner_id)
        char_id = str(card.get("id") or card.get("name") or "oc")
        self.oc_store.save(char_id, record)
        protected = embed_watermark(card, record) if self.settings.oc_watermark_enabled else card
        return {"ok": True, "protected": True, "fingerprint": record, "card": protected}

    async def report_error(
        self,
        *,
        error_type: str,
        message: str,
        stack: str | None = None,
        context: str | None = None,
        source: str = "api",
    ) -> dict[str, Any]:
        record = self.errors.ingest(
            error_type=error_type,
            message=message,
            stack=stack,
            context=context,
            source=source,
        )
        if self.learning and self.settings.grok_supervision_enabled:
            await self._feed_learning(record)
        return {"ok": True, **record}

    async def _feed_learning(self, record: dict[str, Any]) -> None:
        if self.learning is None:
            return
        self.learning._log_evolution(  # noqa: SLF001 — intentional learning hook
            event="guardian_error",
            error_type=record.get("error_type"),
            message=(record.get("message") or "")[:200],
            fix_suggestion=record.get("fix_suggestion"),
        )

    async def supervise_learning(self) -> dict[str, Any]:
        error_summary = self.errors.summarize()
        learning_snapshot: dict[str, Any] = {}
        feedback_count = 0
        if self.learning:
            learning_snapshot = self.learning.evolution_snapshot()
            learning_snapshot["failure_analysis"] = self.learning.failure_analyzer.summarize()
            feedback_count = learning_snapshot.get("feedback_events", 0)
        return await self.supervisor.review(
            error_summary=error_summary,
            learning_snapshot=learning_snapshot,
            feedback_count=feedback_count,
        )

    def sync_upload(
        self,
        *,
        provider: str,
        provider_sub: str,
        passphrase: str,
        bundle_type: str,
        payload: dict[str, Any] | list[Any],
        device_id: str = "unknown",
    ) -> dict[str, Any]:
        if not self.settings.cloud_sync_enabled:
            return {"ok": False, "reason": "cloud_sync_disabled"}
        if self.settings.e2e_encryption_required and not passphrase:
            return {"ok": False, "reason": "passphrase_required"}
        return self.cloud.upload_bundle(
            provider=provider,
            provider_sub=provider_sub,
            passphrase=passphrase,
            bundle_type=bundle_type,
            payload=payload,
            device_id=device_id,
        )

    def sync_download(
        self,
        *,
        provider: str,
        provider_sub: str,
        passphrase: str,
        bundle_type: str,
    ) -> dict[str, Any]:
        if not self.settings.cloud_sync_enabled:
            return {"ok": False, "reason": "cloud_sync_disabled"}
        return self.cloud.download_bundle(
            provider=provider,
            provider_sub=provider_sub,
            passphrase=passphrase,
            bundle_type=bundle_type,
        )

    def sync_list(self, provider: str, provider_sub: str) -> dict[str, Any]:
        return self.cloud.list_bundles(provider, provider_sub)

    def vault_store(
        self,
        session_id: str,
        message: dict[str, Any],
        *,
        vault_key: str,
        ephemeral: bool | None = None,
    ) -> dict[str, Any]:
        import base64
        import secrets

        from monster_ai.modules.guardian.crypto import SALT_SIZE

        salt = secrets.token_bytes(SALT_SIZE)
        key = derive_user_key(vault_key, salt)
        use_ephemeral = self.settings.ephemeral_chat_default if ephemeral is None else ephemeral
        result = self.vault.store_message(session_id, message, key=key, ephemeral=use_ephemeral)
        return {**result, "encrypted": not use_ephemeral}