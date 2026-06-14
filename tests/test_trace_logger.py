import gc
import gzip
import os
import sys
import json
import shutil
import tempfile
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.utils.trace_logger as tl
from app.utils.trace_logger import TraceLogger

def test_schema_fields():
    print("Testing TraceLogger schema fields...")
    temp_dir = tempfile.mkdtemp()
    try:
        logger = TraceLogger(log_dir=temp_dir)
        log_file = logger.log_generation(
            compiled_prompt="System rules\nUser message",
            hyperparams={"temperature": 0.7, "top_p": 0.9},
            raw_output="Thought response",
            parsed_thought="Thought",
            parsed_response="response",
            execution_time=2.5,
            rag_context=["chunk1"],
            workflow="code_review",
            template="json_extractor",
            feedback="none",
            model_name="qwen-1.5b",
            adapter_name="lora-1",
            diagnostics={
                "prompt_tokens": 10,
                "prefill_time": 0.5,
                "prefill_tps": 20.0,
                "generation_tokens": 15,
                "generation_time": 2.0,
                "generation_tps": 7.5,
                "total_time": 2.5,
                "total_tps": 10.0,
            }
        )
        
        # Read the logged record
        assert os.path.exists(log_file)
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        record = json.loads(line)
        
        # Verify schema keys
        expected_keys = {
            "id", "session_id", "timestamp", "timing", "model", "adapter",
            "workflow", "template", "hyperparams", "system_prompt",
            "compiled_prompt", "thinking", "response", "raw_output",
            "rag_chunks", "feedback", "corrected_response",
            "gpu_temp_c", "throttle_reasons", "cooling_duration_sec"
        }
        assert set(record.keys()) == expected_keys, f"Missing or extra keys: {record.keys()}"
        
        # Assert values
        assert record["model"] == "qwen-1.5b"
        assert record["adapter"] == "lora-1"
        assert record["workflow"] == "code_review"
        assert record["template"] == "json_extractor"
        assert record["hyperparams"] == {"temperature": 0.7, "top_p": 0.9}
        assert record["timing"]["total_seconds"] == 2.5
        assert record["timing"]["prefill_seconds"] == 0.5
        assert record["timing"]["prefill_tps"] == 20.0
        assert record["timing"]["generation_seconds"] == 2.0
        assert record["timing"]["generation_tps"] == 7.5
        assert record["timing"]["prompt_tokens"] == 10
        assert record["timing"]["generation_tokens"] == 15
        assert record["timing"]["total_tps"] == 10.0
        assert record["thinking"] == "Thought"
        assert record["response"] == "response"
        assert record["rag_chunks"] == ["chunk1"]
        assert record["feedback"] == "none"
        
        # Test updating feedback
        logger.update_last_entry_feedback(feedback="thumbs_up")
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        record = json.loads(line)
        assert record["feedback"] == "thumbs_up"
        
        print("TraceLogger schema fields OK.")
    finally:
        shutil.rmtree(temp_dir)

def test_file_rotation():
    print("Testing TraceLogger rotation logic...")
    temp_dir = tempfile.mkdtemp()
    
    # Save original max bytes
    old_max = tl._MAX_BYTES
    # Set max bytes very small so any entry triggers rotation
    tl._MAX_BYTES = 50 
    
    try:
        logger = TraceLogger(log_dir=temp_dir)
        
        with patch.object(logger, "_archive_log", return_value=None):
            # Write one entry. This file will exceed 50 bytes.
            file1 = logger.log_generation("prompt 1", {}, "raw 1", "thought 1", "resp 1", 1.0)
            
            # Next entry should be written to rotated file
            file2 = logger.log_generation("prompt 2", {}, "raw 2", "thought 2", "resp 2", 1.0)
            
        assert file1 != file2, f"Expected rotation, but both wrote to {file1}"
        assert os.path.exists(file1)
        assert os.path.exists(file2)
        
        # Verify contents of both
        with open(file1, "r") as f:
            r1 = json.loads(f.readline().strip())
        with open(file2, "r") as f:
            r2 = json.loads(f.readline().strip())
            
        assert r1["thinking"] == "thought 1"
        assert r2["thinking"] == "thought 2"
        
        print("TraceLogger rotation OK.")
    finally:
        tl._MAX_BYTES = old_max
        shutil.rmtree(temp_dir)

def test_log_pruning():
    import time
    from unittest.mock import patch
    print("Testing TraceLogger pruning logic...")
    temp_dir = tempfile.mkdtemp()
    
    with patch("app.engine.config_store.get_ui_config", return_value={"log_retention_days": 2}):
        logger = TraceLogger(log_dir=temp_dir)
        
        old_file = os.path.join(temp_dir, "trace_2020-01-01.jsonl")
        new_file = os.path.join(temp_dir, "trace_2026-06-12.jsonl")
        
        with open(old_file, "w") as f:
            f.write("{}\n")
        with open(new_file, "w") as f:
            f.write("{}\n")
            
        now = time.time()
        os.utime(old_file, (now - 10 * 86400, now - 10 * 86400))
        
        logger.prune_logs()
        
        assert not os.path.exists(old_file), "Expected old log to be pruned"
        assert os.path.exists(new_file), "Expected new log to be kept"
        
    shutil.rmtree(temp_dir)
    print("TraceLogger pruning OK.")

def test_cryptographic_memory_zeroing():
    """
    Verify that _zero_bytes() is called on key material inside _archive_log() and
    that the bytearray is fully overwritten with zeros after the call returns.
    """
    pytest.importorskip("cryptography", reason="cryptography package not installed")

    temp_dir = tempfile.mkdtemp()
    archive_dir = tempfile.mkdtemp()
    captured: list[bytearray] = []

    original_zero = TraceLogger._zero_bytes

    def intercepting_zero(ba: bytearray) -> None:
        # Capture the bytearray reference BEFORE the real zeroing runs so we
        # can inspect the same object (in-place mutation) after the call.
        captured.append(ba)
        original_zero(ba)

    try:
        with patch.object(TraceLogger, "_zero_bytes", staticmethod(intercepting_zero)):
            tracer = TraceLogger(log_dir=temp_dir, archive_dir=archive_dir)

            # Write a real JSONL entry so _archive_log() has a non-empty file.
            test_log = os.path.join(temp_dir, "trace_zeroing_test.jsonl")
            with open(test_log, "w", encoding="utf-8") as fh:
                fh.write('{"id":"zero-test","session_id":"s0","timestamp":"2026-06-13T00:00:00+00:00"}\n')

            tracer._archive_log(test_log)

        assert len(captured) >= 1, (
            "_zero_bytes was never called — key material was not sanitized after archival"
        )
        for slot, ba in enumerate(captured):
            assert isinstance(ba, bytearray), \
                f"Slot {slot}: expected bytearray, got {type(ba).__name__}"
            assert len(ba) > 0, f"Slot {slot}: captured bytearray is empty"
            non_zero = [i for i, v in enumerate(ba) if v != 0]
            assert len(non_zero) == 0, (
                f"Slot {slot}: bytearray not fully zeroed — "
                f"{len(non_zero)} non-zero byte(s) at indices {non_zero[:10]}"
                f"{'...' if len(non_zero) > 10 else ''}"
            )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(archive_dir, ignore_errors=True)


def test_decrypted_payload_cleanup():
    """
    Verify that decrypt_to_bytearray() returns a mutable bytearray, that
    _zero_bytes() wipes every byte to zero, and that no external references to
    the sensitive buffer linger after cleanup.
    """
    Fernet = pytest.importorskip(
        "cryptography.fernet", reason="cryptography package not installed"
    ).Fernet

    temp_dir = tempfile.mkdtemp()
    try:
        # ── 1. Build a valid .enc file with a known test key ──────────────────
        test_key = Fernet.generate_key()
        plaintext = b'{"id":"ref-test","thinking":"sensitive reasoning"}\n'
        encrypted = Fernet(test_key).encrypt(gzip.compress(plaintext))

        enc_path = os.path.join(temp_dir, "trace_2026-06-13_cleanup.jsonl.enc")
        with open(enc_path, "wb") as fh:
            fh.write(encrypted)

        # ── 2. Decrypt to a mutable bytearray ────────────────────────────────
        result = TraceLogger.decrypt_to_bytearray(enc_path, test_key)
        assert isinstance(result, bytearray), \
            "decrypt_to_bytearray must return a bytearray"
        assert len(result) > 0, "Decrypted bytearray is empty"
        assert bytes(result) == plaintext, \
            "Decrypted content does not match the original plaintext"

        # ── 3. Verify no unexpected external references before zeroing ────────
        # sys.getrefcount() always adds 1 for its own argument.
        # Expected: 2 = local variable 'result' + getrefcount argument.
        gc.collect()
        ref_count = sys.getrefcount(result)
        assert ref_count <= 2, (
            f"Reference leak detected before zeroing: refcount={ref_count}, "
            f"expected ≤ 2 (local var + getrefcount arg)"
        )

        # ── 4. Zero the payload in-place ──────────────────────────────────────
        TraceLogger._zero_bytes(result)

        # ── 5. Every byte must be 0x00 ────────────────────────────────────────
        non_zero = [i for i, b in enumerate(result) if b != 0]
        assert len(non_zero) == 0, (
            f"Payload not fully zeroed: {len(non_zero)} non-zero byte(s) remain "
            f"at indices {non_zero[:10]}{'...' if len(non_zero) > 10 else ''}"
        )

        # ── 6. No referrers outside the current stack frame ──────────────────
        # gc.get_referrers() returns all objects that directly reference 'result'.
        # The only legitimate referrer is the local-variables dict of this frame.
        gc.collect()
        referrers = gc.get_referrers(result)
        external = [
            r for r in referrers
            if not (isinstance(r, dict) and "result" in r)
        ]
        assert len(external) == 0, (
            f"Unexpected referrers to decrypted bytearray after zeroing: {external}"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_schema_fields()
    test_file_rotation()
    test_log_pruning()
    test_cryptographic_memory_zeroing()
    test_decrypted_payload_cleanup()
    print("All trace logger unit tests PASSED!")
