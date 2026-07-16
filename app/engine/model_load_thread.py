from __future__ import annotations

import os

from PyQt6.QtCore import QThread, pyqtSignal


class ModelLoadThread(QThread):
    """Load or reload a GGUF model without blocking the Qt GUI thread."""

    loaded = pyqtSignal(str, object, object)  # filename, adapter_name, draft_filename
    error = pyqtSignal(str)

    def __init__(
        self,
        model_path: str | None = None,
        *,
        adapter_name: str | None = None,
        draft_model_path: str | None = None,
        persist_active: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.model_path = model_path
        self.adapter_name = adapter_name
        self.draft_model_path = draft_model_path
        self.persist_active = persist_active

    def run(self) -> None:
        from app.engine import config_store
        from app.engine.model_loader import ModelLoader

        try:
            ModelLoader.reset_instance()
            ModelLoader.get_instance(
                model_path=self.model_path,
                adapter_name=self.adapter_name,
                draft_model_path=self.draft_model_path,
            )

            filename = os.path.basename(self.model_path) if self.model_path else ModelLoader.model_name()
            draft_filename = os.path.basename(self.draft_model_path) if self.draft_model_path else None

            if self.persist_active:
                if not config_store.set_active_model(filename, self.adapter_name):
                    raise OSError("Failed to persist data/active_model.json")
                if draft_filename:
                    config_store.set_active_draft_model(draft_filename, enabled=True)

            self.loaded.emit(filename, self.adapter_name, draft_filename)
        except Exception as exc:
            self.error.emit(str(exc))
