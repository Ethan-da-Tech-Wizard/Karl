"""
Karl MainWindow — sidebar shell + workspace router.
All heavy logic lives in the individual workspace widgets.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget,
)

from app.state import AppState
from app.ui.sidebar import Sidebar
from app.ui.widgets.status_bar import StatusBar
from app.ui.workspaces.workbench import WorkbenchWorkspace
from app.ui.workspaces.prompt_lab import PromptLabWorkspace
from app.ui.workspaces.knowledge_base import KnowledgeBaseWorkspace
from app.ui.workspaces.training_studio import TrainingStudioWorkspace
from app.ui.workspaces.eval_suite import EvalSuiteWorkspace
from app.ui.workspaces.system_config import SystemConfigWorkspace
from app.ui.workspaces.docs import DocsWorkspace


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl")
        self.setMinimumSize(1200, 760)

        self._state = AppState()
        self._build_ui()
        self._connect_signals()
        self._init_model()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Sidebar + stack row
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._sidebar = Sidebar()
        content_layout.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        content_layout.addWidget(self._stack, 1)

        # Create workspaces
        self._workbench      = WorkbenchWorkspace(self._state)
        self._prompt_lab     = PromptLabWorkspace(self._state)
        self._knowledge_base = KnowledgeBaseWorkspace(self._state)
        self._training       = TrainingStudioWorkspace(self._state)
        self._eval           = EvalSuiteWorkspace(self._state)
        self._system         = SystemConfigWorkspace(self._state)
        self._system.set_workbench(self._workbench)
        self._docs           = DocsWorkspace(self._state)

        for ws in (
            self._workbench,
            self._prompt_lab,
            self._knowledge_base,
            self._training,
            self._eval,
            self._system,
            self._docs,
        ):
            self._stack.addWidget(ws)

        # Status bar
        self._status_bar = StatusBar()

        # Stack content above status bar
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(content, 1)
        wrapper_layout.addWidget(self._status_bar)

        self.setCentralWidget(wrapper)

    def _connect_signals(self):
        self._sidebar.workspace_changed.connect(self._stack.setCurrentIndex)
        self._workbench.status_changed.connect(self._on_status_changed)
        self._workbench.model_changed.connect(self._status_bar.set_model)
        self._workbench.adapter_changed.connect(self._status_bar.set_adapter)
        self._workbench.adapter_changed.connect(self._on_adapter_changed)
        self._system.adapter_changed.connect(self._status_bar.set_adapter)
        self._system.adapter_changed.connect(self._on_adapter_changed)

    def _init_model(self):
        from app.engine.model_loader import ModelLoader
        try:
            ModelLoader.get_instance()
            name = ModelLoader.model_name()
            self._state.model_name = name
            self._status_bar.set_model(name)

            # Sync active adapter on load
            adapter = getattr(ModelLoader, "_active_adapter", None)
            self._state.adapter_name = adapter
            self._status_bar.set_adapter(adapter)

            # Sync workspace dropdowns
            self._workbench._refresh_model_combo()
            self._system._scan_adapters()
        except FileNotFoundError:
            self._status_bar.set_state("no model — run download_test_model.py", False)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_status_changed(self, text: str, active: bool):
        self._status_bar.set_state(text, active)

    def _on_adapter_changed(self, name: str):
        self._state.adapter_name = name if name else None

    def closeEvent(self, event):
        self._workbench.on_close()
        event.accept()

