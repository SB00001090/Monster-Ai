"""Guardian Ai — unified privacy, sync, OC protection, and toddler learning service."""
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
from monster_ai.modules.guardian.account_store import AccountStore
from monster_ai.modules.guardian.backstory import BackstoryGenerator
from monster_ai.modules.guardian.art_triage import ArtTriageEngine
from monster_ai.modules.guardian.diary_store import DiaryStore
from monster_ai.modules.guardian.discord_reporter import send_discord_error_report
from monster_ai.modules.guardian.manuscript_store import ManuscriptStore
from monster_ai.modules.guardian.network_learning import GuardianNetworkLearner
from monster_ai.modules.guardian.share_store import ShareStore
from monster_ai.modules.guardian.toddler_learning import ToddlerLearningEngine
from monster_ai.modules.guardian.training_vault import TrainingVault

if TYPE_CHECKING:
    from monster_ai.core.self_repair import SelfRepairEngine
    from monster_ai.modules.learning.engine import LearningEngine
    from monster_ai.modules.learning.image_knowledge import ImageKnowledgeLearner
    from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner


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
        self.manuscripts = ManuscriptStore(root)
        self.diaries = DiaryStore(root)
        self.shares = ShareStore(root)
        self.accounts = AccountStore(root)
        self.errors = ErrorLearningStore(root)
        self.supervisor = GrokSupervisor(root, repair)
        self.toddler = ToddlerLearningEngine(root, self.supervisor)
        self.backstory = BackstoryGenerator(self.oc_store)
        self.key_manager = TrainingKeyManager(
            settings,
            repo_root or Path("."),
            hardware_fingerprint=hardware_fingerprint,
        )
        self.training_vault: TrainingVault | None = None
        self.network_learning: GuardianNetworkLearner | None = None
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
            "manuscript_versions": True,
            "diary_encryption": True,
            "character_share": True,
            "discord_binding": "discord" in self.settings.oauth_providers,
            "connection_policy": "tunnel_or_usb_only",
            "no_tailscale": True,
            "no_qr_code": True,
            "connection_mode": "cloudflare_tunnel",
            "toddler_learning": self.toddler.status(),
            "training_encryption": self.settings.training_encryption_enabled,
            "training_vault": self.training_vault.status() if self.training_vault else None,
            "network_learning": (
                self.network_learning.status()
                if self.network_learning
                else {"enabled": self.settings.network_learning.enabled}
            ),
        }

    def attach_network_learning(
        self,
        web_learner: WebKnowledgeLearner,
        image_learner: ImageKnowledgeLearner | None = None,
    ) -> None:
        art_triage = ArtTriageEngine(
            Path(self.settings.data_dir),
            training_vault=self.training_vault,
            image_learner=image_learner,
            min_quality_score=self.settings.min_quality_score,
        )
        self.network_learning = GuardianNetworkLearner(
            self.settings.network_learning,
            data_dir=Path(self.settings.data_dir),
            web_learner=web_learner,
            supervisor=self.supervisor,
            training_vault=self.training_vault,
            art_triage=art_triage,
        )

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
        toddler = self.toddler.record_quality_result(passed=passed, score=score)
        return {
            "score": score,
            "threshold": self.settings.min_quality_score,
            "passed": passed,
            "status": "pass" if passed else "fail",
            "action": None if passed else "retry_generation",
            "toddler": toddler.get("status"),
        }

    def toddler_status(self) -> dict[str, Any]:
        return self.toddler.status()

    async def toddler_progress(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        if self.learning:
            snapshot = self.learning.evolution_snapshot()
        return await self.toddler.progress_with_grok(snapshot)

    def toddler_positive_feedback(self, *, reason: str = "user_praise") -> dict[str, Any]:
        return self.toddler.record_positive_feedback(reason=reason)

    async def generate_backstory(
        self,
        *,
        card: dict[str, Any],
        owner_id: str = "local",
        theme: str = "",
        ephemeral: bool = False,
        multimodal: bool = True,
    ) -> dict[str, Any]:
        result = await self.backstory.generate(
            card=card,
            owner_id=owner_id,
            theme=theme,
            ephemeral=ephemeral or self.settings.ephemeral_chat_default,
            check_plagiarism=self.settings.oc_fingerprint_enabled,
            repair=self.repair,
            multimodal=multimodal,
        )
        if result.get("ok") and not result.get("ephemeral"):
            oc_id = str(card.get("id") or card.get("name") or "oc")
            version = self.manuscripts.save_version(
                oc_id,
                content={
                    "card": result.get("protected_card") or card,
                    "sections": result.get("sections"),
                    "narrative": result.get("narrative"),
                },
                author=owner_id,
                label="backstory_generate",
            )
            result["manuscript_version"] = version.get("version")
        return result

    def protect_oc(self, card: dict[str, Any], *, owner_id: str = "local") -> dict[str, Any]:
        if not self.settings.oc_fingerprint_enabled:
            return {"ok": True, "protected": False, "card": card}
        record = generate_fingerprint(card, owner_id=owner_id)
        char_id = str(card.get("id") or card.get("name") or "oc")
        self.oc_store.save(char_id, record)
        protected = embed_watermark(card, record) if self.settings.oc_watermark_enabled else card
        version = self.manuscripts.save_version(
            char_id,
            content={"card": protected, "fingerprint": record},
            author=owner_id,
            label="oc_protect",
        )
        return {
            "ok": True,
            "protected": True,
            "fingerprint": record,
            "card": protected,
            "manuscript_version": version.get("version"),
        }

    async def report_error(
        self,
        *,
        error_type: str,
        message: str,
        stack: str | None = None,
        context: str | None = None,
        source: str = "api",
        account_id: str | None = None,
        discord_notify: bool = False,
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
        discord_result: dict[str, Any] | None = None
        if discord_notify and account_id:
            webhook = self.accounts.get_discord_webhook(account_id)
            if webhook:
                discord_result = await send_discord_error_report(
                    webhook_url=webhook,
                    error_type=error_type,
                    message=message,
                    stack=stack,
                    context=context,
                    source=source,
                    account_id=account_id,
                )
        out: dict[str, Any] = {"ok": True, **record}
        if discord_result:
            out["discord"] = discord_result
        return out

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

    def manuscript_list(self, oc_id: str) -> dict[str, Any]:
        return {"ok": True, "oc_id": oc_id, "versions": self.manuscripts.list_versions(oc_id)}

    def manuscript_restore(self, oc_id: str, version: int) -> dict[str, Any]:
        return self.manuscripts.restore_version(oc_id, version)

    def manuscript_diff(self, oc_id: str, v1: int, v2: int) -> dict[str, Any]:
        return self.manuscripts.diff_versions(oc_id, v1, v2)

    def diary_append(
        self,
        character_id: str,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
        vault_key: str,
        mood: str | None = None,
    ) -> dict[str, Any]:
        return self.diaries.append_messages(
            character_id,
            session_id=session_id,
            messages=messages,
            vault_passphrase=vault_key,
            mood=mood,
        )

    def diary_get(self, character_id: str, date: str, *, vault_key: str) -> dict[str, Any]:
        return self.diaries.get_day(character_id, date, vault_passphrase=vault_key)

    def diary_summary(
        self,
        character_id: str,
        *,
        vault_key: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        return self.diaries.generate_summary(character_id, date=date, vault_passphrase=vault_key)

    def diary_dates(self, character_id: str) -> dict[str, Any]:
        return {"ok": True, "character_id": character_id, "dates": self.diaries.list_dates(character_id)}

    def share_create(
        self,
        *,
        oc_id: str,
        card: dict[str, Any],
        owner_id: str,
        mode: str,
        ttl_hours: int,
        passphrase: str,
    ) -> dict[str, Any]:
        return self.shares.create_share(
            oc_id=oc_id,
            card=card,
            owner_id=owner_id,
            mode=mode,
            ttl_hours=ttl_hours,
            passphrase=passphrase,
        )

    def share_import(self, *, token: str, passphrase: str) -> dict[str, Any]:
        return self.shares.import_share(token=token, passphrase=passphrase)

    def share_list(self, owner_id: str) -> dict[str, Any]:
        return {"ok": True, "shares": self.shares.list_by_owner(owner_id)}

    def account_register(self, *, username: str, display_name: str | None = None) -> dict[str, Any]:
        return self.accounts.register_local(username=username, display_name=display_name)

    def account_link_oauth(
        self,
        *,
        account_id: str,
        provider: str,
        provider_sub: str,
        display_name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        return self.accounts.link_oauth(
            account_id=account_id,
            provider=provider,
            provider_sub=provider_sub,
            display_name=display_name,
            email=email,
        )

    def account_bind_discord_webhook(self, account_id: str, *, webhook_url: str) -> dict[str, Any]:
        return self.accounts.bind_discord_webhook(account_id, webhook_url=webhook_url)

    def account_status(self, account_id: str) -> dict[str, Any]:
        return self.accounts.status(account_id)