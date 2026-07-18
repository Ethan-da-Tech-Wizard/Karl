"""Speculative decoding configuration and integration guards."""

from __future__ import annotations

from pathlib import Path


def test_registry_companion_draft_is_discoverable(tmp_path, monkeypatch):
    from app.engine import config_store

    monkeypatch.chdir(tmp_path)
    config_store._registry_cache = None
    config_store._registry_cache_mtime = None

    config_store.write_json_atomic(
        config_store.MODEL_REGISTRY_PATH,
        [
            {
                "filename": "target.gguf",
                "n_ctx": 4096,
                "draft_model_filename": "draft.gguf",
            }
        ],
    )
    config_store.set_active_model("target.gguf")

    draft_cfg = config_store.get_active_draft_model()

    assert config_store.registry_draft_model_filename("target.gguf") == "draft.gguf"
    assert draft_cfg["enabled"] == False
    assert draft_cfg["filename"] == "draft.gguf"


def test_active_draft_model_persists_enabled_flag(tmp_path, monkeypatch):
    from app.engine import config_store

    monkeypatch.chdir(tmp_path)

    assert config_store.set_active_draft_model("draft.gguf", enabled=True)
    draft_cfg1 = config_store.get_active_draft_model()
    assert draft_cfg1["enabled"] == True
    assert draft_cfg1["filename"] == "draft.gguf"

    assert config_store.set_active_draft_model(None, enabled=False)
    draft_cfg2 = config_store.get_active_draft_model()
    assert draft_cfg2["enabled"] == False
    assert draft_cfg2["filename"] is None


def test_model_loader_uses_persisted_draft_setting():
    source = Path("app/engine/model_loader.py").read_text(encoding="utf-8")

    assert "config_store.get_active_draft_model()" in source
    assert "needs_reload or needs_draft_reload" in source
    assert "change speculative draft model" in source
    assert "class _LlamaDraftModelAdapter" in source
    assert "draft_model=cls._draft_instance" in source


def test_status_bar_exposes_speculative_indicator():
    source = Path("app/ui/widgets/status_bar.py").read_text(encoding="utf-8")

    assert "def set_speculative_active" in source
    assert "[Speculative Active]" in source
