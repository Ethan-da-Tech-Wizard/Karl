from __future__ import annotations

import re
from dataclasses import dataclass

from app.vision.schemas import ImageRecord, OcrResult, VisionResult
from app.vision.vision_model_loader import VisionModelLoader


ERROR_PATTERNS = (
    "traceback",
    "exception",
    "error",
    "failed",
    "failure",
    "warning",
    "segmentation fault",
    "nameerror",
    "typeerror",
    "valueerror",
    "importerror",
    "modulenotfounderror",
    "syntaxerror",
    "referenceerror",
    "stack trace",
)

CODE_PATTERNS = (
    r"\bdef\s+\w+",
    r"\bclass\s+\w+",
    r"\bimport\s+\w+",
    r"\bfrom\s+\w+\s+import\b",
    r"\bfunction\s+\w+",
    r"\bconst\s+\w+",
    r"\blet\s+\w+",
    r"\bvar\s+\w+",
    r"=>",
    r"\{.*\}",
    r"\bline\s+\d+",
)

DOCUMENT_PATTERNS = (
    "invoice",
    "receipt",
    "page",
    "chapter",
    "paragraph",
    "document",
    "signature",
)

UI_PATTERNS = (
    "button",
    "menu",
    "dialog",
    "sidebar",
    "toolbar",
    "modal",
    "panel",
)


@dataclass(frozen=True)
class AnalysisSuggestion:
    kind: str
    tags: list[str]
    detected_code: bool
    detected_error: bool
    layout: str


class VisionAnalyzer:
    def __init__(self, vision_loader=VisionModelLoader):
        self.vision_loader = vision_loader

    def analyze_record(
        self,
        record: ImageRecord,
        ocr: OcrResult | None = None,
        mode: str = "ocr_vision",
        prompt: str | None = None,
    ) -> tuple[VisionResult, AnalysisSuggestion]:
        effective_ocr = ocr or record.ocr
        suggestion = classify_image(record, effective_ocr.text)

        if mode == "ocr_only":
            vision = VisionResult(
                engine="ocr-heuristic",
                model=None,
                caption=self._heuristic_caption(record, effective_ocr, suggestion),
                layout=suggestion.layout,
                detected_code=suggestion.detected_code,
                detected_error=suggestion.detected_error,
            )
            return vision, suggestion

        vision = self.vision_loader.describe_image(
            record.original_path,
            prompt=prompt,
        )
        if not vision.layout:
            vision.layout = suggestion.layout
        vision.detected_code = vision.detected_code or suggestion.detected_code
        vision.detected_error = vision.detected_error or suggestion.detected_error
        if not vision.caption:
            vision.caption = self._heuristic_caption(record, effective_ocr, suggestion)
        return vision, suggestion

    @staticmethod
    def _heuristic_caption(record: ImageRecord, ocr: OcrResult, suggestion: AnalysisSuggestion) -> str:
        ocr_state = "OCR text detected" if ocr.text.strip() else "No OCR text detected"
        details = [
            f"{record.width}x{record.height} image classified as {suggestion.kind}.",
            ocr_state + f" with engine {ocr.engine}.",
        ]
        if suggestion.detected_error:
            details.append("Visible text appears to contain an error or traceback.")
        elif suggestion.detected_code:
            details.append("Visible text appears to contain source code or terminal output.")
        details.append("Load a local vision model for pixel-level description beyond OCR and heuristics.")
        return " ".join(details)


def classify_image(record: ImageRecord, text: str) -> AnalysisSuggestion:
    lowered = text.lower()
    detected_error = any(marker in lowered for marker in ERROR_PATTERNS)
    detected_code = detected_error or any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in CODE_PATTERNS)

    tags: list[str] = []
    kind = record.kind if record.kind != "unknown" else "unknown"

    if detected_error:
        kind = "error"
        tags.extend(["error", "debug"])
    elif detected_code:
        kind = "code_screenshot"
        tags.extend(["code", "screenshot"])
    elif any(marker in lowered for marker in DOCUMENT_PATTERNS):
        kind = "document"
        tags.extend(["document", "ocr"])
    elif any(marker in lowered for marker in UI_PATTERNS):
        kind = "ui_mockup"
        tags.extend(["ui", "interface"])

    if record.source == "clipboard":
        tags.append("clipboard")
    if text.strip():
        tags.append("ocr")

    layout = _layout_hint(record, text)
    return AnalysisSuggestion(
        kind=kind,
        tags=_dedupe([*record.tags, *tags]),
        detected_code=detected_code,
        detected_error=detected_error,
        layout=layout,
    )


def _layout_hint(record: ImageRecord, text: str) -> str:
    aspect = record.width / record.height if record.height else 1.0
    lines = [line for line in text.splitlines() if line.strip()]
    if aspect > 1.6:
        shape = "wide landscape"
    elif aspect < 0.75:
        shape = "tall portrait"
    else:
        shape = "balanced frame"
    if len(lines) > 12:
        return f"{shape}; dense text layout with {len(lines)} OCR lines"
    if lines:
        return f"{shape}; sparse text layout with {len(lines)} OCR lines"
    return f"{shape}; no OCR text layout signal"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        clean = value.strip().lower()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
    return out
