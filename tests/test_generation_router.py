"""Generation router — backends, VAE, FHD–8K resolution policy."""
from __future__ import annotations

from monster_ai.modules.generation.router import (
    MAX_HEIGHT,
    MAX_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    GenerationRouter,
    clamp_resolution,
    get_backend,
    match_checkpoint,
)


def test_clamp_below_fhd_raises_to_minimum():
    w, h, meta = clamp_resolution(512, 512)
    assert w >= MIN_WIDTH
    assert h >= MIN_HEIGHT
    assert meta["clamped"] is True


def test_clamp_above_8k_caps():
    w, h, meta = clamp_resolution(10000, 6000)
    assert w <= MAX_WIDTH
    assert h <= MAX_HEIGHT
    assert meta["clamped"] is True


def test_backend_checkpoint_match():
    backend = get_backend("flux")
    matched = match_checkpoint(backend, ["flux1-dev.safetensors", "sd15.safetensors"])
    assert matched == "flux1-dev.safetensors"


def test_router_resolve_with_backend():
    router = GenerationRouter()
    out = router.resolve(
        backend_id="sdxl",
        width=1920,
        height=1080,
        available_checkpoints=["juggernautXL.safetensors"],
    )
    assert out["backend"] == "sdxl"
    assert out["width"] >= MIN_WIDTH
    assert out["height"] >= MIN_HEIGHT
    assert out["checkpoint"] == "juggernautXL.safetensors"
    assert out["vae"]


def test_list_resolutions_includes_fhd_and_8k():
    router = GenerationRouter()
    presets = router.list_resolutions()
    ids = {p["id"] for p in presets}
    assert "fhd_16_9" in ids
    assert "8k_16_9" in ids
    fhd = next(p for p in presets if p["id"] == "fhd_16_9")
    assert fhd["width"] == 1920 and fhd["height"] == 1080