import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vision.vision_model_loader import installed_vision_models, read_vision_registry


def test_vision_registry_is_readable():
    entries = read_vision_registry()

    assert entries
    assert all(entry.id for entry in entries)
    assert all(entry.model_filename.endswith(".gguf") for entry in entries)
    assert all(entry.projector_filename.endswith(".gguf") for entry in entries)


def test_installed_vision_models_reports_paths_and_install_state():
    rows = installed_vision_models()

    assert rows
    first = rows[0]
    assert "model_path" in first
    assert "projector_path" in first
    assert "model_installed" in first
    assert "projector_installed" in first
