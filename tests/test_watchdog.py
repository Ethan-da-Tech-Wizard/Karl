import os
import time
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget


def test_llm_watchdog_terminates_slow_stream(monkeypatch):
    app = QApplication.instance() or QApplication([])
    from app.engine.llm_thread import LLMThread
    from app.engine.model_loader import ModelLoader
    import app.engine.llm_thread as llm_thread

    class SlowStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            time.sleep(0.4)
            if self.closed:
                raise StopIteration
            return {"choices": [{"text": "late-token", "finish_reason": None}]}

        def close(self):
            self.closed = True

    class FakeLLM:
        def __init__(self):
            self.stream = SlowStream()
            self.reset_called = False

        def __call__(self, *args, **kwargs):
            return self.stream

        def tokenize(self, data, add_bos=False):
            return list(data[: max(1, min(len(data), 4))])

        def reset(self):
            self.reset_called = True

    fake_llm = FakeLLM()
    errors = []
    unlocked = []

    monkeypatch.setattr(
        llm_thread,
        "compile_and_reload",
        lambda module, path, notice_cb, logger: module,
    )
    monkeypatch.setattr(
        llm_thread.core.interaction_loop,
        "build_prompt",
        lambda system, history: "prompt",
    )
    monkeypatch.setattr(ModelLoader, "get_instance", lambda *args, **kwargs: fake_llm)
    monkeypatch.setattr(ModelLoader, "lock_instance", lambda: None)
    monkeypatch.setattr(ModelLoader, "unlock_instance", lambda: unlocked.append(True))
    monkeypatch.setattr(ModelLoader, "context_limit", lambda: 4096)
    monkeypatch.setattr(ModelLoader, "model_name", lambda: "fake.gguf")
    monkeypatch.setattr(llm_thread, "kv_cache_stats", lambda llm, prompt: {})
    monkeypatch.setattr(llm_thread, "log_cache_stats", lambda *args, **kwargs: None)

    thread = LLMThread(
        system_prompt="system",
        chat_history=[],
        hyperparams={"max_tokens": 8, "watchdog_timeout_seconds": 0.1},
    )
    thread.error_occurred.connect(errors.append)

    started = time.perf_counter()
    thread.run()
    elapsed = time.perf_counter() - started
    app.processEvents()

    assert elapsed < 2.0
    assert fake_llm.stream.closed
    assert fake_llm.reset_called
    assert unlocked == [True]
    assert thread._watchdog_error_emitted
    assert any("Inference Watchdog Timeout" in msg for msg in errors)


def test_agentic_watchdog_cleanup_emits_exact_timeout():
    from app.engine.agentic_thread import AgenticThread

    class FakeLLM:
        def __init__(self):
            self.reset_called = False

        def reset(self):
            self.reset_called = True

    class FakeStream:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    errors = []
    fake_llm = FakeLLM()
    fake_stream = FakeStream()
    thread = AgenticThread(
        system_prompt="system",
        initial_history=[],
        hyperparams={"watchdog_timeout_seconds": 0.1},
    )
    thread._active_response_generator = fake_stream
    thread.error_occurred.connect(errors.append)

    thread._cleanup_after_watchdog_timeout(fake_llm)

    assert thread._stop_requested
    assert thread._watchdog_timed_out
    assert fake_stream.closed
    assert fake_llm.reset_called
    assert errors == [
        "Inference Watchdog Timeout: Token generation froze for more than 30s. "
        "Inference terminated safely."
    ]


def test_main_window_restores_and_clears_autosave_checkpoint(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    from app.utils.memory_manager import MemoryManager
    from app.utils.session_tree import SessionTree
    import app.ui.main_window as main_window

    class FakeState(QObject):
        state_changed = pyqtSignal(str, object)
        change_workspace_requested = pyqtSignal(int)
        append_to_workbench_input = pyqtSignal(str)
        replace_workbench_input = pyqtSignal(str)
        attach_image_to_workbench = pyqtSignal(str)
        set_workbench_hyperparams = pyqtSignal(dict)
        set_workbench_system_prompt = pyqtSignal(str)

        def __init__(self):
            super().__init__()
            self.memory = MemoryManager(sessions_dir=str(tmp_path))
            self.model_name = "none"
            self.adapter_name = None
            self.generating = False
            self.swarm_running = False

    class FakeSidebar(QWidget):
        workspace_changed = pyqtSignal(int)

        def __init__(self):
            super().__init__()
            self.selected = None

        def select(self, idx):
            self.selected = idx
            self.workspace_changed.emit(idx)

    class FakeStatusBar(QWidget):
        def set_model(self, value):
            self.model = value

        def set_adapter(self, value):
            self.adapter = value

        def set_state(self, *args):
            pass

        def set_context_stats(self, *args):
            pass

        def set_load_stats(self, *args):
            pass

        def set_bridge_status(self, *args):
            pass

    class FakeChatView:
        def __init__(self):
            self._messages = []

        def clear_display(self):
            self._messages = []

        def _render_all(self):
            pass

    class FakeWorkbench(QWidget):
        status_changed = pyqtSignal(str, bool)
        model_changed = pyqtSignal(str)
        adapter_changed = pyqtSignal(str)
        context_stats = pyqtSignal(int, int, int, int)
        appearance_requested = pyqtSignal()

        def __init__(self, state):
            super().__init__()
            self.state = state
            self.chat_history = SessionTree()
            self._hyperparams = {}
            self._thread = None
            self._session_id = "existing"
            self._current_session_file = "existing.json"
            self._chat_view = FakeChatView()

        def _new_session(self):
            pass

        def _save_current_session(self):
            pass

        def _toggle_all_huds(self):
            pass

        def _toggle_reasoning(self):
            pass

        def _toggle_sessions(self):
            pass

        def _toggle_rag_hud(self):
            pass

        def _toggle_context_hud(self):
            pass

        def update_theme(self):
            pass

        def _populate_branches_tree(self):
            self.branches_populated = True

        def _refresh_sessions(self):
            self.sessions_refreshed = True

        def on_close(self):
            pass

    class FakeWorkspace(QWidget):
        adapter_changed = pyqtSignal(str)
        appearance_changed = pyqtSignal()

        def __init__(self, *args, **kwargs):
            super().__init__()

        def set_workbench(self, *args):
            pass

        def _scan_adapters(self):
            pass

    tree = SessionTree()
    tree.add_message("user", "recover this")
    manager = MemoryManager(sessions_dir=str(tmp_path))
    manager.save_autosave_checkpoint(
        tree,
        active_workspace=3,
        model_settings={"model_name": "restored.gguf", "adapter_name": "adapter-a", "hyperparams": {"temperature": 0.2}},
    )

    monkeypatch.setattr(main_window, "AppState", FakeState)
    monkeypatch.setattr(main_window, "Sidebar", FakeSidebar)
    monkeypatch.setattr(main_window, "StatusBar", FakeStatusBar)
    monkeypatch.setattr(main_window, "WorkbenchWorkspace", FakeWorkbench)
    for name in (
        "PromptLabWorkspace",
        "KnowledgeBaseWorkspace",
        "VisionWorkbench",
        "TrainingStudioWorkspace",
        "EvalSuiteWorkspace",
        "SwarmStudioWorkspace",
        "SystemConfigWorkspace",
        "DocsWorkspace",
        "FlywheelStudioWorkspace",
    ):
        monkeypatch.setattr(main_window, name, FakeWorkspace)
    monkeypatch.setattr(main_window.MainWindow, "_setup_shortcuts", lambda self: None)
    monkeypatch.setattr(main_window.MainWindow, "_load_theme_config", lambda self: None)
    monkeypatch.setattr(main_window.MainWindow, "_init_websocket_server", lambda self: None)
    monkeypatch.setattr(main_window.MainWindow, "_init_model", lambda self: None)
    import app.utils.keychain_manager as keychain_manager
    monkeypatch.setattr(keychain_manager, "revoke_tokens", lambda: None)
    monkeypatch.setattr(keychain_manager, "save_cached_token", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window.QTimer, "singleShot", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *args, **kwargs: main_window.QMessageBox.StandardButton.Yes,
    )

    window = main_window.MainWindow()
    window._state.memory = manager
    window._check_autosave_recovery()

    assert not os.path.exists(manager.autosave_path)
    assert window._sidebar.selected == 3
    assert window._workbench.chat_history[0]["content"] == "recover this"
    assert window._workbench._hyperparams["temperature"] == 0.2
    assert window._state.model_name == "restored.gguf"
    assert window._state.adapter_name == "adapter-a"
    assert window._workbench._chat_view._messages[0][1] == "recover this"

    window.close()
    app.processEvents()
