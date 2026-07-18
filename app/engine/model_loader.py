import json
import logging
import os
import inspect
import threading
import multiprocessing
import time
from llama_cpp import Llama, LlamaRAMCache

from app.engine import config_store
from core.hardware_scout import get_hardware_profile


logger = logging.getLogger("karl.model_loader")


class ModelMemoryError(RuntimeError):
    """Raised when a requested GGUF load exceeds Karl's local memory guard."""

    def __init__(self, message: str, details: dict):
        """Store a user-facing message plus structured memory-plan details."""
        super().__init__(message)
        self.details = details


class CircuitBreakerOpenException(RuntimeError):
    """Raised when model loading is temporarily blocked after repeated failures."""

    MESSAGE = (
        "Inference engine is temporarily locked (Circuit Breaker Tripped). "
        "VRAM or system memory is exhausted. Wait 30 seconds for the system "
        "to cool down before trying again."
    )

    def __init__(self, message: str | None = None):
        """Create a circuit-open error with Karl's standard recovery message."""
        super().__init__(message or self.MESSAGE)


class ModelCircuitBreaker:
    """Stateful guard that blocks repeated expensive model-load failures.

    The breaker starts CLOSED, trips OPEN after failure_threshold terminal
    failures, then allows one HALF_OPEN recovery attempt after cooldown_duration
    seconds. OPEN calls raise CircuitBreakerOpenException before the Llama
    constructor is invoked.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_duration: float = 30.0,
        clock=None,
    ):
        """Initialize breaker thresholds and optional monotonic clock."""
        self.failure_threshold = failure_threshold
        self.cooldown_duration = cooldown_duration
        self._clock = clock or time.monotonic
        self.state = self.CLOSED
        self.consecutive_failures = 0
        self.cooldown_expiration: float | None = None

    def before_call(self) -> None:
        """Validate that a new load attempt may proceed.

        Raises CircuitBreakerOpenException while the breaker is OPEN and the
        cooldown has not expired. Transitions OPEN to HALF_OPEN after cooldown.
        """
        if self.state != self.OPEN:
            return

        now = self._clock()
        if self.cooldown_expiration is not None and now >= self.cooldown_expiration:
            self.state = self.HALF_OPEN
            return

        raise CircuitBreakerOpenException()

    def record_success(self) -> None:
        """Reset the breaker to CLOSED after a successful load."""
        self.state = self.CLOSED
        self.consecutive_failures = 0
        self.cooldown_expiration = None

    def record_failure(self, exc: BaseException | None = None) -> None:
        """Record a terminal load failure and trip OPEN when threshold is met."""
        if self.state == self.HALF_OPEN:
            self._trip()
            return

        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self._trip()

    def reset(self) -> None:
        """Manually reset breaker state and failure counters."""
        self.state = self.CLOSED
        self.consecutive_failures = 0
        self.cooldown_expiration = None

    def _trip(self) -> None:
        self.state = self.OPEN
        self.cooldown_expiration = self._clock() + self.cooldown_duration

    def get_state(self) -> str:
        """Return the current circuit breaker state (CLOSED / OPEN / COOLDOWN / HALF_OPEN)."""
        if self.state == self.OPEN:
            now = self._clock()
            if self.cooldown_expiration is not None and now >= self.cooldown_expiration:
                return self.HALF_OPEN
            return "COOLDOWN"
        return self.state



class _LlamaDraftModelAdapter:
    """Compatibility marker for speculative draft-model integration."""

    def __init__(self, draft_model):
        self.draft_model = draft_model


class ModelLoader:
    """Thread-safe singleton manager for llama-cpp model instances."""

    _instance = None
    _lock = threading.RLock()
    _circuit_breaker = ModelCircuitBreaker()
    _draft_model_path: str | None = None
    _draft_instance = None
    _draft_n_ctx: int | None = None
    _draft_n_gpu_layers: int | None = None
    _remote_instance = None
    _remote_fallback_reason: str | None = None
    _MEMORY_SAFETY_MARGIN = 0.92
    _instance_locked = False
    _active_generation_count: int = 0   # incremented by lock_instance, decremented by unlock_instance
    _vocab_leak_report: dict = {}
    _load_latency_s: float | None = None
    _vram_bandwidth_gbs: float | None = None
    _backend_freed: bool = False
    _last_activity_time: float = 0.0
    _adapter_offloaded: bool = False
    _offloaded_adapter_name: str | None = None
    _idle_watcher_started: bool = False
    # Set inside get_instance() on first load
    _model_path: str | None = None
    _active_adapter: str | None = None
    _model_name: str | None = None
    _n_ctx: int = 4096
    # KV prompt cache (LlamaRAMCache); set to False to permanently disable.
    _cache_enabled: bool = True


    @classmethod
    def _read_registry_n_ctx(cls, filename: str) -> int:
        """Look up n_ctx for the given model filename from model_registry.json."""
        return config_store.registry_n_ctx(filename)

    @classmethod
    def _registry_entry(cls, filename: str) -> dict:
        for entry in config_store.get_model_registry():
            if entry.get("filename") == filename:
                return entry
        return {}

    @staticmethod
    def _truthy(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @classmethod
    def _quantized_kv_cache_enabled(cls) -> bool:
        env_value = os.environ.get("KARL_QUANTIZED_KV_CACHE")
        if env_value is not None:
            return cls._truthy(env_value)

        ui_config = config_store.get_ui_config()
        if cls._truthy(ui_config.get("quantized_kv_cache", False)):
            return True

        active_config = config_store.read_json(config_store.ACTIVE_MODEL_PATH, default={})
        if isinstance(active_config, dict):
            return cls._truthy(active_config.get("quantized_kv_cache", False))
        return False

    @staticmethod
    def _ggml_type_q8_0() -> int:
        try:
            from llama_cpp import GGML_TYPE_Q8_0
            return GGML_TYPE_Q8_0
        except Exception:
            return 8

    @classmethod
    def _adapter_path(cls, adapter_name: str | None) -> str | None:
        if not adapter_name:
            return None
        possible_paths = [
            os.path.join("data", "adapters", adapter_name, f"{adapter_name}.bin"),
            os.path.join("data", "adapters", adapter_name, f"{adapter_name}.gguf"),
            os.path.join("data", "adapters", adapter_name, "adapter_model.bin"),
            os.path.join("data", "adapters", adapter_name, "adapter_model.gguf"),
            os.path.join("data", "adapters", f"{adapter_name}.bin"),
            os.path.join("data", "adapters", f"{adapter_name}.gguf"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    @classmethod
    def _resolve_model_path(cls, model_path: str) -> str:
        if os.path.exists(model_path):
            return model_path
        fallback = "data/models/deepseek-r1-1.5b.gguf"
        if os.path.exists(fallback):
            logger.warning("%s not found — using %s", model_path, fallback)
            return fallback
        raise FileNotFoundError(
            f"No model at {model_path} or fallback {fallback}. "
            "Run python download_test_model.py first."
        )

    # ── CUDA Load Latency & VRAM Bandwidth Profiler ──────────────────────────

    @staticmethod
    def _bench_vram_bandwidth() -> float | None:
        """
        Measure effective PCIe host-to-device transfer bandwidth in GB/s.

        Allocates a 64 MB pinned-CPU tensor and copies it to a CUDA device
        tensor in a timed loop.  This reflects the PCIe throughput that
        constrains GGUF weight loading — the same path taken when llama.cpp
        transfers model layers from system RAM to VRAM.

        Returns None on CPU-only systems or when PyTorch is unavailable.
        Memory is always freed before returning.

        Thresholds (PCIe bandwidth reference):
          ≥ 15 GB/s — Gen3/Gen4 x16, healthy
          8 – 15 GB/s — Gen3 x8 / Gen2 x16, moderate bottleneck
          < 8 GB/s   — severely throttled lane, inference will be limited
        """
        src_cpu = None
        dst_gpu = None
        try:
            import torch
            if not torch.cuda.is_available():
                return None

            SIZE_BYTES = 64 * 1024 * 1024   # 64 MB
            N_ITER     = 8                   # 8 × 64 MB = 512 MB total transfer
            n_floats   = SIZE_BYTES // 4     # float32 = 4 bytes per element

            # Pinned (page-locked) host memory enables DMA transfers that
            # saturate PCIe bandwidth; fall back to regular memory if the
            # system denies the page lock.
            try:
                src_cpu = torch.empty(n_floats, dtype=torch.float32, pin_memory=True)
            except Exception:
                src_cpu = torch.empty(n_floats, dtype=torch.float32)
            dst_gpu = torch.empty(n_floats, dtype=torch.float32, device="cuda")

            # Warm-up: prime CUDA lazy init, allocator, and DMA engine
            dst_gpu.copy_(src_cpu, non_blocking=False)
            torch.cuda.synchronize()

            # Timed measurement — synchronize ensures all kernels are complete
            t0 = time.perf_counter()
            for _ in range(N_ITER):
                dst_gpu.copy_(src_cpu, non_blocking=False)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - t0

            bw = (N_ITER * SIZE_BYTES) / elapsed / 1e9   # GB/s
            return round(bw, 2)

        except Exception:
            return None
        finally:
            del src_cpu, dst_gpu
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    @classmethod
    def get_circuit_breaker_state(cls) -> str:
        """Return the current circuit breaker state (CLOSED / COOLDOWN / HALF_OPEN)."""
        with cls._lock:
            return cls._circuit_breaker.get_state()

    @classmethod
    def reset_circuit_breaker(cls):
        """Force-close the circuit breaker."""
        with cls._lock:
            cls._circuit_breaker.reset()

    @classmethod
    def load_latency_s(cls) -> float | None:
        """Wall-clock seconds for the most recent successful model load."""
        return getattr(cls, "_load_latency_s", None)

    @classmethod
    def vram_bandwidth_gbs(cls) -> float | None:
        """
        PCIe H2D bandwidth in GB/s measured immediately before the last load.
        Returns None on CPU-only systems or when PyTorch is not installed.
        """
        return getattr(cls, "_vram_bandwidth_gbs", None)

    # ── Tokenizer Vocabulary Leak Inspector ───────────────────────────────────

    @staticmethod
    def _load_adapter_special_tokens(adapter_dir: str) -> list[dict]:
        """
        Extract special tokens from HuggingFace tokenizer files in *adapter_dir*.
        Returns list of {id, content, source} dicts.
        Sources checked (in order): tokenizer.json, tokenizer_config.json,
        special_tokens_map.json.
        """
        tokens: list[dict] = []
        seen_ids: set[int] = set()
        seen_texts: set[str] = set()

        # ── tokenizer.json → added_tokens array ──────────────────────────────
        tj_path = os.path.join(adapter_dir, "tokenizer.json")
        if os.path.isfile(tj_path):
            try:
                with open(tj_path, "r", encoding="utf-8") as fh:
                    tj = json.load(fh)
                for entry in tj.get("added_tokens", []):
                    if not entry.get("special"):
                        continue
                    tid = int(entry["id"])
                    content = entry.get("content", "")
                    if tid not in seen_ids and content not in seen_texts:
                        seen_ids.add(tid)
                        seen_texts.add(content)
                        tokens.append({"id": tid, "content": content, "source": "tokenizer.json"})
            except Exception as exc:
                logger.debug("Could not parse %s: %s", tj_path, exc)

        # ── tokenizer_config.json → added_tokens_decoder ─────────────────────
        tc_path = os.path.join(adapter_dir, "tokenizer_config.json")
        if os.path.isfile(tc_path):
            try:
                with open(tc_path, "r", encoding="utf-8") as fh:
                    tc = json.load(fh)
                for id_str, entry in tc.get("added_tokens_decoder", {}).items():
                    if not entry.get("special"):
                        continue
                    tid = int(id_str)
                    content = entry.get("content", "")
                    if tid not in seen_ids and content not in seen_texts:
                        seen_ids.add(tid)
                        seen_texts.add(content)
                        tokens.append({"id": tid, "content": content, "source": "tokenizer_config.json"})
            except Exception as exc:
                logger.debug("Could not parse %s: %s", tc_path, exc)

        # ── special_tokens_map.json — id-less role→text mapping ───────────────
        sm_path = os.path.join(adapter_dir, "special_tokens_map.json")
        if os.path.isfile(sm_path):
            try:
                with open(sm_path, "r", encoding="utf-8") as fh:
                    sm = json.load(fh)
                for _role, val in sm.items():
                    content = val if isinstance(val, str) else val.get("content", "")
                    if content and content not in seen_texts:
                        seen_texts.add(content)
                        tokens.append({"id": None, "content": content, "source": "special_tokens_map.json"})
            except Exception as exc:
                logger.debug("Could not parse %s: %s", sm_path, exc)

        return tokens

    @staticmethod
    def _get_unk_id(llm) -> int | None:
        """Return the UNK token ID for the loaded llama model, or None if absent."""
        try:
            return llm.token_unk()
        except Exception:
            pass
        # Probe whether id=0 is UNK by inspecting its decoded representation.
        try:
            piece = llm.detokenize([0])
            if piece and b"unk" in piece.lower():
                return 0
        except Exception:
            pass
        return None

    @classmethod
    def _try_register_token_c_layer(cls, llm, token_text: str, expected_id: int) -> bool:
        """
        Attempt runtime token registration via the llama_cpp ctypes layer.
        llama_add_token is not part of the standard llama.cpp public API; this
        probes whether a future or custom build exposes it.
        Returns True on success, False (silently) when the binding is absent.
        """
        try:
            import llama_cpp as _llama_lib
            # Try the high-level Python module first, then the ctypes sub-module.
            fn = getattr(_llama_lib, "llama_add_token", None)
            if fn is None:
                _ctypes_layer = getattr(_llama_lib, "llama_cpp", None)
                if _ctypes_layer is not None:
                    fn = getattr(_ctypes_layer, "llama_add_token", None)
            if fn is None:
                return False
            fn(llm.model, expected_id, token_text.encode("utf-8"), len(token_text), True)
            logger.info(
                "Vocab inspector: C-layer registered '%s' → id %d", token_text, expected_id
            )
            return True
        except Exception as exc:
            logger.debug("C-layer llama_add_token unavailable (%s).", exc)
            return False

    @classmethod
    def _inspect_adapter_vocab(cls, adapter_name: str, llm) -> dict:
        """
        Compare the adapter's declared special tokens against the GGUF's embedded
        vocabulary.  Tokens that tokenize to <unk> or fall outside the vocab
        boundary are recorded as *hard leaks*; tokens that fragment into multiple
        sub-pieces are recorded as *fragmented* (softer degradation).

        For each hard leak, a C-layer registration attempt is made.  The
        resulting report is stored on cls._vocab_leak_report and returned.
        Downstream callers (e.g. interaction_loop.build_prompt) can query
        cls.vocab_leak_tokens() to bypass injecting leaking tags into prompts.
        """
        adapter_dir = os.path.join("data", "adapters", adapter_name)
        if not os.path.isdir(adapter_dir):
            cls._vocab_leak_report = {}
            return {}

        special_tokens = cls._load_adapter_special_tokens(adapter_dir)
        if not special_tokens:
            logger.debug("Vocab inspector: no special-token files found in %s", adapter_dir)
            cls._vocab_leak_report = {}
            return {}

        try:
            n_vocab = llm.n_vocab()
        except Exception:
            n_vocab = None

        unk_id = cls._get_unk_id(llm)

        leaks: list[dict] = []
        clean: list[dict] = []

        for entry in special_tokens:
            content    = entry["content"]
            expected_id = entry.get("id")  # None when sourced from special_tokens_map

            try:
                token_ids = llm.tokenize(content.encode("utf-8"), add_bos=False)
            except TypeError:
                # Older llama-cpp-python versions don't accept add_bos kwarg
                try:
                    token_ids = llm.tokenize(content.encode("utf-8"))
                except Exception as exc:
                    logger.warning(
                        "Vocab inspector: could not tokenize '%s': %s", content, exc
                    )
                    continue
            except Exception as exc:
                logger.warning(
                    "Vocab inspector: could not tokenize '%s': %s", content, exc
                )
                continue

            is_unk_hit     = (len(token_ids) == 1 and unk_id is not None and token_ids[0] == unk_id)
            is_out_of_vocab = (
                n_vocab is not None
                and expected_id is not None
                and expected_id >= n_vocab
            )
            is_fragmented  = len(token_ids) > 1

            if is_unk_hit or is_out_of_vocab:
                logger.warning(
                    "Tokenizer warning: custom adapter token parsed as <unk>. "
                    "token='%s' expected_id=%s actual_ids=%s unk_id=%s n_vocab=%s",
                    content, expected_id, token_ids, unk_id, n_vocab,
                )
                c_layer_ok = (
                    cls._try_register_token_c_layer(llm, content, expected_id)
                    if expected_id is not None
                    else False
                )
                leaks.append({
                    "content":          content,
                    "expected_id":      expected_id,
                    "actual_ids":       token_ids,
                    "unk_hit":          is_unk_hit,
                    "out_of_vocab":     is_out_of_vocab,
                    "fragmented":       is_fragmented,
                    "c_layer_registered": c_layer_ok,
                    "source":           entry.get("source"),
                })
            elif is_fragmented:
                logger.debug(
                    "Vocab inspector: token sub-tokenized (soft leak) '%s' → %s",
                    content, token_ids,
                )
                leaks.append({
                    "content":          content,
                    "expected_id":      expected_id,
                    "actual_ids":       token_ids,
                    "unk_hit":          False,
                    "out_of_vocab":     False,
                    "fragmented":       True,
                    "c_layer_registered": False,
                    "source":           entry.get("source"),
                })
            else:
                clean.append({
                    "content":     content,
                    "expected_id": expected_id,
                    "actual_ids":  token_ids,
                    "source":      entry.get("source"),
                })

        report = {
            "adapter":  adapter_name,
            "checked":  len(special_tokens),
            "leaks":    leaks,
            "clean":    clean,
            "unk_id":   unk_id,
            "n_vocab":  n_vocab,
        }
        cls._vocab_leak_report = report

        hard_leaks = [e for e in leaks if e["unk_hit"] or e["out_of_vocab"]]
        if hard_leaks:
            logger.warning(
                "Vocab leak inspector: %d hard leak(s) detected for adapter '%s'. "
                "These tokens will collapse to <unk> during inference. "
                "Ensure the adapter was fine-tuned on the same base tokenizer as the GGUF.",
                len(hard_leaks), adapter_name,
            )
        elif leaks:
            logger.info(
                "Vocab leak inspector: %d token(s) sub-tokenized (soft) for adapter '%s'. "
                "No hard <unk> collisions.",
                len(leaks), adapter_name,
            )
        else:
            logger.info(
                "Vocab leak inspector: all %d special token(s) verified clean for adapter '%s'.",
                len(special_tokens), adapter_name,
            )

        return report

    @classmethod
    def vocab_leak_report(cls) -> dict:
        """Return the most recent tokenizer vocabulary leak inspection report."""
        return cls._vocab_leak_report

    @classmethod
    def vocab_leak_tokens(cls) -> dict:
        """
        Return {token_text: expected_adapter_id} for every token that hard-leaked
        (<unk> collision or out-of-vocabulary).  Empty when no adapter is active
        or when all tokens verified clean.
        Intended for use by interaction_loop.build_prompt to bypass injecting
        broken tokens into the model's prompt context.
        """
        report = cls._vocab_leak_report
        return {
            e["content"]: e["expected_id"]
            for e in report.get("leaks", [])
            if e.get("unk_hit") or e.get("out_of_vocab")
        }

    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def estimate_load_memory(cls, model_path: str, adapter_name: str | None = None) -> dict:
        """
        Estimate local RAM/VRAM pressure before a GGUF reload.

        The estimate intentionally errs on the conservative side because Karl loads
        with n_gpu_layers=-1. If a model is larger than available VRAM, llama.cpp can
        fail after the previous model was already unloaded.
        """
        resolved_path = cls._resolve_model_path(model_path)
        filename = os.path.basename(resolved_path)
        entry = cls._registry_entry(filename)
        n_ctx = int(entry.get("n_ctx") or cls._read_registry_n_ctx(filename))
        file_gb = os.path.getsize(resolved_path) / (1024 ** 3)

        # KV cache grows roughly with context. This is a practical guardrail, not a
        # llama.cpp memory profiler.
        kv_cache_gb = max(0.25, (n_ctx / 4096.0) * 0.35)
        adapter_path = cls._adapter_path(adapter_name)
        adapter_gb = 0.0
        if adapter_path:
            try:
                adapter_gb = os.path.getsize(adapter_path) / (1024 ** 3)
            except OSError as exc:
                logger.debug("could not stat adapter file %s: %s", adapter_path, exc)

        estimated_ram_gb = max(
            float(entry.get("min_ram_gb") or 0.0),
            (file_gb * 1.20) + kv_cache_gb + adapter_gb + 0.75,
        )
        estimated_vram_gb = max(
            float(entry.get("min_vram_gb") or 0.0),
            file_gb + kv_cache_gb + adapter_gb,
        )

        try:
            hardware = get_hardware_profile()
        except Exception as exc:
            logger.warning("could not collect hardware profile before model load: %s", exc)
            hardware = {"ram_gb": 0.0, "vram_gb": 0.0, "storage_gb": 0.0}

        return {
            "filename": filename,
            "path": resolved_path,
            "adapter": adapter_name,
            "adapter_path": adapter_path,
            "n_ctx": n_ctx,
            "file_gb": round(file_gb, 2),
            "kv_cache_gb": round(kv_cache_gb, 2),
            "adapter_gb": round(adapter_gb, 2),
            "estimated_ram_gb": round(estimated_ram_gb, 2),
            "estimated_vram_gb": round(estimated_vram_gb, 2),
            "available_ram_gb": float(hardware.get("ram_gb") or 0.0),
            "available_vram_gb": float(hardware.get("vram_gb") or 0.0),
            "storage_gb": float(hardware.get("storage_gb") or 0.0),
            "registry": entry,
        }

    @classmethod
    def _show_memory_warning_dialog(cls, message: str):
        try:
            from PyQt6.QtCore import QThread
            from PyQt6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance()
            if app is not None and QThread.currentThread() == app.thread():
                QMessageBox.warning(None, "Karl Model Memory Guard", message)
        except Exception as exc:
            logger.debug("could not show model memory warning dialog: %s", exc)

    @classmethod
    def preflight_model_load(
        cls,
        model_path: str,
        adapter_name: str | None = None,
        *,
        show_dialog: bool = True,
    ) -> dict:
        """Estimate memory pressure and block unsafe model reloads.

        Returns a load plan dict. Raises ModelMemoryError when estimated RAM or
        VRAM exceeds the configured safety margin unless
        KARL_ALLOW_OVERSIZED_MODEL=1 is set.
        """
        plan = cls.estimate_load_memory(model_path, adapter_name)
        if os.environ.get("KARL_ALLOW_OVERSIZED_MODEL") == "1":
            plan["allowed_by_override"] = True
            return plan

        failures = []
        available_ram = plan["available_ram_gb"]
        available_vram = plan["available_vram_gb"]
        if available_ram and plan["estimated_ram_gb"] > available_ram * cls._MEMORY_SAFETY_MARGIN:
            failures.append(
                f"RAM estimate {plan['estimated_ram_gb']:.2f} GB exceeds safe available RAM "
                f"{available_ram * cls._MEMORY_SAFETY_MARGIN:.2f} GB."
            )
        if available_vram and plan["estimated_vram_gb"] > available_vram * cls._MEMORY_SAFETY_MARGIN:
            failures.append(
                f"VRAM estimate {plan['estimated_vram_gb']:.2f} GB exceeds safe available VRAM "
                f"{available_vram * cls._MEMORY_SAFETY_MARGIN:.2f} GB."
            )

        plan["blocked"] = bool(failures)
        plan["failures"] = failures
        if failures:
            message = (
                f"Blocked load for {plan['filename']}.\n\n"
                + "\n".join(failures)
                + "\n\nSet KARL_ALLOW_OVERSIZED_MODEL=1 to bypass this guard."
            )
            logger.warning(message.replace("\n", " "))
            if show_dialog:
                cls._show_memory_warning_dialog(message)
            raise ModelMemoryError(message, plan)
        return plan

    @classmethod
    def _touch_activity(cls) -> None:
        """Refresh the idle timer. Call at every inference entry point."""
        cls._last_activity_time = time.time()

    @classmethod
    def _start_idle_watcher(cls) -> None:
        """Spawn the background adapter-offload daemon (once per process)."""
        if cls._idle_watcher_started:
            return
        cls._idle_watcher_started = True

        def _watcher():
            while True:
                time.sleep(30)
                try:
                    if cls._last_activity_time == 0.0:
                        continue
                    if time.time() - cls._last_activity_time < 300:
                        continue
                    with cls._lock:
                        if (cls._adapter_offloaded
                                or cls._active_adapter is None
                                or cls._instance is None
                                or cls._active_generation_count > 0
                                or cls._instance_locked):
                            continue
                        adapter_name = cls._active_adapter
                        # Best-effort C-layer LoRA detach before flagging offload.
                        try:
                            import llama_cpp.llama_cpp as _ll
                            if (hasattr(_ll, "llama_lora_adapter_remove")
                                    and hasattr(cls._instance, "_lora_adapter")):
                                _ll.llama_lora_adapter_remove(
                                    cls._instance.ctx, cls._instance._lora_adapter
                                )
                                logger.debug("C-layer LoRA adapter removed from context.")
                            elif hasattr(cls._instance, "set_lora"):
                                cls._instance.set_lora(None)
                        except Exception as exc:
                            logger.debug("Idle adapter C-layer detach unavailable: %s", exc)
                        cls._offloaded_adapter_name = adapter_name
                        cls._adapter_offloaded = True
                        cls._active_adapter = None
                        logger.info("Adapter unloaded to save VRAM.")
                except Exception as exc:
                    logger.debug("Idle watcher tick error: %s", exc)

        threading.Thread(
            target=_watcher, daemon=True, name="karl-idle-adapter-watcher"
        ).start()

    @classmethod
    def get_instance(cls, model_path: str | None = None, adapter_name: str | None = None,
                     draft_model_path: str | None = None) -> Llama:
        """Return the active Llama instance, loading or reloading if needed.

        Args:
            model_path: Optional GGUF path. When omitted, data/active_model.json
                selects the model filename.
            adapter_name: Optional LoRA adapter name under data/adapters/.
            draft_model_path: Optional GGUF draft model for speculative decoding.

        Raises:
            CircuitBreakerOpenException: repeated fatal load failures are cooling down.
            FileNotFoundError: requested model and fallback model are unavailable.
            ModelMemoryError: preflight RAM/VRAM guard blocks the load.
            RuntimeError/OSError: llama-cpp load or platform checks fail.
        """
        with cls._lock:
            # Mark this as an active inference call for the idle watcher.
            cls._last_activity_time = time.time()

            if model_path is None:
                active = config_store.get_active_model()
                model_path = os.path.join("data", "models", active["filename"])
                if adapter_name is None:
                    adapter_name = active["adapter"]
            if draft_model_path is None:
                draft_cfg = config_store.get_active_draft_model()
                draft_n_ctx = int(draft_cfg.get("n_ctx", cls._n_ctx) or cls._n_ctx)
                draft_n_gpu_layers = int(draft_cfg.get("n_gpu_layers", -1))
                if draft_cfg.get("enabled"):
                    configured_path = draft_cfg.get("draft_model_path")
                    if configured_path:
                        draft_model_path = configured_path
                    elif draft_cfg.get("filename"):
                        draft_model_path = os.path.join("data", "models", draft_cfg["filename"])
            else:
                draft_n_ctx = cls._n_ctx
                draft_n_gpu_layers = -1

            # If the idle watcher offloaded the adapter, clear _active_adapter so that
            # the needs_reload check below fires and the adapter is lazily reloaded.
            if cls._adapter_offloaded:
                logger.info(
                    "Lazy adapter reload triggered for '%s'.", cls._offloaded_adapter_name
                )
                cls._active_adapter = None
                cls._adapter_offloaded = False
                cls._offloaded_adapter_name = None

            current_model_path = getattr(cls, "_model_path", None)
            current_adapter = getattr(cls, "_active_adapter", None)

            # change speculative draft model only when requested draft path differs
            needs_draft_reload = (
                draft_model_path != getattr(cls, '_draft_model_path', None) or
                (
                    draft_model_path is not None and (
                        draft_n_ctx != getattr(cls, "_draft_n_ctx", None) or
                        draft_n_gpu_layers != getattr(cls, "_draft_n_gpu_layers", None)
                    )
                )
            )

            needs_reload = (
                cls._instance is None or
                (model_path is not None and model_path != current_model_path) or
                (adapter_name != current_adapter)
            )

            if needs_reload or needs_draft_reload:
                cls._circuit_breaker.before_call()

                if cls._instance_locked or cls._active_generation_count > 0:
                    raise RuntimeError(
                        "Cannot reload model or change adapter while inference is active "
                        f"({cls._active_generation_count} generation"
                        f"{'s' if cls._active_generation_count != 1 else ''} in flight). "
                        "Request cancellation before reloading."
                    )
                model_path = cls._resolve_model_path(model_path)
                model_name = os.path.basename(model_path)
                
                # ── Pre-flight CPU Instruction Check ──────────────────────
                # Detect potential segfaults due to AVX/AVX2/AVX512 incompatibility
                # before loading a massive model.
                import subprocess
                import sys
                check_script = (
                    "import sys; "
                    "try: "
                    "  # Basic import check for llama_cpp which loads GGML shared libs. "
                    "  # This is often enough to trigger SIGILL/SIGSEGV on incompatible CPUs. "
                    "  from llama_cpp import Llama; "
                    "  sys.exit(0); "
                    "except Exception: "
                    "  sys.exit(1)"
                )
                try:
                    # Use same executable as host Karl app
                    proc = subprocess.run(
                        [sys.executable, "-c", check_script],
                        capture_output=True,
                        timeout=5.0
                    )
                    if proc.returncode in (132, 139): # SIGILL or SIGSEGV
                        msg = (
                            "FATAL: CPU Instruction Error detected. The installed llama-cpp-python "
                            "binary is incompatible with your CPU instructions. "
                            "Please re-install/recompile using: CMAKE_ARGS='-DGGML_AVX=OFF' pip install llama-cpp-python --force-reinstall"
                        )
                        logger.error(msg)
                        cls._circuit_breaker.record_failure(RuntimeError(msg))
                        raise RuntimeError(msg)
                except subprocess.TimeoutExpired:
                    pass # Ignore timeouts for pre-flight check
                # ─────────────────────────────────────────────────────────

                n_ctx = cls._read_registry_n_ctx(model_name)
                try:
                    cls.preflight_model_load(model_path, adapter_name)
                except (ModelMemoryError, MemoryError, OSError, RuntimeError) as exc:
                    cls._circuit_breaker.record_failure(exc)
                    raise

                if cls._instance is not None:
                    try:
                        logger.info("Closing existing Llama instance to free VRAM")
                        cls._instance.close()
                    except Exception as e:
                        logger.warning(f"Error closing existing Llama instance: {e}")
                    cls._instance = None
                
                import gc
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass

                cls._model_path = model_path
                cls._model_name = model_name
                cls._n_ctx = n_ctx
                cls._active_adapter = adapter_name

                lora_path = cls._adapter_path(adapter_name)

                # ── Multi-GPU VRAM Telemetry & Tensor Split ───────────────────
                _gpu_list = get_hardware_profile().get("gpu_list", [])
                tensor_split: list[float] | None = None
                if len(_gpu_list) > 1:
                    _free_mb = [g["memory_free_mb"] for g in _gpu_list]
                    _total_free = sum(_free_mb)
                    if _total_free > 0:
                        tensor_split = [v / _total_free for v in _free_mb]
                        logger.info(
                            "Multi-GPU detected (%d GPUs). Proportional tensor split: %s",
                            len(_gpu_list),
                            [f"{s:.3f}" for s in tensor_split],
                        )
                # ─────────────────────────────────────────────────────────────

                # n_batch from registry (default 512 = llama.cpp default; making it
                # explicit lets per-model overrides land in model_registry.json).
                _reg_entry = cls._registry_entry(model_name)
                n_batch = int(_reg_entry.get("n_batch", 512))

                def _attempt_load(ctx_size, ts=None):
                    threads = max(1, multiprocessing.cpu_count() - 2)
                    gpu_tag = f", {len(ts)}-GPU split" if ts else ""
                    kwargs = dict(
                        model_path=model_path,
                        n_ctx=ctx_size,
                        n_gpu_layers=-1,
                        n_batch=n_batch,
                        n_ubatch=n_batch,
                        flash_attn=True,
                        logits_all=False,
                        n_threads=threads,
                        verbose=False,
                        use_mmap=True,
                        use_mlock=True,
                    )
                    if lora_path:
                        kwargs["lora_path"] = lora_path
                        logger.info(
                            "Loading %s with LoRA adapter %s (n_ctx=%d, threads=%d%s)",
                            model_path, lora_path, ctx_size, threads, gpu_tag,
                        )
                    else:
                        logger.info(
                            "Loading %s (n_ctx=%d, threads=%d%s)",
                            model_path, ctx_size, threads, gpu_tag,
                        )
                    if ts is not None:
                        kwargs["tensor_split"] = ts

                    quantized_kv_cache = cls._quantized_kv_cache_enabled()
                    if quantized_kv_cache:
                        q8_type = cls._ggml_type_q8_0()
                        kwargs["type_k"] = q8_type
                        kwargs["type_v"] = q8_type
                        logger.info(
                            "Enabling 8-bit quantized KV cache (Q8_0) for long-context execution."
                        )
                    
                    try:
                        return Llama(**kwargs)
                    except TypeError as e:
                        if quantized_kv_cache and ("type_k" in kwargs or "type_v" in kwargs):
                            logger.warning(
                                "Installed llama-cpp-python does not support type_k/type_v "
                                "KV cache overrides. Falling back to standard F16 KV cache."
                            )
                            kwargs.pop("type_k", None)
                            kwargs.pop("type_v", None)
                            return Llama(**kwargs)
                        raise
                    except (OSError, RuntimeError) as e:
                        # Detect mlock privilege/limit failures
                        err_msg = str(e).lower()
                        if "mlock" in err_msg or "locked memory" in err_msg:
                            logger.warning(
                                "Warning: mlock failed due to ulimit -l limits. "
                                "Attempting fallback loading without memory locking..."
                            )
                            logger.info(
                                "INSTRUCTION: To permanently raise locked memory limits on Linux (Arch/Ubuntu), "
                                "add '* hard memlock unlimited' and '* soft memlock unlimited' to /etc/security/limits.conf "
                                "and restart your session."
                            )
                            kwargs["use_mlock"] = False
                            return Llama(**kwargs)
                        raise # Re-raise OOM or other errors for the fallback loop to handle

                # ── llama-cpp backend reinit after deep eviction ──────────────
                if cls._backend_freed:
                    try:
                        import llama_cpp.llama_cpp as _llama_lib
                        _llama_lib.llama_backend_init()
                        cls._backend_freed = False
                        logger.info("llama_backend_init() called after deep VRAM eviction.")
                    except Exception as exc:
                        logger.debug("llama_backend_init unavailable or failed: %s", exc)
                # ─────────────────────────────────────────────────────────────

                # ── Pre-flight VRAM Bandwidth Benchmark ──────────────────────
                # Measure PCIe H2D throughput before the model occupies VRAM so
                # the allocator is in its cleanest state.  The result is stored
                # and surfaced in the status bar after loading completes.
                cls._vram_bandwidth_gbs = cls._bench_vram_bandwidth()
                cls._load_latency_s = None   # reset; set on the successful attempt
                if cls._vram_bandwidth_gbs is not None:
                    logger.info(
                        "VRAM bandwidth pre-flight: %.2f GB/s", cls._vram_bandwidth_gbs
                    )
                # ─────────────────────────────────────────────────────────────

                # ── Fallback Context Scaling Loop ─────────────────────────────
                # If loading fails due to VRAM/RAM exhaustion, halve n_ctx and retry.
                current_n_ctx = cls._n_ctx
                min_ctx = 2048
                cls._instance = None

                # Multi-GPU first attempt — proportional tensor split across all cards.
                # Broad except catches driver mismatches and CUDA peer-to-peer mapping
                # failures, which are not OOM conditions and cannot be fixed by halving
                # n_ctx, so we skip straight to the single-GPU fallback loop below.
                if tensor_split is not None:
                    _t0 = time.perf_counter()
                    try:
                        cls._instance = _attempt_load(current_n_ctx, ts=tensor_split)
                        cls._load_latency_s = time.perf_counter() - _t0
                        cls._n_ctx = current_n_ctx
                    except Exception as e:
                        logger.warning(
                            "Multi-GPU tensor-split load failed (%s). "
                            "Falling back to single-GPU (GPU 0).",
                            e,
                        )

                # Single-GPU fallback: context halving loop (also the only path when
                # only one GPU is present or the multi-GPU attempt did not succeed).
                while cls._instance is None:
                    _t0 = time.perf_counter()
                    try:
                        cls._instance = _attempt_load(current_n_ctx)
                        cls._load_latency_s = time.perf_counter() - _t0
                        cls._n_ctx = current_n_ctx  # Store successfully allocated limit
                    except (MemoryError, OSError, RuntimeError) as e:
                        if current_n_ctx <= min_ctx:
                            msg = "VRAM Allocation Limit Exceeded even at minimum context budget (2048). Please free system GPU memory."
                            logger.error(f"{msg} Final failure: {e}")
                            failure = RuntimeError(msg)
                            cls._circuit_breaker.record_failure(failure)
                            raise failure from e

                        old_ctx = current_n_ctx
                        current_n_ctx = max(min_ctx, current_n_ctx // 2)
                        logger.warning(
                            f"VRAM allocation failed for n_ctx={old_ctx}: {e}. "
                            f"Retrying with scaled context (n_ctx={current_n_ctx})..."
                        )

                        import gc
                        gc.collect()
                        try:
                            import torch
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                        except ImportError:
                            pass
                # ─────────────────────────────────────────────────────────────

                _bw_str = (
                    f"{cls._vram_bandwidth_gbs:.1f} GB/s"
                    if cls._vram_bandwidth_gbs is not None
                    else "N/A (no CUDA)"
                )
                logger.info(
                    "Ready. Load: %.2fs | VRAM bandwidth: %s",
                    cls._load_latency_s or 0.0,
                    _bw_str,
                )

                # ── KV Prompt Cache ───────────────────────────────────────────
                cls._attach_kv_cache()
                # ─────────────────────────────────────────────────────────────

                # ── Tokenizer Vocabulary Leak Inspection ──────────────────────
                # Run after the instance is live so llm.tokenize() and
                # llm.n_vocab() use the GGUF's own embedded vocabulary table.
                if adapter_name:
                    cls._inspect_adapter_vocab(adapter_name, cls._instance)
                else:
                    cls._vocab_leak_report = {}
                # ─────────────────────────────────────────────────────────────

                if needs_reload or needs_draft_reload:
                    # Tear down existing draft
                    if cls._draft_instance is not None:
                        try:
                            cls._draft_instance.close()
                        except Exception:
                            pass
                        cls._draft_instance = None

                    if draft_model_path and os.path.exists(draft_model_path):
                        try:
                            from llama_cpp import Llama as _LlamaInner
                            threads = max(1, multiprocessing.cpu_count() - 2)
                            
                            draft_kwargs = dict(
                                model_path=draft_model_path,
                                n_ctx=draft_n_ctx,
                                n_gpu_layers=draft_n_gpu_layers,
                                logits_all=False,
                                n_threads=threads,
                                verbose=False,
                                use_mmap=True,
                                use_mlock=True,
                            )
                            try:
                                cls._draft_instance = _LlamaInner(**draft_kwargs)
                            except (OSError, RuntimeError) as e:
                                if "mlock" in str(e).lower() or "locked memory" in str(e).lower():
                                    logger.warning("Warning: Draft model mlock failed. Falling back to non-locked loading.")
                                    draft_kwargs["use_mlock"] = False
                                    cls._draft_instance = _LlamaInner(**draft_kwargs)
                                else:
                                    raise

                            # Re-instantiate primary model wired to the draft instance.
                            # llama-cpp-python exposes speculative decoding via the draft_model kwarg
                            # (available since 0.2.77). If the installed version lacks this kwarg,
                            # catch TypeError and continue without speculative support.
                            try:
                                if cls._instance is not None:
                                    cls._instance.close()
                                
                                primary_kwargs = dict(
                                    model_path=cls._model_path,
                                    n_ctx=cls._n_ctx,
                                    lora_path=cls._adapter_path(cls._active_adapter),
                                    n_gpu_layers=-1,
                                    logits_all=False,
                                    n_threads=threads,
                                    verbose=False,
                                    draft_model=cls._draft_instance,
                                    use_mmap=True,
                                    use_mlock=True,
                                )
                                try:
                                    cls._instance = Llama(**primary_kwargs)
                                except (OSError, RuntimeError) as e:
                                    if "mlock" in str(e).lower() or "locked memory" in str(e).lower():
                                        logger.warning("Warning: Primary model mlock failed during speculative load.")
                                        primary_kwargs["use_mlock"] = False
                                        cls._instance = Llama(**primary_kwargs)
                                    else:
                                        raise

                                logger.info(
                                    f"Speculative decoding active: target={cls._model_name} "
                                    f"draft={os.path.basename(draft_model_path)}"
                                )
                            except TypeError:
                                logger.warning(
                                    "Installed llama-cpp-python does not support draft_model kwarg. "
                                    "Falling back to standard inference without speculative decoding."
                                )
                                cls._draft_instance.close()
                                cls._draft_instance = None
                        except Exception as e:
                            logger.warning(f"Failed to load draft model {draft_model_path}: {e}")
                            cls._draft_instance = None
                            try:
                                config_store.set_active_draft_model(None, enabled=False)
                                logger.info("Speculative decoding has been disabled in configuration due to loading failure.")
                            except Exception as config_err:
                                logger.warning(f"Failed to auto-disable speculative decoding in config: {config_err}")

                    cls._draft_model_path = draft_model_path
                    cls._draft_n_ctx = draft_n_ctx
                    cls._draft_n_gpu_layers = draft_n_gpu_layers
                cls._circuit_breaker.record_success()
            cls._start_idle_watcher()
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Unload active model and draft handles, clearing runtime loader state.

        Raises RuntimeError if any generation currently holds the inference lock.
        """
        with cls._lock:
            cls._raise_if_inference_active("reset ModelLoader")
            cls._instance_locked = False

            # 1. Release KV-cache memory before closing the Llama handle.
            if cls._instance is not None:
                try:
                    cls._instance.set_cache(None)
                except Exception:
                    pass

            # 2. Close and explicitly delete Llama handles to drop all C-level refs
            if cls._instance is not None:
                try:
                    cls._instance.close()
                except Exception:
                    pass
                del cls._instance
                cls._instance = None

            if cls._draft_instance is not None:
                try:
                    cls._draft_instance.close()
                except Exception:
                    pass
                del cls._draft_instance
                cls._draft_instance = None

            cls._draft_model_path = None
            cls._draft_n_ctx = None
            cls._draft_n_gpu_layers = None
            cls._active_adapter = None
            cls._model_path = None

            # 2. CPython GC pass — collects any lingering cyclic refs to the Llama object
            import gc
            gc.collect()

            # 3. PyTorch CUDA defragmentation
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except ImportError:
                pass

            # 4. llama-cpp C-backend teardown — forces OS to reclaim all GGML/CUDA
            #    allocations. The backend is re-initialised automatically on next load.
            try:
                import llama_cpp.llama_cpp as _llama_lib
                _llama_lib.llama_backend_free()
                cls._backend_freed = True
                logger.info("llama_backend_free() called; backend will reinit on next load.")
            except Exception as exc:
                logger.debug("llama_backend_free unavailable or failed: %s", exc)

    # ── KV Prompt Cache Management ────────────────────────────────────────────

    @staticmethod
    def _free_vram_mb() -> float | None:
        """Return the minimum free VRAM (MB) across all GPUs, or None."""
        try:
            gpus = get_hardware_profile().get("gpu_list", [])
            if not gpus:
                return None
            return min(g.get("memory_free_mb", float("inf")) for g in gpus)
        except Exception:
            return None

    @classmethod
    def _attach_kv_cache(cls) -> None:
        """
        Attach a LlamaRAMCache to the loaded instance.

        Capacity is 25 % of free VRAM (clamped to 256 MB–2 GB).
        Skipped entirely when free VRAM < 500 MB to avoid OOM.
        """
        if cls._instance is None or not cls._cache_enabled:
            return

        free_mb = cls._free_vram_mb()
        if free_mb is not None and free_mb < 500:
            logger.warning(
                "Free VRAM %.0f MB < 500 MB — KV prompt cache disabled to prevent OOM.",
                free_mb,
            )
            return

        _256_mb = 256 * (1 << 20)
        _2_gb   =   2 * (1 << 30)
        if free_mb is not None:
            capacity = min(_2_gb, max(_256_mb, int(free_mb * 0.25 * 1024 * 1024)))
        else:
            capacity = 1 << 30   # 1 GB fallback when VRAM info is unavailable

        try:
            cache = LlamaRAMCache(capacity_bytes=capacity)
            cls._instance.set_cache(cache)
            logger.info("KV prompt cache attached (%.2f GB).", capacity / (1 << 30))
        except Exception as exc:
            logger.warning("Failed to attach KV prompt cache: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _raise_if_inference_active(cls, operation: str = "reset ModelLoader") -> None:
        """Raise RuntimeError if any generation is in flight."""
        count = cls._active_generation_count
        if count > 0 or cls._instance_locked:
            raise RuntimeError(
                f"Cannot {operation} while inference is active "
                f"({count} active generation{'s' if count != 1 else ''} in flight). "
                "Request cancellation before reloading."
            )

    @classmethod
    def lock_instance(cls) -> None:
        """Mark the singleton as in-use by an active generation."""
        with cls._lock:
            cls._active_generation_count += 1
            cls._instance_locked = True
            logger.info(
                "ModelLoader inference lock acquired (active=%d).",
                cls._active_generation_count,
            )

    @classmethod
    def unlock_instance(cls) -> None:
        """Release one active generation lock from the singleton."""
        with cls._lock:
            cls._active_generation_count = max(0, cls._active_generation_count - 1)
            if cls._active_generation_count == 0:
                cls._instance_locked = False
            logger.info(
                "ModelLoader inference lock released (active=%d).",
                cls._active_generation_count,
            )

    @classmethod
    def acquire_instance(cls, **kwargs):
        """Like get_instance but asserts the lock is clear before a reload."""
        llm = cls.get_instance(**kwargs)
        cls.lock_instance()
        return llm

    @classmethod
    def _remote_fallback(cls, reason: str) -> None:
        """Disable remote inference after a failure and remember the reason."""
        cls._remote_fallback_reason = reason
        cls._remote_instance = None
        try:
            cfg = config_store.get_engine_config()
            url = cfg.get("remote_engine_url") or cfg.get("remote_server_url")
            token = cfg.get("remote_engine_token") or cfg.get("remote_auth_token")
            config_store.set_remote_engine_config(False, url, token)
        except Exception:
            logger.debug("Failed to persist remote fallback disable.", exc_info=True)

    @classmethod
    def last_remote_fallback_reason(cls) -> str | None:
        return cls._remote_fallback_reason

    @classmethod
    def reset_circuit_breaker(cls) -> None:
        """Reset the model-load circuit breaker to CLOSED."""
        with cls._lock:
            cls._circuit_breaker.reset()

    @classmethod
    def is_instance_locked(cls) -> bool:
        """Return True when a generation is actively using the model."""
        with cls._lock:
            return cls._instance_locked

    @classmethod
    def context_limit(cls) -> int:
        """Return the context limit of the loaded GGUF model or config fallback."""
        return cls.n_ctx()

    @classmethod
    def model_name(cls) -> str:
        """Return the basename of the active GGUF model, or 'none'."""
        name = getattr(cls, "_model_name", "none")
        return name if name is not None else "none"

    @classmethod
    def n_ctx(cls) -> int:
        """Return the context window size for the loaded model."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    if hasattr(cls._instance, "n_ctx"):
                        val = cls._instance.n_ctx
                        if callable(val):
                            res = val()
                            if isinstance(res, (int, float)) and not isinstance(res, bool):
                                return int(res)
                        elif isinstance(val, (int, float)) and not isinstance(val, bool):
                            return int(val)
                except Exception as e:
                    logger.warning(f"Error querying model context limit: {e}")
            
            # Fallback to active model's n_ctx
            try:
                from app.engine import config_store
                active = config_store.get_active_model()
                if active and "filename" in active:
                    res = cls._read_registry_n_ctx(active["filename"])
                    if isinstance(res, (int, float)) and not isinstance(res, bool):
                        return int(res)
            except Exception:
                pass
            fallback = getattr(cls, '_n_ctx', 4096)
            if isinstance(fallback, (int, float)) and not isinstance(fallback, bool):
                return int(fallback)
            return 4096

    @classmethod
    def is_loaded(cls) -> bool:
        """Return True when a primary Llama instance is loaded."""
        with cls._lock:
            return cls._instance is not None

    @classmethod
    def is_speculative(cls) -> bool:
        """True when a draft model is attached and speculative decoding is active."""
        with cls._lock:
            return cls._draft_instance is not None

    @classmethod
    def speculative_generation_kwargs(cls) -> dict:
        """Return per-call speculative kwargs when supported by llama-cpp-python.

        Karl primarily wires speculative decoding through the Llama constructor
        because that is the API exposed by the local llama-cpp-python build.
        Some builds may expose a per-call ``draft_model`` kwarg; this helper lets
        generation loops pass it without breaking builds that reject it.
        """
        with cls._lock:
            draft = cls._draft_instance
            instance = cls._instance
        if draft is None or instance is None:
            return {}
        try:
            params = inspect.signature(instance.__call__).parameters
        except (TypeError, ValueError):
            return {}
        if "draft_model" in params or any(
            param.kind == inspect.Parameter.VAR_KEYWORD
            for param in params.values()
        ):
            return {"draft_model": draft}
        return {}

    @classmethod
    def get_quantization(cls) -> str | None:
        """Return quantization level from the registry entry for the loaded model."""
        from app.engine import config_store
        name = getattr(cls, "_model_name", None)
        if not name:
            return None
        entry = config_store.registry_entry(name)
        return entry.get("quant") if entry else None

    @classmethod
    def vram_estimate_gb(cls) -> float | None:
        """Return estimated VRAM requirement from registry for the loaded model."""
        from app.engine import config_store
        name = getattr(cls, "_model_name", None)
        if not name:
            return None
        entry = config_store.registry_entry(name)
        return entry.get("min_vram_gb") if entry else None
