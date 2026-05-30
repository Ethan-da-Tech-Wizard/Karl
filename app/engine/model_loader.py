import os
import json
import threading
from llama_cpp import Llama


class ModelLoader:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def _read_registry_n_ctx(cls, filename: str) -> int:
        """Look up n_ctx for the given model filename from model_registry.json."""
        registry_path = "data/model_registry.json"
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r") as f:
                    registry = json.load(f)
                for entry in registry:
                    if entry.get("filename") == filename:
                        return entry.get("n_ctx", 4096)
            except Exception as e:
                print(f"[ModelLoader] Could not read registry: {e}")
        return 4096

    @classmethod
    def get_instance(cls, model_path: str | None = None) -> Llama:
        with cls._lock:
            if cls._instance is None:
                if model_path is None:
                    active_path = "data/active_model.json"
                    filename = "deepseek-r1-1.5b.gguf"
                    if os.path.exists(active_path):
                        try:
                            with open(active_path, "r") as f:
                                data = json.load(f)
                                filename = data.get("filename", filename)
                        except Exception as e:
                            print(f"[ModelLoader] Could not read {active_path}: {e}")
                    model_path = os.path.join("data", "models", filename)

                if not os.path.exists(model_path):
                    fallback = "data/models/deepseek-r1-1.5b.gguf"
                    if os.path.exists(fallback):
                        print(f"[ModelLoader] {model_path} not found — using {fallback}")
                        model_path = fallback
                    else:
                        raise FileNotFoundError(
                            f"No model at {model_path} or fallback {fallback}. "
                            "Run python download_test_model.py first."
                        )

                cls._model_name = os.path.basename(model_path)
                cls._n_ctx = cls._read_registry_n_ctx(cls._model_name)
                print(f"[ModelLoader] Loading {model_path} (n_ctx={cls._n_ctx})")
                cls._instance = Llama(model_path=model_path, n_ctx=cls._n_ctx, verbose=False)
                print("[ModelLoader] Ready.")
            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            cls._instance = None

    @classmethod
    def model_name(cls) -> str:
        return getattr(cls, "_model_name", "none")

    @classmethod
    def n_ctx(cls) -> int:
        """Return the context window size for the loaded model."""
        return getattr(cls, '_n_ctx', 4096)

    @classmethod
    def is_loaded(cls) -> bool:
        with cls._lock:
            return cls._instance is not None
