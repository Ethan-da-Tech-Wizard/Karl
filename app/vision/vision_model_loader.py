from __future__ import annotations

import base64
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.vision.schemas import VisionResult


REGISTRY_PATH = Path("data/vision_model_registry.json")
ACTIVE_PATH = Path("data/active_vision_model.json")
MODEL_DIR = Path("data/vision_models")
PROJECTOR_DIR = Path("data/vision_projectors")


@dataclass(frozen=True)
class VisionModelEntry:
    id: str
    name: str
    family: str
    model_filename: str
    projector_filename: str
    min_ram_gb: float = 0.0
    min_vram_gb: float = 0.0
    n_ctx: int = 4096
    strengths: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisionModelEntry":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            family=data.get("family", "llava15"),
            model_filename=data.get("model_filename", ""),
            projector_filename=data.get("projector_filename", ""),
            min_ram_gb=float(data.get("min_ram_gb", 0.0) or 0.0),
            min_vram_gb=float(data.get("min_vram_gb", 0.0) or 0.0),
            n_ctx=int(data.get("n_ctx", 4096) or 4096),
            strengths=data.get("strengths", ""),
            notes=data.get("notes", ""),
        )

    def model_path(self) -> Path:
        return MODEL_DIR / self.model_filename

    def projector_path(self) -> Path:
        return PROJECTOR_DIR / self.projector_filename

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "family": self.family,
            "model_filename": self.model_filename,
            "projector_filename": self.projector_filename,
            "min_ram_gb": self.min_ram_gb,
            "min_vram_gb": self.min_vram_gb,
            "n_ctx": self.n_ctx,
            "strengths": self.strengths,
            "notes": self.notes,
            "model_path": str(self.model_path()),
            "projector_path": str(self.projector_path()),
            "model_installed": self.model_path().exists(),
            "projector_installed": self.projector_path().exists(),
        }


def read_vision_registry(path: Path = REGISTRY_PATH) -> list[VisionModelEntry]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        return []
    return [VisionModelEntry.from_dict(item) for item in raw]


def active_vision_model_id(path: Path = ACTIVE_PATH) -> str | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    return data.get("id") or data.get("vision_model_id")


def set_active_vision_model(model_id: str, path: Path = ACTIVE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"id": model_id}, f, indent=2)


def installed_vision_models() -> list[dict[str, Any]]:
    return [entry.to_dict() for entry in read_vision_registry()]


class VisionModelLoader:
    _lock = threading.Lock()
    _entry: VisionModelEntry | None = None
    _llm = None
    _last_error = ""

    @classmethod
    def status(cls) -> dict[str, Any]:
        entry = cls._entry or cls._default_entry()
        backend = cls._backend_status()
        return {
            "loaded": cls._llm is not None,
            "active_id": entry.id if entry else None,
            "active_name": entry.name if entry else None,
            "backend_available": backend["available"],
            "backend_error": backend["error"],
            "last_error": cls._last_error,
            "registry": installed_vision_models(),
        }

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._llm = None
            cls._entry = None
            cls._last_error = ""

    @classmethod
    def load(cls, model_id: str | None = None):
        with cls._lock:
            entry = cls._resolve_entry(model_id)
            cls._entry = entry
            cls._llm = None
            cls._last_error = ""

            if entry is None:
                cls._last_error = "no vision model registry entries found"
                return None
            if not entry.model_path().exists():
                cls._last_error = f"vision model file is missing: {entry.model_path()}"
                return None
            if not entry.projector_path().exists():
                cls._last_error = f"vision projector file is missing: {entry.projector_path()}"
                return None

            try:
                from llama_cpp import Llama
            except Exception as exc:
                cls._last_error = f"llama_cpp import failed: {exc}"
                return None

            handler_cls, handler_error = cls._handler_class(entry.family)
            if handler_cls is None:
                cls._last_error = handler_error
                return None

            try:
                handler = handler_cls(clip_model_path=str(entry.projector_path()), verbose=False)
                cls._llm = Llama(
                    model_path=str(entry.model_path()),
                    chat_handler=handler,
                    n_ctx=entry.n_ctx,
                    n_gpu_layers=-1,
                    verbose=False,
                )
                set_active_vision_model(entry.id)
                return cls._llm
            except Exception as exc:
                cls._last_error = f"vision model load failed: {exc}"
                cls._llm = None
                return None

    @classmethod
    def describe_image(
        cls,
        image_path: str,
        prompt: str | None = None,
        model_id: str | None = None,
        max_tokens: int = 512,
    ) -> VisionResult:
        llm = cls._llm or cls.load(model_id)
        entry = cls._entry or cls._resolve_entry(model_id)
        model_name = entry.name if entry else None
        if llm is None:
            message = cls._last_error or "local vision model is not loaded"
            return VisionResult(
                engine="llama-cpp-unavailable",
                model=model_name,
                caption=f"Local image model unavailable: {message}",
            )

        try:
            data_url = cls._image_data_url(image_path)
            user_prompt = prompt or (
                "Describe this image accurately. If it is a code screenshot, identify visible errors, "
                "important filenames, relevant code, and likely fixes. Do not invent details you cannot see."
            )
            response = llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            caption = response["choices"][0]["message"]["content"].strip()
            return VisionResult(
                engine="llama-cpp-vision",
                model=model_name,
                caption=caption,
                detected_code=_looks_like_code(caption),
                detected_error=_looks_like_error(caption),
            )
        except Exception as exc:
            cls._last_error = f"vision inference failed: {exc}"
            return VisionResult(
                engine="llama-cpp-error",
                model=model_name,
                caption=cls._last_error,
            )

    @classmethod
    def _default_entry(cls) -> VisionModelEntry | None:
        entries = read_vision_registry()
        if not entries:
            return None
        active_id = active_vision_model_id()
        if active_id:
            for entry in entries:
                if entry.id == active_id:
                    return entry
        return entries[0]

    @classmethod
    def _resolve_entry(cls, model_id: str | None = None) -> VisionModelEntry | None:
        entries = read_vision_registry()
        if not entries:
            return None
        wanted = model_id or active_vision_model_id()
        if wanted:
            for entry in entries:
                if entry.id == wanted:
                    return entry
        return entries[0]

    @staticmethod
    def _handler_class(family: str):
        try:
            from llama_cpp.llama_chat_format import (
                Llava15ChatHandler,
                Llava16ChatHandler,
                MiniCPMv26ChatHandler,
                MoondreamChatHandler,
                NanoLlavaChatHandler,
                Qwen25VLChatHandler,
            )
        except Exception as exc:
            return None, f"llama-cpp multimodal handlers unavailable: {exc}"

        handlers = {
            "llava15": Llava15ChatHandler,
            "llava16": Llava16ChatHandler,
            "nanollava": NanoLlavaChatHandler,
            "minicpmv26": MiniCPMv26ChatHandler,
            "moondream": MoondreamChatHandler,
            "qwen25vl": Qwen25VLChatHandler,
        }
        handler = handlers.get(family)
        if handler is None:
            return None, f"unsupported vision model family: {family}"
        return handler, ""

    @staticmethod
    def _backend_status() -> dict[str, Any]:
        try:
            import llama_cpp  # noqa: F401
        except Exception as exc:
            return {"available": False, "error": f"llama_cpp unavailable: {exc}"}
        try:
            from llama_cpp.llama_chat_format import Llava15ChatHandler  # noqa: F401
        except Exception as exc:
            return {"available": False, "error": f"multimodal handlers unavailable: {exc}"}
        try:
            import llama_cpp.mtmd_cpp  # noqa: F401
        except Exception as exc:
            return {"available": False, "error": f"native multimodal mtmd library unavailable: {exc}"}
        return {"available": True, "error": ""}

    @staticmethod
    def _image_data_url(image_path: str) -> str:
        path = Path(image_path)
        suffix = path.suffix.lower().lstrip(".") or "png"
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
        with path.open("rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/{mime};base64,{encoded}"


def _looks_like_code(text: str) -> bool:
    lowered = text.lower()
    markers = ("code", "function", "class", "import", "traceback", "compiler", "terminal")
    return any(marker in lowered for marker in markers)


def _looks_like_error(text: str) -> bool:
    lowered = text.lower()
    markers = ("error", "exception", "traceback", "failed", "warning", "stack trace")
    return any(marker in lowered for marker in markers)
