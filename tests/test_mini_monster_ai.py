"""Tests for Mini Monster AI v1.0."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from monster_ai.config import MiniModuleSettings
from monster_ai.modules.mini.checkpoints import pick_checkpoint, pick_lora
from monster_ai.modules.mini.multilingual import analyze_prompt, detect_locales
from monster_ai.modules.mini.prompts import apply_template, build_negative, get_template, list_templates_api
from monster_ai.modules.mini.quality_guard import effective_template, quality_issues, quality_passed
from monster_ai.modules.mini.success_tracker import SuccessTracker
from monster_ai.modules.mini.workflow_builder import build_mini_txt2img


def test_templates_exist() -> None:
    assert len(list_templates_api()) >= 5
    assert get_template(None).id == "stable"
    assert get_template("idol_likeness").id == "idol_likeness"
    stable = get_template("stable")
    assert stable.width == 896
    assert stable.steps >= 30
    t = get_template("hq")
    assert t.steps >= 20
    neg = build_negative(t)
    assert "bad anatomy" in neg
    pos = apply_template("test subject", t)
    assert "photorealistic" in pos.lower()


def test_multilingual_detect() -> None:
    assert "zh-TW" in detect_locales("繁體中文測試")
    assert "en" in detect_locales("hello world")
    r = analyze_prompt("美女 portrait 寫實", preferred="zh-TW")
    assert r.primary == "zh-TW"
    assert r.mixed


def test_checkpoint_picker() -> None:
    ckpt, _ = pick_checkpoint("auto", ["juggernautXL_v9.safetensors", "sd15.safetensors"])
    assert "juggernaut" in ckpt.lower()
    lora = pick_lora("detail", ["detail_tweaker.safetensors", "other.safetensors"])
    assert lora is not None


def test_success_tracker(tmp_path: Path) -> None:
    tr = SuccessTracker(str(tmp_path))
    tr.record(ok=True, template_id="hq", quality_score=0.9)
    tr.record(ok=False, template_id="hq", quality_score=0.3)
    st = tr.status()
    assert st["total_recorded"] == 2
    assert st["success_rate"] == 0.5


def test_mini_workflow_builder() -> None:
    wf = build_mini_txt2img(
        positive="test",
        negative="bad",
        checkpoint="model.safetensors",
        width=1024,
        height=1024,
        steps=28,
        cfg=7.0,
        template_id="hq",
    )
    assert wf["6"]["inputs"]["text"] == "test"
    assert wf["3"]["inputs"]["steps"] == 28


def test_disclaimer_zh() -> None:
    from monster_ai.modules.mini.disclaimer import get_disclaimer

    d = get_disclaimer("zh-TW")
    assert "Suckbob" in d["text"]
    assert "肖像" in d["text"] or "Likeness" in d["text"]


def test_reference_store(tmp_path: Path) -> None:
    from monster_ai.modules.mini.likeness import ReferenceStore

    store = ReferenceStore(tmp_path)
    p = store.register(name="test_char", image_bytes=b"\x89PNG\r\n\x1a\n", image_ext=".png")
    assert store.get(p.id) is not None


def test_likeness_prompt() -> None:
    from monster_ai.modules.mini.likeness import ReferenceProfile, build_likeness_prompt

    prof = ReferenceProfile(id="x", name="Aria", image_path=Path("a.png"))
    assert "identical face" in build_likeness_prompt("scene", prof)


def test_quality_guard() -> None:
    settings = MiniModuleSettings(lite_mode=True, vram_profile="mini")
    hq = get_template("hq")
    capped = effective_template(hq, settings)
    assert max(capped.width, capped.height) <= 1152

    assert quality_passed({"quality": {"passed": True, "score": 0.9}}, min_score=0.52)
    assert not quality_passed({"quality": {"passed": False, "score": 0.3}}, min_score=0.52)
    assert quality_passed({"quality": {"passed": False, "score": 0.55}}, min_score=0.52)
    assert quality_issues({"quality": {"issues": ["low_clip"]}}) == ["low_clip"]


def test_alive_image_detects_blank(tmp_path: Path) -> None:
    from PIL import Image

    from monster_ai.core.generation_repair import is_alive_image

    good = tmp_path / "good.png"
    g = Image.new("RGB", (256, 256))
    for y in range(256):
        for x in range(256):
            g.putpixel((x, y), (x % 200, y % 180, (x + y) % 220))
    g.save(good)
    assert is_alive_image(good)

    black = tmp_path / "black.png"
    Image.new("RGB", (256, 256), (0, 0, 0)).save(black)
    assert not is_alive_image(black)


@pytest.mark.asyncio
async def test_mini_optimize_prompt(tmp_path: Path) -> None:
    from monster_ai.modules.mini.service import MiniMonsterService

    settings = MiniModuleSettings(data_dir=str(tmp_path), auto_optimize_prompt=True)
    image = MagicMock()
    image.client.ping = AsyncMock(return_value=True)
    repair = MagicMock()
    repair.generate = AsyncMock(return_value="beautiful woman, photorealistic")
    svc = MiniMonsterService(settings, image, repair)
    res = await svc.optimize_prompt("美女 寫實", locale="zh-TW")
    assert "美女" in res["optimized"]
    assert res["locale"] == "zh-TW"