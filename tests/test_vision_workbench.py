import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtCore import Qt

from app.state import AppState
from app.ui.workspaces.vision_workbench import VisionWorkbench


def test_vision_workbench_lists_saved_images(tmp_path):
    state = AppState()
    state.image_store = state.image_store.__class__(base_dir=str(tmp_path / "images"))

    image = QImage(40, 30, QImage.Format.Format_RGB32)
    image.fill(QColor("#00C2FF"))
    record = state.image_store.save_qimage(image, source="test")

    workspace = VisionWorkbench(state)
    workspace.refresh()

    ids = [
        workspace._library.item(i).data(Qt.ItemDataRole.UserRole)
        for i in range(workspace._library.count())
    ]
    assert record.id in ids


def test_vision_workbench_saves_metadata_and_corrections(tmp_path):
    state = AppState()
    state.image_store = state.image_store.__class__(base_dir=str(tmp_path / "images"))

    image = QImage(40, 30, QImage.Format.Format_RGB32)
    image.fill(QColor("#00C2FF"))
    record = state.image_store.save_qimage(image, source="test")

    workspace = VisionWorkbench(state)
    workspace._selected_id = record.id
    workspace._render_record(record)

    workspace._kind_combo.setCurrentIndex(workspace._kind_combo.findData("code_screenshot"))
    workspace._tags.setText("code, error")
    workspace._save_metadata()

    workspace._ocr.setPlainText("NameError visible in screenshot")
    workspace._save_ocr_correction()

    workspace._caption.setPlainText("Editor screenshot with a Python NameError.")
    workspace._save_caption_correction()

    loaded = state.image_store.get(record.id)
    assert loaded.kind == "code_screenshot"
    assert loaded.tags == ["code", "error"]
    assert loaded.ocr.text == "NameError visible in screenshot"
    assert loaded.vision.caption == "Editor screenshot with a Python NameError."
