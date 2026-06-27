"""Unit tests for Karl's error, failure, and edge case paths."""

from __future__ import annotations

import os
import json
import time
import pytest
from unittest.mock import patch, MagicMock

from app.engine.model_loader import ModelLoader
from app.engine.task_supervisor import TaskSupervisor, TaskStatus
from core.cognitive_parser import parse_thought_stream
from app.utils.trace_logger import TraceLogger


# ── 1. ModelLoader Behavior on Missing or Corrupted GGUF Files ───────────────

def test_model_loader_missing_file(monkeypatch):
    """Verify ModelLoader raises FileNotFoundError when GGUF files are missing."""
    # We will mock os.path.exists to return False specifically for GGUF files
    orig_exists = os.path.exists
    def mock_exists(path):
        if str(path).endswith(".gguf"):
            return False
        return orig_exists(path)
    
    monkeypatch.setattr(os.path, "exists", mock_exists)
    
    with pytest.raises(FileNotFoundError, match="No model at"):
        ModelLoader.preflight_model_load("data/models/non-existent-model.gguf")


def test_model_loader_corrupted_file(tmp_path, monkeypatch):
    """Verify ModelLoader raises an exception when loading a corrupted GGUF file."""
    corrupted_file = tmp_path / "corrupted_model.gguf"
    corrupted_file.write_bytes(b"invalid GGUF format signature")
    
    # Mock llama_cpp.Llama constructor to simulate C-level load failure
    import llama_cpp
    def mock_llama(*args, **kwargs):
        if kwargs.get("model_path") == str(corrupted_file):
            raise ValueError("Failed to load model: invalid GGUF signature")
        return None
        
    monkeypatch.setattr(llama_cpp, "Llama", mock_llama)
    
    with pytest.raises((OSError, ValueError, RuntimeError)):
        ModelLoader.acquire_instance(model_path=str(corrupted_file))


# ── 2. Graceful Recovery & Resource Cleanup during Thread Crashes ───────────

def test_llm_thread_crash_recovery():
    """Verify LLMThread crash transitions TaskSupervisor task to ERROR and unlocks ModelLoader."""
    from app.engine.llm_thread import LLMThread
    
    # Mock acquire/unlock and force an exception mid-run
    with patch("app.engine.model_loader.ModelLoader.acquire_instance") as mock_acquire, \
         patch("app.engine.model_loader.ModelLoader.unlock_instance") as mock_unlock, \
         patch.object(LLMThread, "_trim_history", side_effect=RuntimeError("Simulated trim crash")):
         
        mock_acquire.return_value = MagicMock()
        
        thread = LLMThread(
            system_prompt="system",
            chat_history=[],
            hyperparams={"max_tokens": 8},
        )
        
        # Run thread synchronously (calling run() directly)
        thread.run()
        
        # Verify ModelLoader unlock was called exactly once in the finally block
        mock_unlock.assert_called_once()
        
        # Verify task registry record
        supervisor = TaskSupervisor.instance()
        task_id = thread.task_id
        record = supervisor.get(task_id)
        assert record is not None
        assert record.status == TaskStatus.ERROR
        assert "Simulated trim crash" in record.error


# ── 3. Introspective Parser Behavior on Empty Outputs or Malformed Tags ──────

def test_introspective_parser_empty_and_malformed():
    """Verify parse_thought_stream handles empty and malformed tags gracefully."""
    # 1. Empty input
    t, r = parse_thought_stream("")
    assert t == ""
    assert r == ""
    
    # 2. Open tag only, no content
    t, r = parse_thought_stream("<think>")
    assert t == ""
    assert r == ""
    
    # 3. Open tag only, with content
    t, r = parse_thought_stream("<think>thought content")
    assert t == "thought content"
    assert r == ""
    
    # 4. Partial open tag (does not match <think> state machine open)
    t, r = parse_thought_stream("<thi")
    assert t == ""
    assert r == "<thi"
    
    # 5. Malformed closing tag
    t, r = parse_thought_stream("<think>thought content</thin")
    assert t == "thought content</thin"
    assert r == ""


# ── 4. Task Supervisor Timeout Handling during Forced Cancellations ──────────

def test_task_supervisor_cancel_timeout():
    """Verify cancel timeout logic in TaskSupervisor teardown simulation."""
    supervisor = TaskSupervisor.instance()
    
    class SlowCancellable:
        def request_stop(self):
            # Simulate a thread that takes some time to stop or ignores cancel
            pass
            
    task_id = supervisor.register("slow_task", cancellable=SlowCancellable())
    
    # Trigger cancellation
    cancelled = supervisor.cancel(task_id)
    assert cancelled is True
    assert supervisor.status(task_id) == TaskStatus.CANCELLING
    
    # Simulate MainWindow closeEvent cancellation wait loop with a timeout
    start_wait = time.perf_counter()
    timeout_occurred = False
    
    while supervisor.active_tasks():
        if time.perf_counter() - start_wait >= 0.1: # Short timeout for test
            timeout_occurred = True
            break
        time.sleep(0.01)
        
    assert timeout_occurred is True
    assert supervisor.status(task_id) == TaskStatus.CANCELLING # Task remains in CANCELLING, did not block indefinitely


# ── 5. Trace Logger Behavior on Corrupted JSONL Lines ────────────────────────

def test_trace_logger_corrupted_jsonl(tmp_path):
    """Verify read_jsonl skips malformed/corrupted lines gracefully."""
    log_file = tmp_path / "corrupted_trace.jsonl"
    
    # Write valid, invalid (malformed JSON), empty, and valid records
    valid_rec = {
        "schema_version": 1,
        "id": "test-uuid-123",
        "session_id": "session-123",
        "timestamp": "2026-06-26T20:00:00Z",
        "model": "model.gguf",
        "feedback": "none",
        "thinking": "thought",
        "response": "resp"
    }
    
    log_file.write_text(
        json.dumps(valid_rec) + "\n" +
        "this is not valid json - corrupted line\n" +
        "\n" + # empty line
        json.dumps(valid_rec) + "\n",
        encoding="utf-8"
    )
    
    # Read traces
    records = TraceLogger.read_jsonl(str(log_file))
    
    # Only the two valid records should be returned, malformed ones skipped
    assert len(records) == 2
    assert records[0]["id"] == "test-uuid-123"
    assert records[1]["id"] == "test-uuid-123"
