from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from app.vision.ocr_engine import TesseractOcrEngine


class ImageAnalysisThread(QThread):
    progress = pyqtSignal(str)
    ocr_done = pyqtSignal(str, object)  # image_id, OcrResult
    done = pyqtSignal(str, object)      # image_id, ImageRecord
    error = pyqtSignal(str)

    def __init__(self, image_store, image_id: str, lang: str = "eng", parent=None):
        super().__init__(parent)
        self.image_store = image_store
        self.image_id = image_id
        self.lang = lang

    def run(self):
        try:
            record = self.image_store.get(self.image_id)
            image_path = record.processed_path or record.original_path
            self.progress.emit("running OCR")
            ocr = TesseractOcrEngine().analyze(image_path, lang=self.lang)
            record.ocr = ocr
            updated = self.image_store.update_analysis(self.image_id, ocr=ocr.to_dict())
            self.ocr_done.emit(self.image_id, ocr)
            self.done.emit(self.image_id, updated)
        except Exception as exc:
            self.error.emit(str(exc))

