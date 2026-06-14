import json
import logging
import os
import threading
import multiprocessing
import time
from llama_cpp import Llama

from app.engine import config_store
from core.hardware_scout import get_hardware_profile


logger = logging.getLogger("karl.model_loader")


class ModelMemoryError(RuntimeError):
    """Raised when a requested GGUF load exceeds Karl's local memory guard."""

    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


class ModelLoader:
    _instance = None
    _lock = threading.Lock()
    _draft_model_path: str | None = None
    _draft_instance = None
    _MEMORY_SAFETY_MARGIN = 0.92
    _instance_locked = False
    _vocab_leak_report: dict = {}    # populated by _inspect_adapter_vocab after each load
    _load_latency_s: float | None = None   # wall-clock seconds for the last successful load
    _vram_bandwidth_gbs: float | None = None  # measured PCIe H2D bandwidth (GB/s)


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
    def get_instance(cls, model_path: str | None = None, adapter_name: str | None = None,
                     draft_model_path: str | None = None) -> Llama:
        with cls._lock:
            if model_path is None:
                active = config_store.get_active_model()
                model_path = os.path.join("data", "models", active["filename"])
                if adapter_name is None:
                    adapter_name = active["adapter"]

            current_model_path = getattr(cls, "_model_path", None)
            current_adapter = getattr(cls, "_active_adapter", None)

            needs_draft_reload = (draft_model_path != getattr(cls, '_draft_model_path', None))

            needs_reload = (
                cls._instance is None or
                (model_path is not None and model_path != current_model_path) or
                (adapter_name != current_adapter)
            )

            if needs_reload:
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
                        raise RuntimeError(msg)
                except subprocess.TimeoutExpired:
                    pass # Ignore timeouts for pre-flight check
                # ─────────────────────────────────────────────────────────

                n_ctx = cls._read_registry_n_ctx(model_name)
                cls.preflight_model_load(model_path, adapter_name)

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

                def _attempt_load(ctx_size, ts=None):
                    threads = max(1, multiprocessing.cpu_count() - 2)
                    gpu_tag = f", {len(ts)}-GPU split" if ts else ""
                    kwargs = dict(
                        model_path=model_path,
                        n_ctx=ctx_size,
                        n_gpu_layers=-1,
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
                    
                    try:
                        return Llama(**kwargs)
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
                            raise RuntimeError(msg) from e

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

                # ── Tokenizer Vocabulary Leak Inspection ──────────────────────
                # Run after the instance is live so llm.tokenize() and
                # llm.n_vocab() use the GGUF's own embedded vocabulary table.
                if adapter_name:
                    cls._inspect_adapter_vocab(adapter_name, cls._instance)
                else:
                    cls._vocab_leak_report = {}
                # ─────────────────────────────────────────────────────────────

                if needs_draft_reload or needs_reload:
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
                                n_ctx=cls._n_ctx,
                                n_gpu_layers=-1,
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

                    cls._draft_model_path = draft_model_path
            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            if cls._instance_locked:
                logger.warning("Resetting ModelLoader instance while VRAM lock is active.")
            cls._instance_locked = False
            if cls._instance is not None:
                try:
                    cls._instance.close()
                except Exception:
                    pass
            if cls._draft_instance is not None:
                try:
                    cls._draft_instance.close()
                except Exception:
                    pass
                cls._draft_instance = None
            cls._draft_model_path = None
            cls._instance = None
            cls._active_adapter = None
            cls._model_path = None
            
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    @classmethod
    def lock_instance(cls):
        with cls._lock:
            cls._instance_locked = True
            logger.info("ModelLoader instance VRAM lock acquired.")

    @classmethod
    def unlock_instance(cls):
        with cls._lock:
            cls._instance_locked = False
            logger.info("ModelLoader instance VRAM lock released.")

    @classmethod
    def is_instance_locked(cls) -> bool:
        with cls._lock:
            return cls._instance_locked

    @classmethod
    def context_limit(cls) -> int:
        """Return the context limit of the loaded GGUF model or config fallback."""
        return cls.n_ctx()

    @classmethod
    def model_name(cls) -> str:
        return getattr(cls, "_model_name", "none")

    @classmethod
    def n_ctx(cls) -> int:
        """Return the context window size for the loaded model."""
        with cls._lock:
            if cls._instance is not None:
                try:
                    if hasattr(cls._instance, "n_ctx"):
                        val = cls._instance.n_ctx
                        if callable(val):
                            return val()
                        return int(val)
                except Exception as e:
                    logger.warning(f"Error querying model context limit: {e}")
            
            # Fallback to active model's n_ctx
            try:
                from app.engine import config_store
                active = config_store.get_active_model()
                if active and "filename" in active:
                    return cls._read_registry_n_ctx(active["filename"])
            except Exception:
                pass
            return getattr(cls, '_n_ctx', 4096)

    @classmethod
    def is_loaded(cls) -> bool:
        with cls._lock:
            return cls._instance is not None

    @classmethod
    def is_speculative(cls) -> bool:
        """True when a draft model is attached and speculative decoding is active."""
        with cls._lock:
            return cls._draft_instance is not None

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
