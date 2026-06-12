import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QColor, QImage

from app.vision.image_store import ImageStore
from app.vision.schemas import OcrResult
from app.vision.vision_analyzer import VisionAnalyzer, classify_image


def _sample_image(width=80, height=48):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#101820"))
    return image


def test_classify_image_detects_code_error_from_ocr(tmp_path):
    store = ImageStore(base_dir=str(tmp_path / "images"))
    record = store.save_qimage(_sample_image(), source="clipboard")
    ocr_text = "Traceback NameError line 10 in def run"

    suggestion = classify_image(record, ocr_text)

    assert suggestion.kind == "error"
    assert suggestion.detected_error is True
    assert suggestion.detected_code is True
    assert "error" in suggestion.tags
    assert "clipboard" in suggestion.tags


def test_ocr_only_analysis_returns_honest_caption(tmp_path):
    store = ImageStore(base_dir=str(tmp_path / "images"))
    record = store.save_qimage(_sample_image(), source="test")
    ocr = OcrResult(engine="test", text="def run(): raise ValueError('bad')", confidence=0.9)

    vision, suggestion = VisionAnalyzer().analyze_record(record, ocr=ocr, mode="ocr_only")

    assert vision.engine == "ocr-heuristic"
    assert vision.detected_code is True
    assert suggestion.kind in {"code_screenshot", "error"}
    assert "Load a local vision model" in vision.caption
