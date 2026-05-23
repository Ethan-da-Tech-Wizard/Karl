import os
import json
from llama_cpp import Llama

class ModelLoader:
    _instance = None

    @classmethod
    def get_instance(cls, model_path=None):
        if cls._instance is None:
            if model_path is None:
                # Load from data/active_model.json if exists, else default
                active_path = "data/active_model.json"
                filename = "deepseek-r1-1.5b.gguf"
                if os.path.exists(active_path):
                    try:
                        with open(active_path, "r") as f:
                            active_data = json.load(f)
                            filename = active_data.get("filename", "deepseek-r1-1.5b.gguf")
                    except Exception as e:
                        print(f"[ModelLoader] Error reading {active_path}: {e}")
                model_path = os.path.join("data", "models", filename)

            if not os.path.exists(model_path):
                # Fallback to default if upgraded model is missing
                default_path = "data/models/deepseek-r1-1.5b.gguf"
                if os.path.exists(default_path):
                    print(f"[ModelLoader] Specified model {model_path} not found. Falling back to default: {default_path}")
                    model_path = default_path
                else:
                    raise FileNotFoundError(f"Model not found at {model_path} or fallback {default_path}")

            print(f"[ModelLoader] Loading model from {model_path}...")
            cls._instance = Llama(
                model_path=model_path,
                n_ctx=4096,   # Increased from 2048 to support agentic loops
                verbose=False
            )
            print("[ModelLoader] Model loaded.")
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Force a full reload on next get_instance() call. Use when changing n_ctx."""
        cls._instance = None
