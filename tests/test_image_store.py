import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QColor, QImage

from app.vision.schemas import OcrResult
from app.vision.image_store import ImageStore


def _sample_image(width=80, height=48):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#00C2FF"))
    return image


def test_save_qimage_creates_record_and_files(tmp_path):
    store = ImageStore(base_dir=str(tmp_path / "images"))
    record = store.save_qimage(_sample_image(), source="test")

    assert record.id
    assert record.source == "test"
    assert record.width == 80
    assert record.height == 48
    assert record.mime == "image/png"
    assert len(record.sha256) == 64
    assert os.path.exists(record.original_path)
    assert os.path.exists(record.thumbnail_path)
    assert os.path.exists(record.processed_path)

    loaded = store.get(record.id)
    assert loaded.id == record.id
    assert loaded.original_path == record.original_path


def test_import_file_copies_image(tmp_path):
    source = tmp_path / "source.png"
    assert _sample_image(32, 24).save(str(source), "PNG")

    store = ImageStore(base_dir=str(tmp_path / "images"))
    record = store.import_file(str(source))

    assert record.width == 32
    assert record.height == 24
    assert record.original_path != str(source)
    assert os.path.exists(record.original_path)


def test_update_analysis_round_trip(tmp_path):
    store = ImageStore(base_dir=str(tmp_path / "images"))
    record = store.save_qimage(_sample_image(), source="test")

    updated = store.update_analysis(record.id, kind="code_screenshot", tags=["code", "error"])

    assert updated.kind == "code_screenshot"
    assert updated.tags == ["code", "error"]
    assert store.get(record.id).kind == "code_screenshot"


def test_update_analysis_accepts_ocr_dict(tmp_path):
    store = ImageStore(base_dir=str(tmp_path / "images"))
    record = store.save_qimage(_sample_image(), source="test")
    ocr = OcrResult(engine="tesseract", text="NameError at line 3", confidence=0.9)

    updated = store.update_analysis(record.id, ocr=ocr.to_dict())

    assert updated.ocr.text == "NameError at line 3"
    assert updated.ocr.confidence == 0.9
    assert store.get(record.id).ocr.engine == "tesseract"
