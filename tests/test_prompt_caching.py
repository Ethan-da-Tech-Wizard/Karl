"""
Tests for KV prompt-cache plumbing in Karl's inference engine.

Unit tests (no real model required) cover:
  - LlamaRAMCache is attached to the Llama instance after load
  - VRAM guard disables cache when free VRAM < 500 MB
  - kv_cache_stats returns correct hit/miss fields
  - reset_instance calls set_cache(None) to free cache memory
  - n_batch and flash_attn are present in _attempt_load kwargs
  - Cache log writes valid JSON to kv_cache.jsonl

Integration test (requires a real GGUF model, marked slow):
  - Second query on a shared 1000-token system prefix achieves ≥ 3× TTFT speedup
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from collections import OrderedDict
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_fake_llm(tokens_in_cache: int = 0) -> MagicMock:
    """
    Build a mock Llama instance with an attached LlamaRAMCache.

    *tokens_in_cache* controls how long the prefix that lives in the cache is.
    If 0, the cache is empty (cold start / cache miss scenario).
    """
    from llama_cpp import LlamaRAMCache

    llm = MagicMock(name="FakeLlama")

    # tokenize() returns a list of ints — one per character for simplicity.
    llm.tokenize.side_effect = lambda b, add_bos=False: list(b)

    # Attach a real (empty or seeded) LlamaRAMCache.
    cache = LlamaRAMCache(capacity_bytes=64 * (1 << 20))

    if tokens_in_cache > 0:
        # Seed the cache with a fake state keyed by the first N tokens.
        fake_state = MagicMock()
        fake_state.llama_state_size = 1024
        fake_state.input_ids = MagicMock()
        fake_state.input_ids.tolist.return_value = list(range(tokens_in_cache))
        cache.cache_state[tuple(range(tokens_in_cache))] = fake_state

    llm.cache = cache
    return llm


def _model_available() -> bool:
    return os.path.exists("data/models/deepseek-r1-1.5b.gguf")


# ── kv_cache_stats unit tests ─────────────────────────────────────────────────

class TestKvCacheStats:
    def test_no_cache_attached(self):
        from app.engine.kv_cache import kv_cache_stats

        llm = MagicMock()
        llm.cache = None
        stats = kv_cache_stats(llm, "hello world")
        assert stats == {"cache_enabled": False}

    def test_cold_cache_miss(self):
        from app.engine.kv_cache import kv_cache_stats

        llm = _make_fake_llm(tokens_in_cache=0)
        prompt = "hello"
        stats = kv_cache_stats(llm, prompt)
        assert stats["cache_enabled"] is True
        assert stats["cache_hit"] is False
        assert stats["tokens_from_cache"] == 0
        assert stats["tokens_to_eval"] == len(prompt.encode())  # 5 tokens

    def test_full_cache_hit(self):
        from app.engine.kv_cache import kv_cache_stats

        prompt = "hello"
        prompt_bytes = prompt.encode()  # 5 bytes → 5 mock tokens
        llm = _make_fake_llm(tokens_in_cache=len(prompt_bytes))
        # The cache state key is [0,1,2,3,4]; prompt tokens are [104,101,108,108,111]
        # They won't match because our mock tokenizer returns raw bytes.
        # Patch to use matching tokens instead.
        llm.tokenize.side_effect = lambda b, add_bos=False: list(range(len(b)))
        stats = kv_cache_stats(llm, prompt)
        assert stats["cache_enabled"] is True
        assert stats["cache_hit"] is True
        assert stats["tokens_from_cache"] > 0
        assert stats["tokens_from_cache"] + stats["tokens_to_eval"] == len(prompt_bytes)

    def test_partial_cache_hit(self):
        from app.engine.kv_cache import kv_cache_stats

        # Cache has 3 tokens; prompt has 5 tokens — partial prefix hit.
        llm = _make_fake_llm(tokens_in_cache=3)
        llm.tokenize.side_effect = lambda b, add_bos=False: list(range(len(b)))
        stats = kv_cache_stats(llm, "hello")  # 5 chars → 5 tokens
        assert stats["cache_enabled"] is True
        assert stats["cache_hit"] is True
        assert stats["tokens_from_cache"] == 3
        assert stats["tokens_to_eval"] == 2

    def test_exception_does_not_raise(self):
        from app.engine.kv_cache import kv_cache_stats

        llm = MagicMock()
        llm.cache = MagicMock()
        llm.tokenize.side_effect = RuntimeError("tokenizer broken")
        stats = kv_cache_stats(llm, "prompt")
        # Must return a dict, never raise
        assert isinstance(stats, dict)
        assert "error" in stats or stats.get("cache_hit") is None


# ── log_cache_stats unit tests ────────────────────────────────────────────────

class TestLogCacheStats:
    def test_writes_valid_jsonl(self):
        from app.engine.kv_cache import log_cache_stats

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "kv_cache.jsonl")
            with patch("app.engine.kv_cache._KV_CACHE_LOG", log_path):
                log_cache_stats(
                    {"cache_enabled": True, "cache_hit": False,
                     "tokens_from_cache": 0, "tokens_to_eval": 50, "ttft_ms": 142.0},
                    "20260626_120000_000000",
                )
            assert os.path.exists(log_path)
            with open(log_path) as fh:
                entry = json.loads(fh.readline())
            assert entry["ts"] == "20260626_120000_000000"
            assert entry["cache_enabled"] is True
            assert entry["ttft_ms"] == 142.0

    def test_appends_multiple_entries(self):
        from app.engine.kv_cache import log_cache_stats

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "kv_cache.jsonl")
            with patch("app.engine.kv_cache._KV_CACHE_LOG", log_path):
                log_cache_stats({"cache_hit": False}, "ts1")
                log_cache_stats({"cache_hit": True},  "ts2")
            with open(log_path) as fh:
                lines = [json.loads(l) for l in fh if l.strip()]
            assert len(lines) == 2
            assert lines[0]["ts"] == "ts1"
            assert lines[1]["ts"] == "ts2"

    def test_silently_ignores_io_error(self):
        from app.engine.kv_cache import log_cache_stats

        with patch("app.engine.kv_cache._KV_CACHE_LOG", "/nonexistent/deeply/nested/path.jsonl"):
            # Must not raise
            log_cache_stats({"cache_hit": True}, "ts")


# ── ModelLoader._attach_kv_cache unit tests ───────────────────────────────────

class TestAttachKvCache:
    def setup_method(self):
        from app.engine.model_loader import ModelLoader
        # Snapshot class state; restore after each test.
        self._orig_instance = ModelLoader._instance
        self._orig_enabled  = ModelLoader._cache_enabled

    def teardown_method(self):
        from app.engine.model_loader import ModelLoader
        ModelLoader._instance     = self._orig_instance
        ModelLoader._cache_enabled = self._orig_enabled

    def test_attaches_ram_cache_when_vram_sufficient(self):
        from app.engine.model_loader import ModelLoader
        from llama_cpp import LlamaRAMCache

        fake_llm = MagicMock(name="FakeLlama")
        ModelLoader._instance = fake_llm
        ModelLoader._cache_enabled = True

        with patch.object(ModelLoader, "_free_vram_mb", return_value=4096.0):
            ModelLoader._attach_kv_cache()

        # set_cache should have been called once with a LlamaRAMCache instance
        assert fake_llm.set_cache.call_count == 1
        cache_arg = fake_llm.set_cache.call_args[0][0]
        assert isinstance(cache_arg, LlamaRAMCache)

    def test_vram_guard_skips_cache_below_500mb(self):
        from app.engine.model_loader import ModelLoader

        fake_llm = MagicMock(name="FakeLlama")
        ModelLoader._instance = fake_llm
        ModelLoader._cache_enabled = True

        with patch.object(ModelLoader, "_free_vram_mb", return_value=490.0):
            ModelLoader._attach_kv_cache()

        fake_llm.set_cache.assert_not_called()

    def test_cache_disabled_flag_skips_attachment(self):
        from app.engine.model_loader import ModelLoader

        fake_llm = MagicMock(name="FakeLlama")
        ModelLoader._instance = fake_llm
        ModelLoader._cache_enabled = False

        with patch.object(ModelLoader, "_free_vram_mb", return_value=8192.0):
            ModelLoader._attach_kv_cache()

        fake_llm.set_cache.assert_not_called()

    def test_capacity_clamped_to_2gb_max(self):
        from app.engine.model_loader import ModelLoader
        from llama_cpp import LlamaRAMCache

        fake_llm = MagicMock(name="FakeLlama")
        ModelLoader._instance = fake_llm
        ModelLoader._cache_enabled = True

        # 100 GB free — 25% would be 25 GB, but cap is 2 GB.
        with patch.object(ModelLoader, "_free_vram_mb", return_value=100_000.0):
            ModelLoader._attach_kv_cache()

        cache_arg = fake_llm.set_cache.call_args[0][0]
        assert isinstance(cache_arg, LlamaRAMCache)
        assert cache_arg.capacity_bytes == 2 * (1 << 30)

    def test_capacity_floored_at_256mb_min(self):
        from app.engine.model_loader import ModelLoader
        from llama_cpp import LlamaRAMCache

        fake_llm = MagicMock(name="FakeLlama")
        ModelLoader._instance = fake_llm
        ModelLoader._cache_enabled = True

        # 600 MB free: 25% = 150 MB < 256 MB floor → should clamp up to 256 MB.
        with patch.object(ModelLoader, "_free_vram_mb", return_value=600.0):
            ModelLoader._attach_kv_cache()

        cache_arg = fake_llm.set_cache.call_args[0][0]
        assert cache_arg.capacity_bytes == 256 * (1 << 20)


# ── ModelLoader.reset_instance clears cache ───────────────────────────────────

class TestResetClearsCache:
    def test_set_cache_none_called_on_reset(self):
        from app.engine.model_loader import ModelLoader

        orig_instance     = ModelLoader._instance
        orig_count        = ModelLoader._active_generation_count
        orig_locked       = ModelLoader._instance_locked
        orig_model_path   = ModelLoader._model_path
        orig_active_adapt = ModelLoader._active_adapter

        try:
            fake_llm = MagicMock(name="FakeLlama")
            fake_llm.close = MagicMock()
            ModelLoader._instance = fake_llm
            ModelLoader._active_generation_count = 0
            ModelLoader._instance_locked = False
            ModelLoader._model_path = "data/models/test.gguf"
            ModelLoader._active_adapter = None

            ModelLoader.reset_instance()

            # set_cache(None) must be called before close()
            calls = fake_llm.mock_calls
            set_cache_idx = next(
                (i for i, c in enumerate(calls) if c == call.set_cache(None)), None
            )
            close_idx = next(
                (i for i, c in enumerate(calls) if c == call.close()), None
            )
            assert set_cache_idx is not None, "set_cache(None) was not called"
            assert close_idx is not None, "close() was not called"
            assert set_cache_idx < close_idx, "set_cache(None) must precede close()"
        finally:
            ModelLoader._instance                = orig_instance
            ModelLoader._active_generation_count = orig_count
            ModelLoader._instance_locked         = orig_locked
            ModelLoader._model_path              = orig_model_path
            ModelLoader._active_adapter          = orig_active_adapt


# ── n_batch / flash_attn in kwargs ────────────────────────────────────────────

class TestAttemptLoadKwargs:
    """
    Verify that _attempt_load (the nested function in get_instance) passes
    n_batch, n_ubatch, and flash_attn to the Llama constructor.

    We intercept the Llama() constructor call so no model file is needed.
    """

    def test_n_batch_and_flash_attn_passed_to_llama(self):
        from app.engine.model_loader import ModelLoader

        orig_instance   = ModelLoader._instance
        orig_locked     = ModelLoader._instance_locked
        orig_count      = ModelLoader._active_generation_count
        orig_model_path = ModelLoader._model_path
        orig_adapter    = ModelLoader._active_adapter
        orig_offloaded  = ModelLoader._adapter_offloaded

        captured_kwargs: list[dict] = []

        def fake_llama(**kw):
            captured_kwargs.append(kw)
            raise RuntimeError("stop after first constructor call")

        try:
            ModelLoader._instance                = None
            ModelLoader._instance_locked         = False
            ModelLoader._active_generation_count = 0
            ModelLoader._model_path              = None
            ModelLoader._active_adapter          = None
            ModelLoader._adapter_offloaded       = False

            # Patch Llama constructor, resolve_model_path, preflight, and
            # hardware_scout so get_instance() reaches _attempt_load.
            with patch("app.engine.model_loader.Llama", side_effect=fake_llama), \
                 patch.object(ModelLoader, "_resolve_model_path",
                              return_value="data/models/deepseek-r1-1.5b.gguf"), \
                 patch.object(ModelLoader, "preflight_model_load", return_value=None), \
                 patch("app.engine.model_loader.get_hardware_profile",
                       return_value={"gpu_list": []}), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)):
                try:
                    ModelLoader.get_instance(model_path="data/models/deepseek-r1-1.5b.gguf")
                except (RuntimeError, MemoryError, OSError):
                    # Any load failure is expected — we only need captured_kwargs.
                    pass
        finally:
            ModelLoader._instance                = orig_instance
            ModelLoader._instance_locked         = orig_locked
            ModelLoader._active_generation_count = orig_count
            ModelLoader._model_path              = orig_model_path
            ModelLoader._active_adapter          = orig_adapter
            ModelLoader._adapter_offloaded       = orig_offloaded

        assert captured_kwargs, "Llama() was never called"
        kw = captured_kwargs[0]
        assert "n_batch" in kw,    "n_batch missing from Llama() kwargs"
        assert kw["n_batch"] == 512
        assert "n_ubatch" in kw,   "n_ubatch missing from Llama() kwargs"
        assert kw["flash_attn"] is True


# ── Integration: TTFT speedup with shared prefix ─────────────────────────────

@pytest.mark.integration
@pytest.mark.model
@pytest.mark.skipif(not _model_available(), reason="Requires data/models/deepseek-r1-1.5b.gguf")
def test_ttft_speedup_with_shared_prefix():
    """
    Two consecutive completions sharing a ~1000-token system prefix.
    The second call's TTFT must be at least 3× faster than the first.

    This verifies that LlamaRAMCache is actually restoring KV state and
    skipping prompt re-evaluation.
    """
    from llama_cpp import Llama, LlamaRAMCache

    model_path = "data/models/deepseek-r1-1.5b.gguf"
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,
        n_gpu_layers=-1,
        n_batch=512,
        flash_attn=True,
        verbose=False,
    )
    llm.set_cache(LlamaRAMCache(capacity_bytes=512 * (1 << 20)))

    # Build a ~1000-token shared prefix using the model's actual tokenizer.
    # Token density varies by GGUF/tokenizer, so grow the prefix until the
    # invariant the test needs is true instead of relying on a one-shot estimate.
    word = "The quick brown fox jumps over the lazy dog. "
    repeat_count = 1
    while True:
        system_prefix = (
            "<|im_start|>system\n"
            + (word * repeat_count)
            + "<|im_end|>\n<|im_start|>user\nWhat is 2 + 2?<|im_end|>\n<|im_start|>assistant\n"
        )
        prompt_tokens = len(llm.tokenize(system_prefix.encode()))
        if prompt_tokens >= 900:
            break
        repeat_count += 8

    assert prompt_tokens >= 900, f"Prefix too short: {prompt_tokens} tokens"

    def _first_token_latency(prompt: str) -> float:
        t0 = time.perf_counter()
        first = True
        for chunk in llm(prompt, max_tokens=1, stream=True, temperature=0.0, echo=False):
            if first and chunk.get("choices", [{}])[0].get("text"):
                return time.perf_counter() - t0
            first = False
        return time.perf_counter() - t0

    cold_ttft = _first_token_latency(system_prefix)

    # Second call — same prefix, should hit cache.
    warm_ttft = _first_token_latency(system_prefix)

    speedup = cold_ttft / warm_ttft if warm_ttft > 0 else float("inf")
    assert speedup >= 3.0, (
        f"Expected ≥3× TTFT speedup on cached prefix; "
        f"got {speedup:.1f}× (cold={cold_ttft*1000:.0f}ms, warm={warm_ttft*1000:.0f}ms)"
    )


@pytest.mark.integration
@pytest.mark.model
@pytest.mark.skipif(not _model_available(), reason="Requires data/models/deepseek-r1-1.5b.gguf")
def test_cached_output_matches_noncached_at_zero_temperature():
    """
    At temperature=0, cached and non-cached runs must produce identical output.
    """
    from llama_cpp import Llama, LlamaRAMCache

    model_path = "data/models/deepseek-r1-1.5b.gguf"
    prompt = "<|im_start|>user\nWhat is the capital of France?<|im_end|>\n<|im_start|>assistant\n"

    llm_no_cache = Llama(model_path=model_path, n_ctx=512, n_gpu_layers=-1, verbose=False)
    llm_cached   = Llama(model_path=model_path, n_ctx=512, n_gpu_layers=-1, verbose=False)
    llm_cached.set_cache(LlamaRAMCache(capacity_bytes=64 * (1 << 20)))

    def _generate(llm: Llama) -> str:
        result = llm(prompt, max_tokens=20, temperature=0.0, echo=False)
        return result["choices"][0]["text"].strip()

    out_no_cache   = _generate(llm_no_cache)
    _generate(llm_cached)          # warm the cache
    out_cached     = _generate(llm_cached)

    assert out_no_cache == out_cached, (
        f"Output mismatch at temp=0:\n  no-cache: {out_no_cache!r}\n  cached:   {out_cached!r}"
    )
