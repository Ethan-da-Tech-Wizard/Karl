from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class OcrResult:
    engine: str = "none"
    language: str = "eng"
    text: str = ""
    confidence: float = 0.0
    boxes: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OcrResult":
        data = data or {}
        return cls(
            engine=data.get("engine", "none"),
            language=data.get("language", "eng"),
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            boxes=list(data.get("boxes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisionResult:
    engine: str = "none"
    model: str | None = None
    caption: str = ""
    layout: str = ""
    detected_code: bool = False
    detected_error: bool = False
    objects: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VisionResult":
        data = data or {}
        return cls(
            engine=data.get("engine", "none"),
            model=data.get("model"),
            caption=data.get("caption", ""),
            layout=data.get("layout", ""),
            detected_code=bool(data.get("detected_code", False)),
            detected_error=bool(data.get("detected_error", False)),
            objects=list(data.get("objects", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImageRecord:
    id: str
    created_at: str
    source: str
    kind: str
    original_path: str
    thumbnail_path: str
    processed_path: str | None
    sha256: str
    width: int
    height: int
    mime: str
    tags: list[str] = field(default_factory=list)
    ocr: OcrResult = field(default_factory=OcrResult)
    vision: VisionResult = field(default_factory=VisionResult)
    corrections: dict[str, Any] = field(default_factory=lambda: {
        "ocr_text": None,
        "caption": None,
        "answer": None,
    })
    rag: dict[str, Any] = field(default_factory=lambda: {
        "indexed": False,
        "indexed_at": None,
        "text": "",
    })

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageRecord":
        return cls(
            id=data["id"],
            created_at=data.get("created_at", ""),
            source=data.get("source", "file"),
            kind=data.get("kind", "unknown"),
            original_path=data.get("original_path", ""),
            thumbnail_path=data.get("thumbnail_path", ""),
            processed_path=data.get("processed_path"),
            sha256=data.get("sha256", ""),
            width=int(data.get("width", 0) or 0),
            height=int(data.get("height", 0) or 0),
            mime=data.get("mime", "image/png"),
            tags=list(data.get("tags", [])),
            ocr=OcrResult.from_dict(data.get("ocr")),
            vision=VisionResult.from_dict(data.get("vision")),
            corrections=dict(data.get("corrections", {})),
            rag=dict(data.get("rag", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ocr"] = self.ocr.to_dict()
        data["vision"] = self.vision.to_dict()
        return data

