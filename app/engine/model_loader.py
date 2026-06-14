import logging
import os
import threading
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

                if lora_path:
                    logger.info(f"Loading {model_path} with LoRA adapter {lora_path} (n_ctx={cls._n_ctx})")
                    cls._instance = Llama(
                        model_path=model_path,
                        n_ctx=cls._n_ctx,
                        lora_path=lora_path,
                        n_gpu_layers=-1,
                        verbose=False
                    )
                else:
                    logger.info(f"Loading {model_path} (n_ctx={cls._n_ctx})")
                    cls._instance = Llama(
                        model_path=model_path,
                        n_ctx=cls._n_ctx,
                        n_gpu_layers=-1,
                        verbose=False
                    )
                logger.info("Ready.")

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
                            cls._draft_instance = _LlamaInner(
                                model_path=draft_model_path,
                                n_ctx=cls._n_ctx,
                                n_gpu_layers=-1,
                                verbose=False,
                            )
                            # Re-instantiate primary model wired to the draft instance.
                            # llama-cpp-python exposes speculative decoding via the draft_model kwarg
                            # (available since 0.2.77). If the installed version lacks this kwarg,
                            # catch TypeError and continue without speculative support.
                            try:
                                cls._instance.close()
                                cls._instance = Llama(
                                    model_path=cls._model_path,
                                    n_ctx=cls._n_ctx,
                                    n_gpu_layers=-1,
                                    verbose=False,
                                    draft_model=cls._draft_instance,
                                )
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
