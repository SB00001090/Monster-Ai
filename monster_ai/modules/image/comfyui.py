"""ComfyUI image generation integration."""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx

from monster_ai.config import Settings
from monster_ai.core.generation_history import GenerationHistory
from monster_ai.core.generation_repair import GenerationRepair, validate_image_file
from monster_ai.core.image_repair import ImageRepairEngine
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.core.vram_guard import VramGuard
from monster_ai.modules.image.checkpoint_resolver import resolve_checkpoint
from monster_ai.modules.image.model_presets import (
    apply_style_to_negative,
    apply_style_to_prompt,
    get_preset,
    resolve_style_preset,
)
from monster_ai.modules.image.lora_manager import list_loras, resolve_lora
from monster_ai.modules.image.quality import ImageQualityScorer
from monster_ai.modules.image.quality_store import QualityStore
from monster_ai.modules.image.workflow_builder import build_txt2img_workflow, pick_workflow_template
from monster_ai.modules.prompt.anti_collapse import build_negative, suggest_cfg
from monster_ai.modules.prompt.enhancer import PromptEnhancer
from monster_ai.modules.prompt.refinement import PromptRefiner

logger = logging.getLogger(__name__)


class ComfyUIClient:
    def __init__(self, base_url: str, timeout: int = 300) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base}/system_stats")
                return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def require_online(self) -> None:
        if not await self.ping():
            raise RuntimeError(
                "ComfyUI is not running. Start ComfyUI first "
                "(ComfyUI headless on port 8188), then retry."
            )

    async def list_checkpoints(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.base}/object_info/CheckpointLoaderSimple")
                if r.status_code != 200:
                    return []
                data = r.json()
                ckpt = (
                    data.get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[]])
                )
                if ckpt and isinstance(ckpt[0], list):
                    return list(ckpt[0])
        except httpx.HTTPError:
            pass
        return []

    async def resolve_checkpoint_name(self, requested: str) -> tuple[str, str | None]:
        available = await self.list_checkpoints()
        return resolve_checkpoint(requested, available)

    def _parse_prompt_error(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:400]
        node_errors = data.get("node_errors", {})
        for node in node_errors.values():
            for err in node.get("errors", []):
                detail = err.get("details", err.get("message", ""))
                if "ckpt_name" in detail or "not in" in detail:
                    return (
                        "No checkpoint model in ComfyUI. "
                        "Put a .safetensors file in ComfyUI/models/checkpoints/ "
                        "or set modules.image.checkpoint: auto"
                    )
                return detail
        return data.get("error", {}).get("message", response.text[:400])

    async def queue_prompt(self, workflow: dict[str, Any]) -> str:
        await self.require_online()
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.base}/prompt", json=payload)
            if r.status_code >= 400:
                raise RuntimeError(self._parse_prompt_error(r))
            r.raise_for_status()
            body = r.json()
            if body.get("node_errors"):
                raise RuntimeError(self._parse_prompt_error(r))
            return body["prompt_id"]

    async def wait_for_images(
        self, prompt_id: str, poll_interval: float = 1.0, max_wait: int = 120
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            for _ in range(max_wait):
                r = await client.get(f"{self.base}/history/{prompt_id}")
                if r.status_code == 200:
                    data = r.json()
                    if prompt_id in data:
                        outputs = data[prompt_id].get("outputs", {})
                        images = []
                        for node_out in outputs.values():
                            images.extend(node_out.get("images", []))
                        if images:
                            return images
                await asyncio.sleep(poll_interval)
        raise TimeoutError(f"ComfyUI job timed out: {prompt_id}")

    async def download_image(self, image_info: dict[str, Any], dest: Path) -> Path:
        params = {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{self.base}/view", params=params)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return dest


class ImageService:
    name = "image"

    def __init__(
        self,
        settings: Settings,
        repair: SelfRepairEngine,
        gen_repair: GenerationRepair,
        vram_guard: VramGuard,
        prompt_enhancer: PromptEnhancer,
        quality_scorer: ImageQualityScorer | None = None,
        quality_store: QualityStore | None = None,
        image_repair: ImageRepairEngine | None = None,
        prompt_refiner: PromptRefiner | None = None,
        history: GenerationHistory | None = None,
        image_learner: Any | None = None,
    ) -> None:
        self.settings = settings
        self.repair = repair
        self.gen_repair = gen_repair
        self.vram_guard = vram_guard
        self.prompt_enhancer = prompt_enhancer
        self.quality_scorer = quality_scorer or ImageQualityScorer(settings.modules.image.quality)
        self.quality_store = quality_store or QualityStore(
            settings.modules.image.quality.data_dir, settings.modules.image.quality
        )
        self.image_repair = image_repair or ImageRepairEngine(settings.modules.image.quality)
        self.prompt_refiner = prompt_refiner or PromptRefiner(repair)
        self.image_learner = image_learner
        self.history = history
        self.url = settings.modules.image.comfyui_url.rstrip("/")
        self.client = ComfyUIClient(self.url)
        self.output_dir = Path(settings.modules.image.output_dir)
        self.active_checkpoint: str | None = None
        self.last_warning: str | None = None

    async def list_checkpoints(self) -> list[str]:
        return await self.client.list_checkpoints()

    async def list_loras(self) -> list[str]:
        return await list_loras(self.url)

    async def health(self) -> dict[str, Any]:
        if not self.settings.modules.image.enabled:
            return {"enabled": False, "healthy": False, "message": "Module disabled"}
        if not await self.client.ping():
            return {
                "enabled": True,
                "healthy": False,
                "message": "Start ComfyUI on port 8188",
                "url": self.url,
            }
        ckpts = await self.client.list_checkpoints()
        if not ckpts:
            return {
                "enabled": True,
                "healthy": False,
                "message": "ComfyUI OK but no checkpoint in models/checkpoints/",
                "checkpoints": [],
            }
        active, warning = await self.client.resolve_checkpoint_name(
            self.settings.modules.image.checkpoint
        )
        self.active_checkpoint = active
        self.last_warning = warning
        return {
            "enabled": True,
            "healthy": True,
            "message": "ComfyUI ready",
            "url": self.url,
            "checkpoint": active,
            "checkpoint_config": self.settings.modules.image.checkpoint,
            "workflow": pick_workflow_template(active),
            "warning": warning,
            "checkpoints": ckpts,
        }

    async def _render_once(
        self,
        *,
        positive: str,
        negative: str,
        checkpoint: str,
        width: int,
        height: int,
        steps: int,
        cfg: float,
        lora_name: str | None,
        lora_strength: float,
    ) -> Path:
        async with self.vram_guard.acquire("image"):
            workflow = build_txt2img_workflow(
                positive=positive,
                negative=negative,
                checkpoint=checkpoint,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                lora_name=lora_name,
                lora_strength=lora_strength,
            )
            prompt_id = await self.client.queue_prompt(workflow)
            images = await self.client.wait_for_images(prompt_id)
            out = self.output_dir / f"{uuid.uuid4().hex}.png"
            return await self.client.download_image(images[0], out)

    async def generate(
        self,
        prompt: str,
        *,
        negative: str | None = None,
        lora: str | None = None,
        lora_strength: float | None = None,
        width: int | None = None,
        height: int | None = None,
        style: str | None = None,
        checkpoint: str | None = None,
        enhance_prompt: bool = True,
        quality_filter: bool | None = None,
        max_quality_retries: int | None = None,
        record_history: bool = True,
        steps: int | None = None,
        cfg: float | None = None,
    ) -> dict[str, Any]:
        if not self.settings.modules.image.enabled:
            raise RuntimeError("Image module disabled")

        img_cfg = self.settings.modules.image
        q_cfg = img_cfg.quality
        use_quality = q_cfg.enabled if quality_filter is None else quality_filter
        max_q_retries = (
            max_quality_retries if max_quality_retries is not None else q_cfg.max_retries
        )

        loras = await self.list_loras()
        use_lora = resolve_lora(lora, loras)
        strength = lora_strength if lora_strength is not None else img_cfg.lora_strength
        available_ckpts = await self.client.list_checkpoints()

        style_preset = get_preset(style)
        warning: str | None = None
        if checkpoint:
            resolved_ckpt, ckpt_warn = await self.client.resolve_checkpoint_name(checkpoint)
            warning = ckpt_warn
        elif style and style != "auto":
            resolved_ckpt, style_preset, style_warn = resolve_style_preset(
                style, available_ckpts, config_default=img_cfg.checkpoint
            )
            warning = style_warn
        else:
            resolved_ckpt, ckpt_warn = await self.client.resolve_checkpoint_name(img_cfg.checkpoint)
            warning = ckpt_warn

        checkpoint = resolved_ckpt
        self.active_checkpoint = checkpoint
        self.last_warning = warning

        styled_prompt = apply_style_to_prompt(prompt, style_preset)
        if self.image_learner and self.image_learner.enabled:
            styled_prompt = self.image_learner.enhance_prompt(styled_prompt)
        positive = (
            await self.prompt_enhancer.for_image(styled_prompt)
            if enhance_prompt
            else styled_prompt
        )
        neg = negative or self.prompt_enhancer.default_negative()
        neg = apply_style_to_negative(neg, style_preset)
        w = width or style_preset.width or img_cfg.width
        h = height or style_preset.height or img_cfg.height
        steps = steps if steps is not None else img_cfg.steps
        cfg = cfg if cfg is not None else suggest_cfg(checkpoint, img_cfg.cfg)
        active_ckpt = checkpoint
        active_lora = use_lora
        retry_lora_strength = strength

        last_path: Path | None = None
        last_report = None
        quality_attempts = 0
        escalated = False
        gen_attempt_state = {"n": 0}

        async def _run_comfy() -> Path:
            nonlocal active_ckpt, positive, neg, steps, cfg, w, h, active_lora, escalated
            n = gen_attempt_state["n"]
            use_steps = steps if n == 0 else max(12, steps - 4)
            if n == 0:
                use_w, use_h = w, h
            else:
                use_w = max(512, int(w * 0.85))
                use_h = max(512, int(h * 0.85))
            use_lora_attempt = active_lora if n == 0 else active_lora
            use_strength = (
                retry_lora_strength
                if use_lora_attempt
                else strength
            )
            return await self._render_once(
                positive=positive,
                negative=neg,
                checkpoint=active_ckpt,
                width=use_w,
                height=use_h,
                steps=use_steps,
                cfg=cfg,
                lora_name=use_lora_attempt,
                lora_strength=use_strength,
            )

        async def _on_gen_retry(attempt: int, _exc: Exception) -> None:
            gen_attempt_state["n"] = attempt + 1

        for q_attempt in range(max_q_retries + 1):
            path = await self.gen_repair.run(
                "image",
                _run_comfy,
                validate=lambda p: validate_image_file(p),
                on_retry=_on_gen_retry,
            )
            last_path = path
            quality_attempts = q_attempt + 1
            gen_attempt_state["n"] = 0

            if not use_quality:
                break

            report = self.quality_scorer.evaluate(path, positive)
            last_report = report
            self.gen_repair.state.last_quality_score = report.score

            if report.passed:
                self.image_repair.record_quality_pass()
                self.gen_repair.state.quality_fail_streak = 0
                self.quality_store.save_good(
                    path,
                    prompt=positive,
                    negative=neg,
                    report=report,
                    checkpoint=active_ckpt,
                    attempt=q_attempt,
                    extra={"lora": active_lora},
                )
                if self.image_learner:
                    self.image_learner.ingest_generation(
                        label="good",
                        prompt=positive,
                        negative=neg,
                        report=report.to_dict(),
                        checkpoint=active_ckpt,
                        attempt=q_attempt,
                        extra={"lora": active_lora},
                    )
                break

            self.image_repair.record_quality_fail()
            self.gen_repair.state.quality_fail_streak += 1
            self.quality_store.save_bad(
                path,
                prompt=positive,
                negative=neg,
                report=report,
                checkpoint=active_ckpt,
                attempt=q_attempt,
                extra={"lora": active_lora},
            )
            if self.image_learner:
                self.image_learner.ingest_generation(
                    label="bad",
                    prompt=positive,
                    negative=neg,
                    report=report.to_dict(),
                    checkpoint=active_ckpt,
                    attempt=q_attempt,
                    extra={"lora": active_lora},
                )

            if q_cfg.auto_lora_on_retry and not active_lora:
                anti = resolve_lora(q_cfg.anti_collapse_lora, loras)
                if anti:
                    active_lora = anti
                    retry_lora_strength = q_cfg.lora_strength_on_retry

            if q_attempt >= max_q_retries:
                if self.image_repair.should_escalate():
                    plan = self.image_repair.plan_retry(
                        q_attempt + 1,
                        positive=positive,
                        negative=neg,
                        checkpoint=active_ckpt,
                        width=w,
                        height=h,
                        steps=steps,
                        cfg=cfg,
                        lora_name=active_lora,
                        report=report,
                        available_checkpoints=available_ckpts,
                        available_loras=loras,
                    )
                    active_ckpt = plan.checkpoint
                    positive = plan.positive
                    neg = plan.negative
                    steps = plan.steps
                    cfg = plan.cfg
                    w, h = plan.width, plan.height
                    active_lora = plan.lora_name
                    escalated = plan.insurance
                    gen_attempt_state["n"] = 0
                    try:
                        last_path = await self.gen_repair.run(
                            "image_insurance",
                            lambda: self._render_once(
                                positive=positive,
                                negative=neg,
                                checkpoint=active_ckpt,
                                width=w,
                                height=h,
                                steps=steps,
                                cfg=cfg,
                                lora_name=active_lora,
                                lora_strength=strength,
                            ),
                            validate=lambda p: validate_image_file(p),
                        )
                        quality_attempts += 1
                        if use_quality:
                            last_report = self.quality_scorer.evaluate(last_path, positive)
                    except Exception:  # noqa: BLE001
                        pass
                break

            refined = await self.prompt_refiner.refine(positive, neg, report, q_attempt)
            positive = refined.positive
            learned_neg = ""
            if self.image_learner:
                learned_neg = self.image_learner.negative_hints_for_issues(
                    [i.value for i in report.issues]
                )
            neg = refined.negative or build_negative(neg, report.issues)
            if learned_neg:
                neg = f"{neg}, {learned_neg}" if neg else learned_neg
            steps = max(12, min(40, steps + refined.steps_delta))
            cfg = max(4.0, min(12.0, cfg + refined.cfg_delta))

            plan = self.image_repair.plan_retry(
                q_attempt + 1,
                positive=positive,
                negative=neg,
                checkpoint=active_ckpt,
                width=w,
                height=h,
                steps=steps,
                cfg=cfg,
                lora_name=active_lora,
                report=report,
                available_checkpoints=available_ckpts,
                available_loras=loras,
            )
            active_ckpt = plan.checkpoint
            positive = plan.positive
            neg = plan.negative
            steps = plan.steps
            cfg = plan.cfg
            w, h = plan.width, plan.height
            active_lora = plan.lora_name
            if active_lora and q_cfg.auto_lora_on_retry:
                retry_lora_strength = q_cfg.lora_strength_on_retry
            if plan.insurance:
                escalated = True

        assert last_path is not None
        result: dict[str, Any] = {
            "path": str(last_path),
            "url": f"/api/generate/files/images/{last_path.name}",
            "prompt": positive,
            "negative": neg,
            "checkpoint": active_ckpt,
            "workflow": pick_workflow_template(active_ckpt),
            "style": style_preset.id if style_preset.id != "auto" else None,
        }
        if active_lora:
            result["lora"] = active_lora
        if warning:
            result["warning"] = warning
        if use_quality and last_report:
            result["quality"] = {
                **last_report.to_dict(),
                "attempts": quality_attempts,
                "escalated": escalated,
            }
            if not last_report.passed:
                if q_cfg.reject_bad_output and last_report.score < q_cfg.min_alive_score:
                    issues = [i.value for i in last_report.issues]
                    raise RuntimeError(
                        f"quality_rejected:{'|'.join(issues) or 'low_score'} — "
                        "建議降低解析度、換 checkpoint、或開啟 quality_filter 重試"
                    )
                result["warning"] = (
                    (result.get("warning") or "")
                    + " quality_filter_exhausted — best attempt returned"
                ).strip()
        if self.history and record_history:
            self.history.record("image", result)
        return result