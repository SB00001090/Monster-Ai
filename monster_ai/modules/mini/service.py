"""Mini Monster AI — R18+ multimodal pipeline with likeness + voice clone."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from monster_ai.config import MiniModuleSettings
from monster_ai.core.generation_repair import validate_image_file
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.image.comfyui import ImageService
from monster_ai.modules.learning.engine import LearningEngine
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.mini.checkpoints import pick_checkpoint, pick_lora
from monster_ai.modules.mini.constants import DEVELOPER, PRODUCT_NAME, VERSION
from monster_ai.modules.mini.disclaimer import get_disclaimer
from monster_ai.modules.mini.likeness import (
    LIKENESS_TEMPLATE_ID,
    ReferenceStore,
    build_ipadapter_workflow,
    build_likeness_negative,
    build_likeness_prompt,
    comfy_has_node,
    stage_reference_for_comfy,
)
from monster_ai.modules.mini.multilingual import analyze_prompt, merge_mixed_prompt
from monster_ai.modules.mini.network_learning import MiniNetworkLearner
from monster_ai.modules.mini.prompts import apply_template, build_negative, get_template, list_templates_api
from monster_ai.modules.mini.quality_guard import (
    EMERGENCY_TEMPLATE_ID,
    effective_template,
    quality_issues,
    quality_passed,
)
from monster_ai.modules.mini.success_tracker import SuccessTracker
from monster_ai.modules.tts.engine import TTSService

logger = logging.getLogger(__name__)


class MiniMonsterService:
    name = "mini"

    def __init__(
        self,
        settings: MiniModuleSettings,
        image: ImageService,
        repair: SelfRepairEngine,
        learning: LearningEngine | None = None,
        tts: TTSService | None = None,
        *,
        network_guard: Any = None,
    ) -> None:
        self.settings = settings
        self.image = image
        self.repair = repair
        self.tts = tts
        self.learning = learning
        store = (
            learning.store
            if learning and settings.share_with_monster_ai
            else LearningStore(settings.data_dir)
        )
        self.tracker = SuccessTracker(settings.data_dir)
        self.refs = ReferenceStore(settings.data_dir)
        self.network = MiniNetworkLearner(
            store,
            enabled=settings.network_learning_enabled,
            consent_file=str(Path(settings.data_dir) / "network_consent.json"),
            allow_downloads=settings.network_allow_downloads,
            allow_metrics_upload=settings.network_allow_metrics_upload,
            metrics_endpoint=settings.network_metrics_endpoint,
            network_guard=network_guard,
        )
        Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self.settings.enabled

    async def health(self) -> dict[str, Any]:
        comfy_ok = await self.image.client.ping()
        ip_ok = False
        if comfy_ok:
            ip_ok = await comfy_has_node(
                self.image.client.base, "IPAdapterUnifiedLoader"
            )
        return {
            "enabled": self.enabled,
            "comfyui": comfy_ok,
            "ipadapter_nodes": ip_ok,
            "success_rate": self.tracker.status().get("success_rate"),
            "likeness_similarity": self.tracker.status().get("avg_likeness_similarity"),
            "network": self.network.consent_status(),
        }

    def info(self) -> dict[str, Any]:
        return {
            "product": PRODUCT_NAME,
            "version": VERSION,
            "developer": DEVELOPER,
            "enabled": self.settings.enabled,
            "lite_mode": self.settings.lite_mode,
            "uncensored": self.settings.uncensored,
            "likeness_enabled": self.settings.likeness_enabled,
            "voice_clone_enabled": self.settings.voice_clone_enabled,
            "multimodal_sync_enabled": self.settings.multimodal_sync_enabled,
            "default_template": self.settings.default_template,
            "templates": list_templates_api(),
            "references": self.refs.list_profiles(),
            "success": self.tracker.status(),
            "network": self.network.consent_status(),
            "shared_learning": self.settings.share_with_monster_ai,
        }

    def disclaimer(self, locale: str | None = None) -> dict[str, str]:
        return get_disclaimer(locale or self.settings.default_locale)

    async def optimize_prompt(self, prompt: str, *, locale: str | None = None) -> dict[str, Any]:
        analysis = analyze_prompt(prompt, preferred=locale or self.settings.default_locale)
        optimized = prompt
        if self.settings.auto_optimize_prompt:
            try:
                raw = await self.repair.generate(prompt, system=analysis.optimize_system)
                optimized = merge_mixed_prompt(prompt, raw.strip())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Mini prompt optimize failed: %s", exc)
        return {
            "original": prompt,
            "optimized": optimized,
            "locale": analysis.primary,
            "mixed": analysis.mixed,
            "detected": analysis.detected,
        }

    def register_reference(
        self,
        *,
        name: str,
        image_bytes: bytes,
        image_ext: str = ".png",
        voice_bytes: bytes | None = None,
        likeness_lora: str | None = None,
    ) -> dict[str, Any]:
        if self.settings.require_user_reference and not image_bytes:
            raise ValueError("reference_image_required")
        profile = self.refs.register(
            name=name,
            image_bytes=image_bytes,
            image_ext=image_ext,
            voice_bytes=voice_bytes,
            likeness_lora=likeness_lora,
        )
        if voice_bytes and self.tts and self.tts.xtts:
            voice_dest = Path("./data/voices") / f"mini_{profile.id}.wav"
            voice_dest.parent.mkdir(parents=True, exist_ok=True)
            voice_dest.write_bytes(voice_bytes)
        return {"ok": True, "reference_id": profile.id, "name": profile.name}

    async def _render_likeness_ipadapter(
        self,
        *,
        profile_id: str,
        prompt: str,
        template_id: str,
        locale: str | None,
    ) -> dict[str, Any]:
        profile = self.refs.get(profile_id)
        if not profile:
            raise ValueError(f"reference_not_found:{profile_id}")

        template = effective_template(
            get_template(template_id or LIKENESS_TEMPLATE_ID),
            self.settings,
        )
        opt = await self.optimize_prompt(prompt, locale=locale)
        positive = build_likeness_prompt(apply_template(opt["optimized"], template), profile)
        negative = build_likeness_negative(build_negative(template))

        available = await self.image.client.list_checkpoints()
        ckpt, ckpt_warn = pick_checkpoint(self.settings.checkpoint, available)
        loras = await self.image.list_loras()
        use_lora = pick_lora(profile.likeness_lora or self.settings.default_lora, loras)

        comfy_input = Path(self.settings.comfy_input_dir)
        ref_file = stage_reference_for_comfy(profile, comfy_input)

        has_ip = await comfy_has_node(self.image.client.base, "IPAdapterUnifiedLoader")
        if not has_ip:
            result = await self.generate_r18(
                prompt,
                template_id=LIKENESS_TEMPLATE_ID,
                locale=locale,
                lora=use_lora,
                checkpoint=ckpt,
                enhance_prompt=False,
            )
            result["likeness_mode"] = "prompt_fallback"
            result["reference_id"] = profile_id
            result["warning"] = (
                (result.get("warning") or "")
                + " Install ComfyUI-IPAdapter-plus for FaceID workflow."
            ).strip()
            return result

        workflow = build_ipadapter_workflow(
            positive=positive,
            negative=negative,
            checkpoint=ckpt,
            reference_filename=ref_file,
            width=template.width,
            height=template.height,
            steps=template.steps,
            cfg=template.cfg,
            ip_weight=self.settings.likeness_ipadapter_weight,
            lora_name=use_lora,
            lora_strength=self.settings.lora_strength,
        )

        async def _run() -> Path:
            async with self.image.vram_guard.acquire("mini_likeness"):
                pid = await self.image.client.queue_prompt(workflow)
                images = await self.image.client.wait_for_images(pid, max_wait=180)
                out = Path(self.settings.output_dir) / f"{uuid.uuid4().hex}.png"
                return await self.image.client.download_image(images[0], out)

        path = await self.image.gen_repair.run(
            "mini_likeness",
            _run,
            validate=lambda p: validate_image_file(p),
        )
        quality = self.image.quality_scorer.evaluate(path, positive).to_dict()
        return {
            "ok": True,
            "path": str(path),
            "url": f"/api/generate/files/mini/{path.name}",
            "likeness_mode": "ipadapter_faceid",
            "reference_id": profile_id,
            "template_id": template.id,
            "checkpoint": ckpt,
            "lora": use_lora,
            "quality": quality,
            "warning": ckpt_warn,
        }

    async def generate_likeness(
        self,
        prompt: str,
        *,
        reference_id: str,
        template_id: str | None = None,
        locale: str | None = None,
    ) -> dict[str, Any]:
        if not self.settings.likeness_enabled:
            raise RuntimeError("Likeness module disabled")
        result = await self._render_likeness_ipadapter(
            profile_id=reference_id,
            prompt=prompt,
            template_id=template_id or LIKENESS_TEMPLATE_ID,
            locale=locale,
        )

        passed = quality_passed(result, min_score=self.settings.min_quality_score)
        if (
            not passed
            and self.settings.auto_emergency_retry
            and result.get("likeness_mode") == "ipadapter_faceid"
        ):
            fallback = await self.generate_r18(
                prompt,
                template_id=EMERGENCY_TEMPLATE_ID,
                locale=locale,
                enhance_prompt=False,
            )
            if quality_passed(fallback, min_score=self.settings.min_quality_score):
                fallback["likeness_mode"] = "emergency_fallback"
                fallback["reference_id"] = reference_id
                result = fallback
                passed = True

        if not passed and self.settings.reject_bad_output:
            issues = quality_issues(result)
            raise RuntimeError(
                f"quality_rejected:{'|'.join(issues) or 'low_score'} — "
                "建議改用 stable 模板、安裝 Juggernaut/RealVisXL checkpoint、或降低解析度"
            )

        report = result.get("quality") or {}
        self.tracker.record(
            ok=passed,
            template_id=result.get("template_id", LIKENESS_TEMPLATE_ID),
            quality_score=report.get("score"),
            issues=[str(i) for i in (report.get("issues") or [])],
            locale=locale or self.settings.default_locale,
            mode="likeness",
        )
        return result

    async def _generate_r18_once(
        self,
        *,
        positive: str,
        negative: str,
        template,
        resolved_ckpt: str,
        use_lora: str | None,
        use_enhance: bool,
        max_retries: int,
    ) -> dict[str, Any]:
        return await self.image.generate(
            positive,
            negative=negative,
            lora=use_lora,
            lora_strength=self.settings.lora_strength,
            width=template.width,
            height=template.height,
            style="realistic",
            checkpoint=resolved_ckpt,
            enhance_prompt=use_enhance,
            quality_filter=True,
            max_quality_retries=max_retries,
            steps=template.steps,
            cfg=template.cfg,
        )

    async def generate_r18(
        self,
        prompt: str,
        *,
        template_id: str | None = None,
        locale: str | None = None,
        lora: str | None = None,
        checkpoint: str | None = None,
        enhance_prompt: bool | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Mini Monster AI module disabled")

        template = effective_template(
            get_template(template_id or self.settings.default_template),
            self.settings,
        )
        opt = await self.optimize_prompt(prompt, locale=locale)
        positive = apply_template(opt["optimized"], template)
        negative = build_negative(template)

        ckpt_req = checkpoint or self.settings.checkpoint
        available = await self.image.client.list_checkpoints()
        resolved_ckpt, ckpt_warn = pick_checkpoint(ckpt_req, available)
        loras = await self.image.list_loras()
        use_lora = pick_lora(lora or self.settings.default_lora or "detail", loras)

        use_enhance = (
            self.settings.auto_optimize_prompt
            if enhance_prompt is None
            else enhance_prompt
        )

        result = await self._generate_r18_once(
            positive=positive,
            negative=negative,
            template=template,
            resolved_ckpt=resolved_ckpt,
            use_lora=use_lora,
            use_enhance=use_enhance,
            max_retries=self.settings.max_quality_retries,
        )

        passed = quality_passed(result, min_score=self.settings.min_quality_score)

        if (
            not passed
            and self.settings.auto_emergency_retry
            and template.id != EMERGENCY_TEMPLATE_ID
        ):
            emergency = effective_template(get_template(EMERGENCY_TEMPLATE_ID), self.settings)
            em_pos = apply_template(opt["optimized"], emergency)
            em_neg = build_negative(emergency)
            em_lora = pick_lora("detail", loras) or use_lora
            result = await self._generate_r18_once(
                positive=em_pos,
                negative=em_neg,
                template=emergency,
                resolved_ckpt=resolved_ckpt,
                use_lora=em_lora,
                use_enhance=False,
                max_retries=self.settings.max_quality_retries + 2,
            )
            passed = quality_passed(result, min_score=self.settings.min_quality_score)
            template = emergency
            if passed:
                result["emergency_retry"] = True

        if not passed and self.settings.reject_bad_output:
            issues = quality_issues(result)
            raise RuntimeError(
                f"quality_rejected:{'|'.join(issues) or 'low_score'} — "
                "建議改用 stable 模板、安裝 Juggernaut/RealVisXL checkpoint、或降低解析度"
            )

        report = result.get("quality") or {}
        issues = list(report.get("issues") or [])
        self.tracker.record(
            ok=passed,
            template_id=template.id,
            quality_score=report.get("score"),
            issues=[str(i) for i in issues],
            repair_attempts=int(result.get("quality_attempts") or 1) - 1,
            locale=opt["locale"],
            mode="image",
        )

        if self.settings.share_with_monster_ai and self.learning:
            self.learning._log_evolution(  # noqa: SLF001
                event="mini_r18_generate",
                template=template.id,
                ok=passed,
                locale=opt["locale"],
            )

        if self.settings.network_learning_enabled:
            await self.network.upload_anonymous_metrics(self.tracker.status())

        out = {
            **result,
            "mini": True,
            "template_id": template.id,
            "locale": opt["locale"],
            "checkpoint": resolved_ckpt,
            "lora": use_lora,
            "warning": ckpt_warn or result.get("warning"),
            "success_rate": self.tracker.status().get("success_rate"),
        }
        p = out.get("path")
        if p and str(Path(p).parent).startswith(str(Path(self.settings.output_dir))):
            out["url"] = f"/api/generate/files/mini/{Path(p).name}"
        return out

    async def clone_voice(
        self,
        text: str,
        *,
        reference_id: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        if not self.settings.voice_clone_enabled:
            raise RuntimeError("Voice clone disabled")
        profile = self.refs.get(reference_id)
        ref_key = f"mini_{reference_id}"
        if not self.tts or not self.tts.xtts:
            if profile and profile.voice_path and profile.voice_path.is_file():
                raise RuntimeError(
                    "XTTS not enabled. Set modules.tts.xtts_enabled: true and pip install TTS"
                )
            raise RuntimeError("XTTS voice clone not available")

        if profile and profile.voice_path and profile.voice_path.is_file():
            dest = Path("./data/voices") / f"{ref_key}.wav"
            if not dest.is_file():
                dest.write_bytes(profile.voice_path.read_bytes())

        result = await self.tts.clone(text, ref_key)
        self.tracker.record(
            ok=True,
            template_id="voice_clone",
            locale=locale or self.settings.default_locale,
            mode="voice",
        )
        return {**result, "reference_id": reference_id, "locale": locale}

    async def generate_multimodal(
        self,
        prompt: str,
        *,
        reference_id: str,
        voice_text: str | None = None,
        template_id: str | None = None,
        locale: str | None = None,
    ) -> dict[str, Any]:
        if not self.settings.multimodal_sync_enabled:
            raise RuntimeError("Multimodal sync disabled")

        image_result = await self.generate_likeness(
            prompt,
            reference_id=reference_id,
            template_id=template_id or LIKENESS_TEMPLATE_ID,
            locale=locale,
        )
        speech = voice_text or prompt[:200]
        voice_result: dict[str, Any] | None = None
        try:
            voice_result = await self.clone_voice(
                speech,
                reference_id=reference_id,
                locale=locale,
            )
        except Exception as exc:  # noqa: BLE001
            voice_result = {"ok": False, "error": str(exc)}

        return {
            "ok": image_result.get("ok", True),
            "image": image_result,
            "voice": voice_result,
            "multimodal": True,
            "reference_id": reference_id,
        }

    async def record_feedback(
        self,
        *,
        ok: bool,
        template_id: str = "hq",
        similarity_score: float | None = None,
    ) -> dict[str, Any]:
        self.tracker.record(
            ok=ok,
            template_id=template_id,
            similarity_score=similarity_score,
            mode="likeness" if similarity_score is not None else "image",
        )
        if similarity_score is not None and self.settings.network_learning_enabled:
            await self.network.upload_likeness_feedback(
                similarity_score=similarity_score,
                template_id=template_id,
                ok=ok,
            )
        if self.learning and self.settings.share_with_monster_ai:
            self.learning.record_feedback(
                user_id="mini",
                session_id="mini-r18",
                thumbs="up" if ok else "down",
                comment=f"mini template={template_id} sim={similarity_score}",
            )
        return {"ok": True, "success": self.tracker.status()}

    async def network_consent(self, *, grant: bool, downloads: bool = False, metrics: bool = False) -> dict:
        if grant:
            return self.network.grant_consent(downloads=downloads, metrics=metrics)
        return self.network.revoke_consent()

    async def network_catalog(self, query: str) -> dict[str, Any]:
        return await self.network.fetch_model_catalog_hint(query)