from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage


def image_info(path: str) -> dict:
    image = QImage(path)
    if image.isNull():
        raise ValueError(f"Could not read image: {path}")
    return {
        "width": image.width(),
        "height": image.height(),
        "bytes": os.path.getsize(path),
    }


def make_thumbnail(src: str, dst: str, max_size: int = 512) -> None:
    image = QImage(src)
    if image.isNull():
        raise ValueError(f"Could not read image: {src}")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    thumb = image.scaled(
        max_size,
        max_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if not thumb.save(dst):
        raise OSError(f"Could not write thumbnail: {dst}")


def prepare_for_ocr(src: str, dst: str) -> dict:
    image = QImage(src)
    if image.isNull():
        raise ValueError(f"Could not read image: {src}")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    normalized = image.convertToFormat(QImage.Format.Format_RGB32)
    if not normalized.save(dst):
        raise OSError(f"Could not write OCR image: {dst}")
    return {
        "width": normalized.width(),
        "height": normalized.height(),
        "path": dst,
    }

