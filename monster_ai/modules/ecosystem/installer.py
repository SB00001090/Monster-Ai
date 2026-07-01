"""One-click network ecosystem installer for Monster AI + Mini Monster AI."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from monster_ai.config import EcosystemSettings
from monster_ai.modules.ecosystem.manifest import bundle_steps, list_bundles, load_manifest
from monster_ai.modules.learning.store import LearningStore

ROOT = Path(__file__).resolve().parents[3]
DEVELOPER = "Suckbob"


@dataclass
class InstallState:
    running: bool = False
    bundle_id: str = ""
    current_step: str = ""
    completed_steps: int = 0
    total_steps: int = 0
    errors: list[str] = field(default_factory=list)
    log: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        pct = 100.0 * self.completed_steps / max(self.total_steps, 1)
        return {
            "running": self.running,
            "bundle_id": self.bundle_id,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "progress_pct": round(pct, 1),
            "errors": self.errors,
            "log": self.log[-30:],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "developer": DEVELOPER,
        }


class EcosystemInstaller:
    def __init__(
        self,
        settings: EcosystemSettings,
        *,
        root: Path | None = None,
        network_guard: Callable[[], tuple[bool, str]] | None = None,
    ) -> None:
        self.settings = settings
        self.root = root or ROOT
        self.store = LearningStore(settings.data_dir)
        self.consent_path = Path(settings.data_dir) / "consent.json"
        self.state_path = Path(settings.data_dir) / "install_state.json"
        self._guard = network_guard
        self._state = InstallState()
        self._task: asyncio.Task | None = None
        self._manifest = load_manifest()
        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self) -> None:
        data = self.store.read_json(self.state_path, {})
        if data:
            self._state = InstallState(
                running=False,
                bundle_id=str(data.get("bundle_id", "")),
                completed_steps=int(data.get("completed_steps", 0)),
                total_steps=int(data.get("total_steps", 0)),
                errors=list(data.get("errors") or []),
            )

    def _save_state(self) -> None:
        self.store.write_json(self.state_path, self._state.to_dict())

    def consent_status(self) -> dict[str, Any]:
        data = self.store.read_json(self.consent_path, {})
        return {
            "consented": bool(data.get("consented")),
            "consented_at": data.get("consented_at"),
            "allow_r18": bool(data.get("allow_r18", True)),
            "allow_downloads": bool(data.get("allow_downloads", True)),
        }

    def grant_consent(self, *, allow_r18: bool = True, allow_downloads: bool = True) -> dict[str, Any]:
        self.store.write_json(
            self.consent_path,
            {
                "consented": True,
                "consented_at": time.time(),
                "allow_r18": allow_r18,
                "allow_downloads": allow_downloads,
            },
        )
        return self.consent_status()

    def revoke_consent(self) -> dict[str, Any]:
        if self.consent_path.is_file():
            self.consent_path.unlink(missing_ok=True)
        return self.consent_status()

    def _network_ok(self) -> tuple[bool, str]:
        if not self.settings.network_install_enabled:
            return False, "network_install_disabled"
        if self._guard:
            return self._guard()
        return True, ""

    def info(self) -> dict[str, Any]:
        return {
            "product": "Monster AI Ecosystem",
            "developer": DEVELOPER,
            "bundles": list_bundles(self._manifest),
            "consent": self.consent_status(),
            "status": self.status(),
        }

    def status(self) -> dict[str, Any]:
        return self._state.to_dict()

    async def start(self, bundle_id: str) -> dict[str, Any]:
        if self._task and not self._task.done():
            return {"ok": False, "reason": "already_running", "status": self.status()}
        steps = bundle_steps(bundle_id, self._manifest)
        if not steps:
            return {"ok": False, "reason": "unknown_bundle", "bundle_id": bundle_id}

        ok, reason = self._network_ok()
        if not ok:
            return {"ok": False, "reason": reason}
        if self.settings.require_consent and not self.consent_status().get("consented"):
            return {"ok": False, "reason": "consent_required"}

        self._state = InstallState(
            running=True,
            bundle_id=bundle_id,
            total_steps=len(steps),
            started_at=time.time(),
        )
        self._save_state()
        self._task = asyncio.create_task(self._run_bundle(bundle_id, steps))
        return {"ok": True, "bundle_id": bundle_id, "total_steps": len(steps), "status": self.status()}

    async def stop(self) -> dict[str, Any]:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._state.running = False
        self._save_state()
        return {"ok": True, "status": self.status()}

    def _run_cmd(self, cmd: list[str], *, cwd: Path | None = None) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                cmd,
                cwd=str(cwd or self.root),
                capture_output=True,
                text=True,
                timeout=3600,
                check=False,
            )
            out = (r.stdout or "") + (r.stderr or "")
            return r.returncode == 0, out[-2000:]
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _comfy_custom_nodes_dir(self) -> Path | None:
        sys.path.insert(0, str(self.root / "scripts"))
        from detect_comfyui import find_comfyui

        base = find_comfyui()
        if not base:
            return None
        inner = base / "ComfyUI" if (base / "ComfyUI").exists() else base
        nodes = inner / "custom_nodes"
        nodes.mkdir(parents=True, exist_ok=True)
        return nodes

    def _patch_config_flags(self, patches: dict[str, Any]) -> tuple[bool, str]:
        cfg = self.root / "config.yaml"
        if not cfg.is_file():
            return False, "config.yaml missing"
        text = cfg.read_text(encoding="utf-8")
        for key_path, value in patches.items():
            # simple line replace: key: old -> key: new
            parts = key_path.split(".")
            if len(parts) == 2:
                section, key = parts
                import re

                pattern = rf"(  {key}:)\s*.*"
                repl = f"  {key}: {json.dumps(value) if isinstance(value, str) else value}"
                block = f"  {section}:"
                if block not in text:
                    continue
                text = re.sub(pattern, repl, text, count=1)
        cfg.write_text(text, encoding="utf-8")
        return True, "config patched"

    async def _step_pip_core(self) -> tuple[bool, str]:
        return await asyncio.to_thread(
            self._run_cmd,
            [sys.executable, "-m", "pip", "install", "-r", str(self.root / "requirements.txt")],
        )

    async def _step_pip_generate(self) -> tuple[bool, str]:
        req = self.root / "requirements-generate.txt"
        if not req.is_file():
            return True, "skip no requirements-generate.txt"
        return await asyncio.to_thread(
            self._run_cmd,
            [sys.executable, "-m", "pip", "install", "-r", str(req)],
        )

    async def _step_pip_quality(self) -> tuple[bool, str]:
        ok1, o1 = await asyncio.to_thread(
            self._run_cmd,
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "torch",
                "torchvision",
                "--index-url",
                "https://download.pytorch.org/whl/cu124",
            ],
        )
        ok2, o2 = await asyncio.to_thread(
            self._run_cmd,
            [sys.executable, "-m", "pip", "install", "open-clip-torch>=2.24.0"],
        )
        return ok1 and ok2, o1 + o2

    async def _step_install_mini(self) -> tuple[bool, str]:
        script = self.root / "scripts" / "install_mini_monster_ai.py"
        return await asyncio.to_thread(self._run_cmd, [sys.executable, str(script)])

    async def _step_install_modules(self) -> tuple[bool, str]:
        script = self.root / "scripts" / "install_modules.py"
        return await asyncio.to_thread(
            self._run_cmd,
            [sys.executable, str(script), "--with-quality", "--download-models"],
        )

    async def _step_ollama(self, models: list[str]) -> tuple[bool, str]:
        outputs: list[str] = []
        ok_all = True
        for m in models:
            ok, out = await asyncio.to_thread(self._run_cmd, ["ollama", "pull", m])
            outputs.append(out)
            ok_all = ok_all and ok
        return ok_all, "\n".join(outputs)[-2000:]

    async def _step_ollama_roleplay(self) -> tuple[bool, str]:
        models = self._manifest.get("ollama_models", {}).get("roleplay", ["qwen2.5:7b"])
        return await self._step_ollama(list(models))

    async def _step_ollama_uncensored(self) -> tuple[bool, str]:
        models = self._manifest.get("ollama_models", {}).get("uncensored", ["qwen2.5:7b"])
        return await self._step_ollama(list(models))

    async def _step_ollama_lite(self) -> tuple[bool, str]:
        models = self._manifest.get("ollama_models", {}).get("lite", ["llama3.2:latest"])
        return await self._step_ollama(list(models))

    async def _step_piper_voices(self) -> tuple[bool, str]:
        script = self.root / "scripts" / "install_voice_pack.py"
        if script.is_file():
            return await asyncio.to_thread(
                self._run_cmd,
                [sys.executable, str(script), "--voice", "zh_CN-huayan-medium"],
            )
        return await asyncio.to_thread(
            self._run_cmd,
            [sys.executable, str(self.root / "scripts" / "install_modules.py")],
        )

    async def _step_xtts_optional(self) -> tuple[bool, str]:
        ok, out = await asyncio.to_thread(
            self._run_cmd,
            [sys.executable, "-m", "pip", "install", "TTS>=0.22.0"],
        )
        if ok:
            self._patch_config_flags({"modules.tts": True})  # noqa — handled below
            cfg = self.root / "config.yaml"
            if cfg.is_file():
                t = cfg.read_text(encoding="utf-8")
                if "xtts_enabled:" in t:
                    t = t.replace("xtts_enabled: false", "xtts_enabled: true")
                    cfg.write_text(t, encoding="utf-8")
        return ok, out or "xtts optional"

    async def _step_comfy_custom_nodes(self) -> tuple[bool, str]:
        nodes_dir = self._comfy_custom_nodes_dir()
        if not nodes_dir:
            return False, "ComfyUI not found"
        logs: list[str] = []
        ok_all = True
        for spec in self._manifest.get("comfy_custom_nodes") or []:
            dest = nodes_dir / spec["name"]
            if dest.exists():
                logs.append(f"skip {spec['name']}")
                continue
            ok, out = await asyncio.to_thread(
                self._run_cmd,
                ["git", "clone", "--depth", "1", spec["repo"], str(dest)],
            )
            logs.append(out)
            ok_all = ok_all and ok
        return ok_all, "\n".join(logs)[-2000:]

    async def _step_download_checkpoints(self) -> tuple[bool, str]:
        script = self.root / "scripts" / "download_models.py"
        if script.is_file():
            return await asyncio.to_thread(self._run_cmd, [sys.executable, str(script)])
        return await self._download_manifest_checkpoints()

    async def _download_manifest_checkpoints(self) -> tuple[bool, str]:
        if not self.consent_status().get("allow_downloads"):
            return False, "downloads_not_consented"
        sys.path.insert(0, str(self.root / "scripts"))
        from download_models import comfyui_checkpoint_dir, download_checkpoint

        ckpt_dir = comfyui_checkpoint_dir()
        if not ckpt_dir:
            return False, "no comfyui checkpoint dir"
        ok_all = True
        logs: list[str] = []
        for _key, spec in (self._manifest.get("checkpoints") or {}).items():
            try:
                download_checkpoint(spec["repo"], spec["file"], ckpt_dir)
                logs.append(f"ok {spec['file']}")
            except Exception as exc:  # noqa: BLE001
                ok_all = False
                logs.append(str(exc))
        return ok_all, "\n".join(logs)

    async def _step_download_r18_assets(self) -> tuple[bool, str]:
        """Fetch open photoreal / NSFW-capable asset hints + optional HF LoRA placeholders."""
        if not self.consent_status().get("allow_r18"):
            return True, "r18 skipped by consent"
        cache = Path(self.settings.data_dir) / "r18_catalog.json"
        catalog = {
            "ts": time.time(),
            "hints": [
                {"type": "checkpoint", "hint": "Juggernaut XL / RealVisXL / Pony — place in ComfyUI checkpoints"},
                {"type": "lora", "hint": "detail / skin / likeness LoRA — ComfyUI loras folder"},
                {"type": "node", "hint": "IPAdapter-plus + AnimateDiff-Evolved installed via comfy_custom_nodes"},
            ],
            "civitai_search": "https://civitai.com/models?sort=Most+Downloaded&types=Checkpoint,LORA",
        }
        cache.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"catalog written {cache}"

    async def _step_chinese_persona(self) -> tuple[bool, str]:
        script = self.root / "scripts" / "install_chinese_text.py"
        if not script.is_file():
            return True, "skip chinese persona"
        return await asyncio.to_thread(self._run_cmd, [sys.executable, str(script)])

    async def _step_enable_all_modules(self) -> tuple[bool, str]:
        patches = {
            "learning.web_learning_enabled": True,
            "learning.image_learning_enabled": True,
            "learning.curriculum_enabled": True,
        }
        cfg = self.root / "config.yaml"
        if not cfg.is_file():
            return False, "no config"
        t = cfg.read_text(encoding="utf-8")
        replacements = [
            ("web_learning_enabled: false", "web_learning_enabled: true"),
            ("image_learning_enabled: false", "image_learning_enabled: true"),
            ("curriculum_enabled: false", "curriculum_enabled: true"),
            ("network_learning_enabled: false", "network_learning_enabled: true"),
            ("xtts_enabled: false", "xtts_enabled: true"),
        ]
        for old, new in replacements:
            if old in t:
                t = t.replace(old, new)
        cfg.write_text(t, encoding="utf-8")
        return True, "all modules enabled in config"

    async def _step_enable_mini_modules(self) -> tuple[bool, str]:
        return await self._step_enable_all_modules()

    async def _step_enable_r18_modules(self) -> tuple[bool, str]:
        return await self._step_enable_all_modules()

    async def _step_enable_roleplay(self) -> tuple[bool, str]:
        cfg = self.root / "config.yaml"
        if not cfg.is_file():
            return False, "no config"
        t = cfg.read_text(encoding="utf-8")
        t = t.replace("roleplay:\n    enabled: false", "roleplay:\n    enabled: true")
        if "roleplay_web_enabled: false" in t:
            t = t.replace("roleplay_web_enabled: false", "roleplay_web_enabled: true")
        cfg.write_text(t, encoding="utf-8")
        return True, "roleplay enabled"

    async def _step_enable_image_video(self) -> tuple[bool, str]:
        cfg = self.root / "config.yaml"
        if not cfg.is_file():
            return False, "no config"
        t = cfg.read_text(encoding="utf-8")
        for old, new in [
            ("image:\n    enabled: false", "image:\n    enabled: true"),
            ("video:\n    enabled: false", "video:\n    enabled: true"),
        ]:
            t = t.replace(old, new)
        cfg.write_text(t, encoding="utf-8")
        return True, "image+video enabled"

    async def _step_enable_audio(self) -> tuple[bool, str]:
        cfg = self.root / "config.yaml"
        if not cfg.is_file():
            return False, "no config"
        t = cfg.read_text(encoding="utf-8").replace("tts:\n    enabled: false", "tts:\n    enabled: true")
        cfg.write_text(t, encoding="utf-8")
        return True, "tts enabled"

    async def _step_rebuild_monsterlock_seal(self) -> tuple[bool, str]:
        script = self.root / "scripts" / "monsterlock" / "recover_from_self_destruct.py"
        if script.is_file():
            return await asyncio.to_thread(self._run_cmd, [sys.executable, str(script)])
        return True, "skip monsterlock seal"

    def _step_handler(self, step_id: str):
        return {
            "pip_core": self._step_pip_core,
            "pip_generate": self._step_pip_generate,
            "pip_quality": self._step_pip_quality,
            "install_mini": self._step_install_mini,
            "install_modules": self._step_install_modules,
            "ollama_roleplay": self._step_ollama_roleplay,
            "ollama_uncensored": self._step_ollama_uncensored,
            "ollama_lite": self._step_ollama_lite,
            "piper_voices": self._step_piper_voices,
            "xtts_optional": self._step_xtts_optional,
            "comfy_custom_nodes": self._step_comfy_custom_nodes,
            "download_checkpoints": self._step_download_checkpoints,
            "download_r18_assets": self._step_download_r18_assets,
            "chinese_persona": self._step_chinese_persona,
            "enable_all_modules": self._step_enable_all_modules,
            "enable_mini_modules": self._step_enable_mini_modules,
            "enable_r18_modules": self._step_enable_r18_modules,
            "enable_roleplay": self._step_enable_roleplay,
            "enable_image_video": self._step_enable_image_video,
            "enable_audio": self._step_enable_audio,
            "rebuild_monsterlock_seal": self._step_rebuild_monsterlock_seal,
        }.get(step_id)

    async def _run_bundle(self, bundle_id: str, steps: list[str]) -> None:
        try:
            for i, step_id in enumerate(steps):
                self._state.current_step = step_id
                self._save_state()
                handler = self._step_handler(step_id)
                if not handler:
                    self._state.errors.append(f"unknown_step:{step_id}")
                    continue
                ok, detail = await handler()
                self._state.log.append(
                    {"step": step_id, "ok": ok, "detail": detail[:500], "ts": time.time()}
                )
                if not ok:
                    self._state.errors.append(f"{step_id}:{detail[:120]}")
                self._state.completed_steps = i + 1
                self._save_state()
        except asyncio.CancelledError:
            self._state.running = False
            self._save_state()
            raise
        except Exception as exc:  # noqa: BLE001
            self._state.errors.append(str(exc))
        finally:
            self._state.running = False
            self._state.finished_at = time.time()
            self._state.current_step = ""
            self._save_state()