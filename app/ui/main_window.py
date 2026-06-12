"""
Karl MainWindow — sidebar shell + workspace router.
All heavy logic lives in the individual workspace widgets.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget,
)
from PyQt6.QtGui import QKeySequence, QShortcut

from app.state import AppState
from app.ui.sidebar import Sidebar
from app.ui.widgets.status_bar import StatusBar
from app.ui.workspaces.workbench import WorkbenchWorkspace
from app.ui.workspaces.prompt_lab import PromptLabWorkspace
from app.ui.workspaces.knowledge_base import KnowledgeBaseWorkspace
from app.ui.workspaces.vision_workbench import VisionWorkbench
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
        self._load_theme_config()
        self._connect_signals()
        self._init_model()

        # Keyboard Navigation Shortcuts
        self._setup_shortcuts()

        # Start WebSocket Server to bridge editor/VS Code extensions
        self._init_websocket_server()

    def _setup_shortcuts(self):
        # Open Command Palette
        self._palette_shortcut_k = QShortcut(QKeySequence("Ctrl+K"), self)
        self._palette_shortcut_k.activated.connect(self._open_command_palette)
        self._palette_shortcut_p = QShortcut(QKeySequence("Ctrl+P"), self)
        self._palette_shortcut_p.activated.connect(self._open_command_palette)
        
        # Workspace switching (Ctrl+1 to Ctrl+8)
        self._workspace_shortcuts = []
        for idx in range(8):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{idx+1}"), self)
            # Use a helper slot to avoid lambda cell capture issues
            shortcut.activated.connect(self._make_workspace_switcher(idx))
            self._workspace_shortcuts.append(shortcut)
            
        # Focus input
        self._focus_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self._focus_shortcut.activated.connect(self._focus_active_input)
        
        # New session
        self._new_session_shortcut = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
        self._new_session_shortcut.activated.connect(self._workbench._new_session)
        
        # Save session snapshot
        self._save_session_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._save_session_shortcut.activated.connect(self._workbench._save_current_session)

    def _make_workspace_switcher(self, idx):
        return lambda: self._sidebar.select(idx)

    def _open_command_palette(self):
        from app.ui.widgets.command_palette import CommandPalette
        palette = CommandPalette(self, self)
        palette.exec()

    def _focus_active_input(self):
        current_widget = self._stack.currentWidget()
        if not current_widget:
            return
        from PyQt6.QtWidgets import QLineEdit, QTextEdit
        inputs = current_widget.findChildren((QLineEdit, QTextEdit))
        for inp in inputs:
            if inp.isVisible() and inp.isEnabled() and not inp.isReadOnly():
                inp.setFocus()
                break

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
        self._vision         = VisionWorkbench(self._state, self._workbench)
        self._training       = TrainingStudioWorkspace(self._state)
        self._eval           = EvalSuiteWorkspace(self._state)
        self._system         = SystemConfigWorkspace(self._state)
        self._system.set_workbench(self._workbench)
        self._docs           = DocsWorkspace(self._state)
        self._docs.set_workbench(self._workbench)

        for ws in (
            self._workbench,
            self._prompt_lab,
            self._knowledge_base,
            self._vision,
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
        self._workbench.appearance_requested.connect(self._open_appearance_controls)
        self._system.adapter_changed.connect(self._status_bar.set_adapter)
        self._system.adapter_changed.connect(self._on_adapter_changed)
        self._system.appearance_changed.connect(self._apply_theme_from_state)

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

    def _open_appearance_controls(self):
        self._sidebar.select(6)
        if hasattr(self._system, "show_theme_tab"):
            self._system.show_theme_tab()

    def _load_theme_config(self):
        from app.engine import config_store

        config = config_store.get_ui_config()
        self._state.theme_preset = config["theme_preset"]
        self._state.custom_accent = config["custom_accent"]
        self._state.layout_preset = config["layout_preset"]
        self._state.reduced_motion = config["reduced_motion"]
        self._state.glow_enabled = config["glow_enabled"]
        self._state.animation_intensity = config["animation_intensity"]
        self._state.glow_strength = config["glow_strength"]

        self._apply_theme_from_state()

    def _apply_theme_from_state(self):
        from PyQt6.QtWidgets import QApplication
        from app.ui.themes import get_theme_stylesheet

        # Apply stylesheet to application
        stylesheet_str = get_theme_stylesheet(self._state)
        QApplication.instance().setStyleSheet(stylesheet_str)

        # Apply theme colors to the workbench workspace
        self._workbench.update_theme()

        # Apply layout preset
        self.apply_layout_preset(self._state.layout_preset)

    def apply_layout_preset(self, preset_name: str):
        # 1. Sidebar and status bar visibilities
        if preset_name == "Minimal Distraction":
            self._sidebar.hide()
            self._status_bar.hide()
        else:
            self._sidebar.show()
            self._status_bar.show()

        # 2. Dock visibilities and layout options in active workspaces
        # Workbench Workspace Docks
        if hasattr(self, "_workbench"):
            wb = self._workbench
            if hasattr(wb, "_sessions_dock") and hasattr(wb, "_reasoning_dock"):
                if preset_name in ("Focused Workbench", "Minimal Distraction"):
                    wb._sessions_dock.hide()
                    wb._reasoning_dock.hide()
                elif preset_name == "Max Introspection":
                    wb._sessions_dock.hide()
                    wb._reasoning_dock.show()
                elif preset_name == "Knowledge Heavy":
                    wb._sessions_dock.show()
                    wb._reasoning_dock.hide()
                else:
                    # Default/Research Lab/Wide Monitor Command
                    wb._sessions_dock.show()
                    wb._reasoning_dock.show()

                # Adjust sizes
                if preset_name == "Wide Monitor Command":
                    wb._sessions_dock.setMinimumWidth(320)
                    wb._reasoning_dock.setMinimumWidth(450)
                else:
                    wb._sessions_dock.setMinimumWidth(200)
                    wb._reasoning_dock.setMinimumWidth(280)

    def _init_websocket_server(self):
        from app.engine.websocket_server import WebSocketServerManager
        try:
            self._ws_server = WebSocketServerManager.get_instance(port=8080)
        except Exception as e:
            print(f"[WebSocket] Failed to start WebSocket server on boot: {e}")

    def closeEvent(self, event):
        self._workbench.on_close()
        
        # Safely shut down the WebSocket server connection bridge on exit
        from app.engine.websocket_server import WebSocketServerManager
        try:
            WebSocketServerManager.reset_instance()
        except Exception as e:
            print(f"[WebSocket] Error during exit teardown: {e}")
            
        event.accept()
