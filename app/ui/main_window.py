"""
Karl MainWindow — sidebar shell + workspace router.
All heavy logic lives in the individual workspace widgets.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget,
)
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
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
from app.ui.workspaces.swarm_studio import SwarmStudioWorkspace
from app.ui.workspaces.flywheel_studio import FlywheelStudioWorkspace


logger = logging.getLogger("karl.main_window")


class _ModelInitThread(QThread):
    """Loads the active model off the UI thread at startup."""

    loaded = pyqtSignal(str, object)   # model name, adapter name or None
    failed = pyqtSignal(str)

    def run(self):
        from app.engine.model_loader import ModelLoader
        try:
            ModelLoader.get_instance()
            adapter = getattr(ModelLoader, "_active_adapter", None)
            self.loaded.emit(ModelLoader.model_name(), adapter)
        except FileNotFoundError:
            self.failed.emit("no model — run download_test_model.py")
        except Exception as exc:
            logger.error("startup model load failed: %s", exc)
            self.failed.emit(f"model load failed: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl")
        self.setMinimumSize(1200, 760)

        self._state = AppState()
        self._build_ui()
        self._load_theme_config()
        self._connect_signals()

        # Keyboard Navigation Shortcuts
        self._setup_shortcuts()

        # Heavy startup work is deferred so the window paints first: the
        # model loads on a worker thread (multi-second under VRAM/disk
        # pressure) and the WebSocket bridge starts after the first paint.
        self._model_init_thread = None
        QTimer.singleShot(0, self._init_model)
        QTimer.singleShot(0, self._init_websocket_server)

    def _setup_shortcuts(self):
        # Open Command Palette
        self._palette_shortcut_k = QShortcut(QKeySequence("Ctrl+K"), self)
        self._palette_shortcut_k.activated.connect(self._open_command_palette)
        self._palette_shortcut_p = QShortcut(QKeySequence("Ctrl+P"), self)
        self._palette_shortcut_p.activated.connect(self._open_command_palette)
        
        # Workspace switching (Ctrl+1 to Ctrl+0)
        self._workspace_shortcuts = []
        for idx in range(10):
            key = f"Ctrl+{idx+1}" if idx < 9 else "Ctrl+0"
            shortcut = QShortcut(QKeySequence(key), self)
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

        # Heavenscape HUD Toggle Shortcuts
        self._hud_toggle_all_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        self._hud_toggle_all_shortcut.activated.connect(self._workbench._toggle_all_huds)

        self._hud_reasoning_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        self._hud_reasoning_shortcut.activated.connect(self._workbench._toggle_reasoning)

        self._hud_sessions_shortcut = QShortcut(QKeySequence("Ctrl+Shift+L"), self)
        self._hud_sessions_shortcut.activated.connect(self._workbench._toggle_sessions)

        self._hud_rag_shortcut = QShortcut(QKeySequence("Ctrl+Shift+G"), self)
        self._hud_rag_shortcut.activated.connect(self._workbench._toggle_rag_hud)

        self._hud_context_shortcut = QShortcut(QKeySequence("Ctrl+Shift+B"), self)
        self._hud_context_shortcut.activated.connect(self._workbench._toggle_context_hud)

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
        self._swarm          = SwarmStudioWorkspace(self._state)
        self._system         = SystemConfigWorkspace(self._state)
        self._docs           = DocsWorkspace(self._state)
        self._docs.set_workbench(self._workbench)
        self._flywheel       = FlywheelStudioWorkspace(self._state)
        self._system.set_workbench(self._workbench) # system config knows about workbench

        for ws in (
            self._workbench,
            self._prompt_lab,
            self._knowledge_base,
            self._vision,
            self._training,
            self._eval,
            self._swarm,
            self._system,
            self._docs,
            self._flywheel,
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
        self._state.state_changed.connect(self._on_state_changed)

    def _init_model(self):
        if self._model_init_thread is not None and self._model_init_thread.isRunning():
            return
        self._status_bar.set_state("loading model…", True)
        self._model_init_thread = _ModelInitThread(self)
        self._model_init_thread.loaded.connect(self._on_startup_model_loaded)
        self._model_init_thread.failed.connect(self._on_startup_model_failed)
        self._model_init_thread.start()

    def _on_startup_model_loaded(self, name: str, adapter: object):
        self._state.model_name = name
        self._status_bar.set_model(name)

        # Sync active adapter on load
        self._state.adapter_name = adapter
        self._status_bar.set_adapter(adapter)

        # Sync workspace dropdowns
        self._workbench._refresh_model_combo()
        self._system._scan_adapters()
        self._status_bar.set_state("idle", False)

    def _on_startup_model_failed(self, message: str):
        self._status_bar.set_state(message, False)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_status_changed(self, text: str, active: bool):
        self._status_bar.set_state(text, active)
        state = "idle"
        if text == "error":
            state = "error"
        elif active:
            state = "generating"
        self.setProperty("modelState", state)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_adapter_changed(self, name: str):
        self._state.adapter_name = name if name else None

    def _on_state_changed(self, name: str, value: object):
        if name in (
            "theme_preset", "theme_mode", "custom_accent", "layout_preset",
            "reduced_motion", "glow_enabled", "animation_intensity", "glow_strength"
        ):
            self._apply_theme_from_state()
        elif name == "model_name":
            self._status_bar.set_model(str(value))
        elif name == "adapter_name":
            self._status_bar.set_adapter(value)

    def _open_appearance_controls(self):
        self._sidebar.select(7)
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
        self._state.log_rotation_size_mb = config.get("log_rotation_size_mb", 10)
        self._state.log_retention_days = config.get("log_retention_days", 30)

        self._apply_theme_from_state()

    def _apply_theme_from_state(self):
        from PyQt6.QtWidgets import QApplication
        from app.ui.themes import get_theme_stylesheet

        # Re-applying an identical app-wide stylesheet forces Qt to restyle
        # every widget; skip it when nothing in the compiled QSS changed
        # (e.g. only glow/animation toggles were touched).
        stylesheet_str = get_theme_stylesheet(self._state)
        if stylesheet_str != getattr(self, "_applied_stylesheet", None):
            QApplication.instance().setStyleSheet(stylesheet_str)
            self._applied_stylesheet = stylesheet_str

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
            logger.warning(f"Failed to start WebSocket server on boot: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "_bridge_poll_timer"):
            self._bridge_poll_timer = QTimer(self)
            self._bridge_poll_timer.timeout.connect(self._poll_bridge_status)
            self._bridge_poll_timer.start(5000)
            self._poll_bridge_status()

    def _poll_bridge_status(self):
        try:
            from app.engine.websocket_server import WebSocketServerManager
            ws_mgr = WebSocketServerManager._instance
            if ws_mgr and ws_mgr.server is not None:
                n = len(ws_mgr.clients)
                if n > 0:
                    self._status_bar.set_bridge_status("connected", n)
                else:
                    self._status_bar.set_bridge_status("listening")
            else:
                self._status_bar.set_bridge_status("offline")
        except Exception:
            try:
                self._status_bar.set_bridge_status("offline")
            except Exception:
                pass

    def closeEvent(self, event):
        self._workbench.on_close()

        # The llama load cannot be interrupted; wait for it so the process
        # does not tear down Qt objects under a running thread.
        if self._model_init_thread is not None and self._model_init_thread.isRunning():
            self._model_init_thread.wait()

        # Safely shut down the WebSocket server connection bridge on exit
        from app.engine.websocket_server import WebSocketServerManager
        try:
            WebSocketServerManager.reset_instance()
        except Exception as e:
            logger.warning(f"Error during exit teardown: {e}")

        event.accept()
