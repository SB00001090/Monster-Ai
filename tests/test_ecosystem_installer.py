"""Tests for Monster AI ecosystem one-click installer."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from monster_ai.config import EcosystemSettings
from monster_ai.modules.ecosystem.disclaimer import privacy_notice
from monster_ai.modules.ecosystem.installer import EcosystemInstaller
from monster_ai.modules.ecosystem.manifest import bundle_steps, list_bundles, load_manifest


@pytest.fixture
def eco_settings(tmp_path: Path) -> EcosystemSettings:
    return EcosystemSettings(
        enabled=True,
        data_dir=str(tmp_path / "ecosystem"),
        network_install_enabled=True,
        require_consent=True,
        allow_r18_bundle=True,
    )


def test_manifest_loads_bundles() -> None:
    manifest = load_manifest()
    bundles = list_bundles(manifest)
    ids = {b["id"] for b in bundles}
    assert "full" in ids
    assert "mini" in ids
    assert "r18_multimodal" in ids
    full_steps = bundle_steps("full", manifest)
    assert "pip_core" in full_steps
    assert "install_mini" in full_steps


def test_privacy_notice() -> None:
    zh = privacy_notice("zh-TW")
    assert "Suckbob" in zh["text"]
    en = privacy_notice("en")
    assert "consent" in en["text"].lower()


def test_consent_flow(eco_settings: EcosystemSettings, tmp_path: Path) -> None:
    inst = EcosystemInstaller(eco_settings, root=tmp_path)
    assert not inst.consent_status()["consented"]
    inst.grant_consent(allow_r18=True, allow_downloads=True)
    assert inst.consent_status()["consented"]
    inst.revoke_consent()
    assert not inst.consent_status()["consented"]


def test_start_requires_consent(eco_settings: EcosystemSettings, tmp_path: Path) -> None:
    inst = EcosystemInstaller(eco_settings, root=tmp_path)

    async def _run() -> dict:
        return await inst.start("mini")

    result = asyncio.run(_run())
    assert not result["ok"]
    assert result["reason"] == "consent_required"


def test_start_unknown_bundle(eco_settings: EcosystemSettings, tmp_path: Path) -> None:
    inst = EcosystemInstaller(eco_settings, root=tmp_path)
    inst.grant_consent()

    async def _run() -> dict:
        return await inst.start("nonexistent_bundle")

    result = asyncio.run(_run())
    assert not result["ok"]
    assert result["reason"] == "unknown_bundle"


def test_network_guard_blocks(eco_settings: EcosystemSettings, tmp_path: Path) -> None:
    inst = EcosystemInstaller(
        eco_settings,
        root=tmp_path,
        network_guard=lambda: (False, "network_locked"),
    )
    inst.grant_consent()

    async def _run() -> dict:
        return await inst.start("mini")

    result = asyncio.run(_run())
    assert not result["ok"]
    assert result["reason"] == "network_locked"


@pytest.mark.asyncio
async def test_download_r18_assets_writes_catalog(
    eco_settings: EcosystemSettings, tmp_path: Path
) -> None:
    inst = EcosystemInstaller(eco_settings, root=tmp_path)
    inst.grant_consent(allow_r18=True)
    ok, detail = await inst._step_download_r18_assets()
    assert ok
    catalog = Path(eco_settings.data_dir) / "r18_catalog.json"
    assert catalog.is_file()
    assert "catalog written" in detail


@pytest.mark.asyncio
async def test_mini_bundle_steps_mocked(eco_settings: EcosystemSettings, tmp_path: Path) -> None:
    """Run mini bundle with mocked subprocess steps."""
    inst = EcosystemInstaller(eco_settings, root=tmp_path)
    inst.grant_consent()

    async def fake_step() -> tuple[bool, str]:
        return True, "mocked"

    for step_id in bundle_steps("mini"):
        handler = inst._step_handler(step_id)
        if handler:
            with patch.object(inst, handler.__name__, new=AsyncMock(side_effect=fake_step)):
                pass

    with patch.object(inst, "_step_pip_core", new=AsyncMock(return_value=(True, "ok"))), patch.object(
        inst, "_step_install_mini", new=AsyncMock(return_value=(True, "ok"))
    ), patch.object(
        inst, "_step_piper_voices", new=AsyncMock(return_value=(True, "ok"))
    ), patch.object(
        inst, "_step_ollama_lite", new=AsyncMock(return_value=(True, "ok"))
    ), patch.object(
        inst, "_step_enable_mini_modules", new=AsyncMock(return_value=(True, "ok"))
    ):
        result = await inst.start("mini")
        assert result["ok"]
        await inst._task
        st = inst.status()
        assert not st["running"]
        assert st["completed_steps"] == st["total_steps"]


def test_info_includes_developer(eco_settings: EcosystemSettings, tmp_path: Path) -> None:
    inst = EcosystemInstaller(eco_settings, root=tmp_path)
    info = inst.info()
    assert info["developer"] == "Suckbob"
    assert len(info["bundles"]) >= 6