import os
import json
import threading
from llama_cpp import Llama


class ModelLoader:
    _instance = None
    _lock = threading.Lock()

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

                print(f"[ModelLoader] Loading {model_path}")
                cls._instance = Llama(model_path=model_path, n_ctx=4096, verbose=False)
                cls._model_name = os.path.basename(model_path)
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
    def is_loaded(cls) -> bool:
        with cls._lock:
            return cls._instance is not None
