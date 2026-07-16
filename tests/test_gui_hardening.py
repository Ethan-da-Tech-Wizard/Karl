import tests.qt_test_helper  # noqa: F401

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt


class _FakeMainWindow:
    def __init__(self):
        self.calls = []

    def switch_workspace(self, index):
        self.calls.append(("switch_workspace", index))

    def start_new_workbench_session(self):
        self.calls.append(("start_new_workbench_session",))

    def save_workbench_session(self):
        self.calls.append(("save_workbench_session",))

    def toggle_workbench_rag(self):
        self.calls.append(("toggle_workbench_rag",))

    def toggle_workbench_agentic_loop(self):
        self.calls.append(("toggle_workbench_agentic_loop",))

    def open_knowledge_ingest(self):
        self.calls.append(("open_knowledge_ingest",))

    def rebuild_knowledge_index(self):
        self.calls.append(("rebuild_knowledge_index",))

    def run_eval_suite(self):
        self.calls.append(("run_eval_suite",))

    def open_system_defaults(self):
        self.calls.append(("open_system_defaults",))


def test_command_palette_uses_public_actions():
    from app.ui.widgets.command_palette import CommandPalette

    fake = _FakeMainWindow()
    host = QWidget()
    palette = CommandPalette(fake, parent=host)

    titles = [title for title, _action in palette._commands]
    assert "System Config: Open Defaults Tab" in titles
    assert "System Config: Open Settings Tab" not in titles

    palette.input_edit.setText("Run Benchmarks")
    item = palette.list_widget.item(0)
    assert item is not None
    assert item.data(Qt.ItemDataRole.UserRole) is not None
    palette.list_widget.setCurrentItem(item)
    palette._execute_selected()

    assert fake.calls == [("run_eval_suite",)]


def test_prompt_column_ignores_run_when_thread_active():
    from app.ui.workspaces.prompt_lab import _PromptColumn

    class FakeThread:
        def isRunning(self):
            return True

    column = _PromptColumn("A")
    emitted = []
    column.run_requested.connect(lambda label, text: emitted.append((label, text)))
    column._user_edit.setPlainText("hello")
    column._thread = FakeThread()

    column._emit_run()

    assert emitted == []


def test_prompt_lab_focus_primary_input_targets_active_editor():
    from app.state import AppState
    from app.ui.workspaces.prompt_lab import PromptLabWorkspace

    workspace = PromptLabWorkspace(AppState())
    workspace.show()
    QApplication.processEvents()

    assert workspace.focus_primary_input() is True
    QApplication.processEvents()
    assert QApplication.focusWidget() is workspace._col_a._user_edit


def test_log_decrypt_thread_unauthorized_without_entries():
    from app.ui.workspaces.flywheel_studio import _LogDecryptThread

    signals = []
    thread = _LogDecryptThread("token", [])
    thread.unauthorized.connect(lambda: signals.append("unauthorized"))

    thread.run()

    assert signals == ["unauthorized"]


def test_workspace_public_action_wrappers_exist():
    from app.state import AppState
    from app.ui.workspaces.eval_suite import EvalSuiteWorkspace
    from app.ui.workspaces.knowledge_base import KnowledgeBaseWorkspace
    from app.ui.workspaces.system_config import SystemConfigWorkspace
    from app.ui.workspaces.workbench import WorkbenchWorkspace

    state = AppState()
    workbench = WorkbenchWorkspace(state)
    kb = KnowledgeBaseWorkspace(state)
    eval_suite = EvalSuiteWorkspace(state)
    system = SystemConfigWorkspace(state)

    for name in (
        "new_session",
        "save_current_session",
        "toggle_rag_pipeline",
        "toggle_agentic_loop",
        "toggle_all_huds",
        "toggle_reasoning_panel",
        "toggle_sessions_panel",
        "toggle_rag_panel",
        "toggle_context_panel",
    ):
        assert callable(getattr(workbench, name))

    assert callable(kb.open_ingest_dialog)
    assert callable(kb.rebuild_index)
    assert callable(eval_suite.run_suite)
    assert callable(system.show_defaults_tab)


# ── MainWindow.closeEvent thread-shutdown coverage ────────────────────────────
#
# MainWindow.closeEvent() explicitly .wait()s for two specific threads (the
# model-init thread it owns, and System Config's own model-load thread) --
# see the comment there: "The llama load cannot be interrupted; wait for it
# so the process does not tear down Qt objects under a running thread." It
# does NOT reference the Knowledge Base or Flywheel Studio workspaces at
# all. These tests lock in both halves of that behavior: the explicit wait
# actually happens, and closing while a KB/Flywheel worker thread is still
# running doesn't raise or hang the close path (even though, as the second
# test documents, those specific threads aren't joined).

class _FakeQThread:
    """Minimal stand-in for the two threads closeEvent() explicitly waits
    on -- controllable isRunning()/wait() without spinning up a real Qt
    thread, so this test is deterministic and fast."""

    def __init__(self, running: bool = True):
        self._running = running
        self.wait_called = False

    def isRunning(self):
        return self._running

    def wait(self):
        self.wait_called = True
        self._running = False


class _FakeCloseEvent:
    def __init__(self):
        self.accepted = False

    def accept(self):
        self.accepted = True


def _stub_close_teardown(monkeypatch):
    """closeEvent() also tears down the WS bridge, revokes OS-keychain
    tokens, and scrubs shared memory -- stub those side effects out so
    these tests only exercise the thread-waiting logic."""
    from app.engine.websocket_server import WebSocketServerManager
    from app.utils.ipc_helper import SharedMemoryManager
    import app.utils.keychain_manager as keychain_manager

    monkeypatch.setattr(WebSocketServerManager, "reset_instance", classmethod(lambda cls: None))
    monkeypatch.setattr(keychain_manager, "revoke_tokens", lambda: None)
    monkeypatch.setattr(
        SharedMemoryManager, "instance",
        classmethod(lambda cls: type("_Stub", (), {"_cleanup_all": lambda self: None})()),
    )


def test_close_event_waits_for_model_init_thread(monkeypatch):
    from app.ui.main_window import MainWindow

    _stub_close_teardown(monkeypatch)

    fake_self = type("FakeSelf", (), {})()
    fake_self._workbench = type("FakeWorkbench", (), {"on_close": lambda self: None})()
    fake_self._model_init_thread = _FakeQThread(running=True)
    fake_self._system = type("FakeSystem", (), {"_model_load_thread": None})()

    event = _FakeCloseEvent()
    MainWindow.closeEvent(fake_self, event)

    assert fake_self._model_init_thread.wait_called is True
    assert fake_self._model_init_thread.isRunning() is False
    assert event.accepted is True


def test_close_event_waits_for_system_config_model_thread(monkeypatch):
    """A second, independent place a model can be mid-load from: the
    System Config workspace's own model-load thread."""
    from app.ui.main_window import MainWindow

    _stub_close_teardown(monkeypatch)

    system_thread = _FakeQThread(running=True)
    fake_self = type("FakeSelf", (), {})()
    fake_self._workbench = type("FakeWorkbench", (), {"on_close": lambda self: None})()
    fake_self._model_init_thread = None
    fake_self._system = type("FakeSystem", (), {"_model_load_thread": system_thread})()

    event = _FakeCloseEvent()
    MainWindow.closeEvent(fake_self, event)

    assert system_thread.wait_called is True
    assert event.accepted is True


def test_close_event_survives_active_kb_and_flywheel_threads(monkeypatch):
    """Closing the real MainWindow while a Knowledge Base ingest thread and
    a Flywheel Studio log-decrypt thread are genuinely running (real
    QThread.start(), not a mock) must not raise or hang -- even though
    closeEvent() doesn't join either of them. If that guarantee is ever
    added, strengthen this test to assert the threads finish, not just
    that close() didn't blow up.
    """
    import threading as _threading

    from PyQt6.QtCore import QThread, QTimer, pyqtSignal
    from PyQt6.QtWidgets import QApplication

    import app.ui.main_window as main_window_mod

    app = QApplication.instance() or QApplication([])

    class _BlockingThread(QThread):
        """Runs until the test releases it -- gives deterministic control
        over isRunning() instead of racing a real ingest/decrypt job."""
        finished_signal = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.release_event = _threading.Event()

        def run(self):
            self.release_event.wait(timeout=5.0)

    # Replace every workspace except the two under test with a cheap stub,
    # matching the pattern used for MainWindow construction in
    # test_watchdog.py -- keeps this test fast and focused.
    class _FakeWorkspace(QWidget):
        # Union of signals _connect_signals() wires up from _workbench and
        # _system -- both get replaced by this same stub class here, so it
        # needs to satisfy both call sites.
        status_changed = pyqtSignal(str, bool)
        model_changed = pyqtSignal(str)
        adapter_changed = pyqtSignal(str)
        context_stats = pyqtSignal(int, int, int, int)
        appearance_requested = pyqtSignal()
        appearance_changed = pyqtSignal()

        def __init__(self, *args, **kwargs):
            super().__init__()

        def on_close(self):
            """closeEvent() unconditionally calls self._workbench.on_close();
            WorkbenchWorkspace is one of the stubbed-out workspaces here."""
            pass

    for name in (
        "WorkbenchWorkspace", "PromptLabWorkspace", "VisionWorkbench",
        "TrainingStudioWorkspace", "EvalSuiteWorkspace", "SwarmStudioWorkspace",
        "SystemConfigWorkspace", "DocsWorkspace",
    ):
        monkeypatch.setattr(main_window_mod, name, _FakeWorkspace)

    monkeypatch.setattr(main_window_mod.MainWindow, "_setup_shortcuts", lambda self: None)
    monkeypatch.setattr(main_window_mod.MainWindow, "_load_theme_config", lambda self: None)
    monkeypatch.setattr(main_window_mod.QTimer, "singleShot", lambda *a, **kw: None)
    _stub_close_teardown(monkeypatch)

    window = main_window_mod.MainWindow()

    kb_thread = _BlockingThread()
    kb_thread.start()
    window._knowledge_base._ingest_thread = kb_thread
    window._knowledge_base._active_threads.add(kb_thread)

    flywheel_thread = _BlockingThread()
    flywheel_thread.start()
    window._flywheel._log_decrypt_thread = flywheel_thread

    try:
        for _ in range(20):
            if kb_thread.isRunning() and flywheel_thread.isRunning():
                break
            app.processEvents()
            QThread.msleep(10)
        assert kb_thread.isRunning() is True
        assert flywheel_thread.isRunning() is True

        event = _FakeCloseEvent()
        main_window_mod.MainWindow.closeEvent(window, event)

        assert event.accepted is True
        # Documents current behavior: neither thread was joined by close.
        assert kb_thread.isRunning() is True
        assert flywheel_thread.isRunning() is True
    finally:
        kb_thread.release_event.set()
        flywheel_thread.release_event.set()
        kb_thread.wait(2000)
        flywheel_thread.wait(2000)
