"""
Tests for InferenceService — thread selection, callback routing, and lifecycle.

PyQt6 signals require a running QApplication; `qt_test_helper` creates one
before any module is imported.
"""

from __future__ import annotations

import pytest

import tests.qt_test_helper  # noqa: F401 — side-effect: creates QApplication

from PyQt6.QtCore import QCoreApplication, Qt, QThread, pyqtSignal

from app.engine.inference_service import InferenceService


# ── Fake thread classes ───────────────────────────────────────────────────────

class _FakeLLMThread(QThread):
    """Emits a complete single-shot cycle synchronously in run()."""

    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)
    generation_finished = pyqtSignal(str, str, bool, bool, dict)
    live_stats = pyqtSignal(int, float)
    reload_notice = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    context_stats = pyqtSignal(int, int, int, int)
    rag_context_used = pyqtSignal(list)
    tool_call_started = pyqtSignal(str, str)
    status_update = pyqtSignal(str, bool)

    THOUGHT = "thinking…"
    RESPONSE = "hello world"
    DIAGS = {"generation_tokens": 2}

    def __init__(self, **kwargs):
        super().__init__()
        self.init_kwargs = kwargs
        self._should_error = kwargs.pop("_should_error", False)

    def run(self):
        if self._should_error:
            self.error_occurred.emit("boom")
            return
        self.new_thought_token.emit(self.THOUGHT)
        self.new_chat_token.emit("hello ")
        self.new_chat_token.emit("world")
        self.live_stats.emit(2, 42.0)
        self.generation_finished.emit(
            self.THOUGHT, self.RESPONSE, False, False, self.DIAGS
        )


class _FakeAgenticThread(QThread):
    """Emits a complete agentic-loop cycle synchronously in run()."""

    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)
    iteration_finished = pyqtSignal(int, str, str, dict)
    live_stats = pyqtSignal(int, float)
    loop_finished = pyqtSignal(int)
    reload_notice = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    context_stats = pyqtSignal(int, int, int, int)
    status_update = pyqtSignal(str, bool)

    RESPONSE = "agentic response"

    def __init__(self, **kwargs):
        super().__init__()
        self.init_kwargs = kwargs
        # Simulate what AgenticThread stores after running
        self.chat_history = [{"role": "assistant", "content": self.RESPONSE}]

    def run(self):
        self.new_chat_token.emit(self.RESPONSE)
        self.loop_finished.emit(1)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def service(monkeypatch):
    """Return an InferenceService with thread classes replaced by fakes."""
    import app.engine.inference_service as svc_mod

    monkeypatch.setattr(svc_mod, "LLMThread", _FakeLLMThread)
    monkeypatch.setattr(svc_mod, "AgenticThread", _FakeAgenticThread)
    return InferenceService(state=None)


def _drain(ms: int = 200) -> None:
    """Process pending Qt events so signal handlers execute."""
    QCoreApplication.processEvents()
    from PyQt6.QtCore import QTimer

    QTimer.singleShot(ms, QCoreApplication.instance().quit)
    QCoreApplication.instance().exec()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_single_shot_creates_llm_thread(service, monkeypatch):
    """run_generation without agentic flag creates an LLMThread."""
    import app.engine.inference_service as svc_mod

    created = []
    _OrigFake = svc_mod.LLMThread

    class _Spy(_OrigFake):
        def __init__(self, **kw):
            created.append(type(self).__name__)
            super().__init__(**kw)

    monkeypatch.setattr(svc_mod, "LLMThread", _Spy)

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
    )
    t.wait(2000)
    assert created == ["_Spy"]


def test_agentic_flag_creates_agentic_thread(service, monkeypatch):
    """agentic=True routes to AgenticThread."""
    import app.engine.inference_service as svc_mod

    created = []
    _OrigFake = svc_mod.AgenticThread

    class _Spy(_OrigFake):
        def __init__(self, **kw):
            created.append(type(self).__name__)
            super().__init__(**kw)

    monkeypatch.setattr(svc_mod, "AgenticThread", _Spy)

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        agentic=True,
    )
    t.wait(2000)
    assert created == ["_Spy"]


def test_hyperparams_agentic_flag_selects_agentic_thread(service, monkeypatch):
    """hyperparams['agentic_loop_enabled']=True also routes to AgenticThread."""
    import app.engine.inference_service as svc_mod

    created = []
    _OrigFake = svc_mod.AgenticThread

    class _Spy(_OrigFake):
        def __init__(self, **kw):
            created.append(type(self).__name__)
            super().__init__(**kw)

    monkeypatch.setattr(svc_mod, "AgenticThread", _Spy)

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={"agentic_loop_enabled": True},
    )
    t.wait(2000)
    assert created == ["_Spy"]


_DC = Qt.ConnectionType.DirectConnection


def test_on_token_cb_receives_chat_tokens(service):
    """on_token_cb is called for every new_chat_token emission."""
    tokens: list[str] = []

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        on_token_cb=tokens.append,
        connection_type=_DC,
    )
    t.wait(2000)

    assert tokens == ["hello ", "world"]


def test_on_thought_token_cb_receives_thought_tokens(service):
    """on_thought_token_cb is called for every new_thought_token emission."""
    thoughts: list[str] = []

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        on_thought_token_cb=thoughts.append,
        connection_type=_DC,
    )
    t.wait(2000)

    assert thoughts == [_FakeLLMThread.THOUGHT]


def test_on_finished_cb_called_with_normalised_args_for_llm(service):
    """on_finished_cb receives (thought, response, diagnostics) for LLMThread."""
    finished: list[tuple] = []

    def _cb(thought, response, diagnostics):
        finished.append((thought, response, diagnostics))

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        on_finished_cb=_cb,
        connection_type=_DC,
    )
    t.wait(2000)

    assert len(finished) == 1
    thought, response, diags = finished[0]
    assert response == _FakeLLMThread.RESPONSE
    assert thought == _FakeLLMThread.THOUGHT
    assert diags == _FakeLLMThread.DIAGS


def test_on_finished_cb_called_for_agentic_thread(service):
    """on_finished_cb receives (thought, response, {}) for AgenticThread."""
    finished: list[tuple] = []

    def _cb(thought, response, diagnostics):
        finished.append((thought, response, diagnostics))

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        agentic=True,
        on_finished_cb=_cb,
        connection_type=_DC,
    )
    t.wait(2000)

    assert len(finished) == 1
    _thought, response, diags = finished[0]
    assert response == _FakeAgenticThread.RESPONSE
    assert diags == {}


def test_on_error_cb_called_on_error(service, monkeypatch):
    """on_error_cb is called when the thread emits error_occurred."""
    import app.engine.inference_service as svc_mod

    class _ErrorThread(_FakeLLMThread):
        def run(self):
            self.error_occurred.emit("boom")

    monkeypatch.setattr(svc_mod, "LLMThread", _ErrorThread)

    errors: list[str] = []
    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        on_error_cb=errors.append,
        connection_type=_DC,
    )
    t.wait(2000)

    assert errors == ["boom"]


def test_on_live_stats_cb_called(service):
    """on_live_stats_cb is called when the thread emits live_stats."""
    stats: list[tuple] = []

    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
        on_live_stats_cb=lambda n, tps: stats.append((n, tps)),
        connection_type=_DC,
    )
    t.wait(2000)

    assert stats == [(2, 42.0)]


def test_thread_added_to_active_set_while_running(service):
    """The thread is in _active_threads while running and removed after finish."""
    captured_mid_run: list[bool] = []

    class _TrackThread(_FakeLLMThread):
        def run(self):
            # Called on worker thread; DirectConnection means discard() will also
            # run on the worker thread (via finished signal) before wait() returns.
            captured_mid_run.append(self in service._active_threads)
            super().run()

    import app.engine.inference_service as svc_mod
    original = svc_mod.LLMThread
    svc_mod.LLMThread = _TrackThread
    try:
        t = service.run_generation(
            prompt="hi",
            system_prompt="sys",
            chat_history=[],
            hyperparams={},
            connection_type=_DC,
        )
        t.wait(2000)
        # With DirectConnection, discard() ran on the worker thread synchronously
        # when `finished` was emitted — guaranteed to have executed before wait() returns.
        in_set_after_wait = t in service._active_threads
    finally:
        svc_mod.LLMThread = original

    assert captured_mid_run == [True], "Thread must be in _active_threads during run()"
    assert not in_set_after_wait, "Thread must be removed from _active_threads after finished"


def test_thread_is_already_started_on_return(service):
    """run_generation must start the thread before returning the handle."""
    t = service.run_generation(
        prompt="hi",
        system_prompt="sys",
        chat_history=[],
        hyperparams={},
    )
    # isRunning() may briefly be False if run() already finished; isFinished() covers it
    started = t.isRunning() or t.isFinished()
    t.wait(2000)
    assert started, "Thread must be started (running or finished) when returned"
