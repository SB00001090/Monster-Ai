"""Training vault encryption tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from monster_ai.config import GuardianSettings, ImageQualitySettings
from monster_ai.modules.guardian.key_manager import TrainingKeyManager
from monster_ai.modules.guardian.training_vault import TrainingVault
from monster_ai.modules.image.quality import QualityReport
from monster_ai.modules.image.quality_store import QualityStore


@pytest.fixture
def vault_setup(tmp_path: Path):
    settings = GuardianSettings(
        data_dir=str(tmp_path / "guardian"),
        training_encryption_enabled=True,
        bind_hardware_key=True,
        require_user_passphrase=False,
    )
    km = TrainingKeyManager(settings, tmp_path, hardware_fingerprint="test-hw-fp-abc")
    km.unlock(None)
    vault = TrainingVault(tmp_path / "guardian", km)
    return settings, km, vault


def test_encrypted_image_roundtrip(vault_setup) -> None:
    _, _, vault = vault_setup
    src = vault_setup[0]
    tmp = Path(src.data_dir).parent / "img.png"
    Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)).save(tmp)
    meta = {"label": "good", "prompt": "secret prompt", "score": 0.9}
    out = vault.store_image_asset(tmp, label="good", metadata=meta)
    assert out.suffix == ".mgtrain"
    assert "secret prompt" not in out.read_text(encoding="utf-8")

    listed = vault.list_assets("good")
    assert len(listed) == 1
    decrypted = vault.decrypt_asset_to_memory(listed[0]["id"])
    assert decrypted is not None
    assert decrypted["metadata"]["prompt"] == "secret prompt"


def test_text_template_encrypted(vault_setup) -> None:
    _, _, vault = vault_setup
    path = vault.store_text_asset(
        label="template",
        name="sdxl_stable",
        content="masterpiece, best quality, {{prompt}}",
        metadata={"steps": 30},
    )
    assert path.exists()
    assert "masterpiece" not in path.read_text(encoding="utf-8")


def test_quality_store_uses_vault(vault_setup, tmp_path: Path) -> None:
    _, _, vault = vault_setup
    qdir = tmp_path / "quality"
    settings = ImageQualitySettings(data_dir=str(qdir))
    store = QualityStore(settings.data_dir, settings, training_vault=vault, encrypt_training=True)
    src = tmp_path / "gen.png"
    Image.fromarray(np.zeros((16, 16, 3), dtype=np.uint8)).save(src)
    report = QualityReport(passed=True, score=0.88)
    out = store.save_good(src, prompt="hidden", negative="", report=report, checkpoint="ckpt", attempt=0)
    assert out is not None
    assert out.suffix == ".mgtrain"
    assert not (store.good_dir / "gen.png").exists()
    records = store.read_log_records()
    assert len(records) == 1
    assert records[0]["prompt"] == "hidden"


def test_export_import_encrypted_bundle(vault_setup) -> None:
    _, km, vault = vault_setup
    vault.store_text_asset(label="prompt", name="p1", content="test prompt example")
    exported = vault.export_encrypted_bundle()
    assert len(exported.get("assets", [])) >= 1

    vault2 = TrainingVault(Path(vault_setup[0].data_dir), km)
    result = vault2.import_encrypted_bundle(exported)
    assert result["imported"] >= 1


def test_migrate_plaintext_deletes_source(vault_setup, tmp_path: Path) -> None:
    _, _, vault = vault_setup
    good_dir = tmp_path / "legacy" / "good"
    good_dir.mkdir(parents=True)
    src = good_dir / "old.png"
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(src)
    (good_dir / "old.json").write_text('{"label":"good","prompt":"legacy"}', encoding="utf-8")
    r = vault.migrate_plaintext_dir(good_dir, label="good", delete_plaintext=True)
    assert r["migrated"] == 1
    assert not src.exists()
    assert vault.list_assets("good")