from __future__ import annotations

import csv
import shutil
import subprocess
from io import StringIO

from app.vision.schemas import OcrResult


class TesseractOcrEngine:
    def __init__(self, executable: str = "tesseract"):
        self.executable = executable

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def version(self) -> str | None:
        if not self.available():
            return None
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=8,
            )
        except Exception:
            return None
        first = (result.stdout or result.stderr or "").splitlines()
        return first[0].strip() if first else None

    def analyze(self, image_path: str, lang: str = "eng") -> OcrResult:
        if not self.available():
            return OcrResult(
                engine="tesseract",
                language=lang,
                text="",
                confidence=0.0,
                boxes=[{"error": "tesseract executable not found"}],
            )

        result = subprocess.run(
            [self.executable, image_path, "stdout", "-l", lang, "tsv"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "unknown OCR error").strip()
            return OcrResult(
                engine="tesseract",
                language=lang,
                text="",
                confidence=0.0,
                boxes=[{"error": message}],
            )

        return self._parse_tsv(result.stdout, lang)

    def _parse_tsv(self, raw: str, lang: str) -> OcrResult:
        reader = csv.DictReader(StringIO(raw), delimiter="\t")
        words = []
        boxes = []
        confidences = []

        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            try:
                conf = float(row.get("conf", "-1"))
            except ValueError:
                conf = -1.0
            if conf >= 0:
                confidences.append(conf)
            words.append(text)
            boxes.append({
                "text": text,
                "confidence": conf,
                "left": int(float(row.get("left", 0) or 0)),
                "top": int(float(row.get("top", 0) or 0)),
                "width": int(float(row.get("width", 0) or 0)),
                "height": int(float(row.get("height", 0) or 0)),
                "block": int(float(row.get("block_num", 0) or 0)),
                "line": int(float(row.get("line_num", 0) or 0)),
            })

        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OcrResult(
            engine="tesseract",
            language=lang,
            text=" ".join(words),
            confidence=round(confidence / 100.0, 4),
            boxes=boxes,
        )

