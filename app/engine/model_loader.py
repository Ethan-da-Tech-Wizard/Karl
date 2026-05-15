import os
from llama_cpp import Llama

class ModelLoader:
    _instance = None

    @classmethod
    def get_instance(cls, model_path="data/models/deepseek-r1-1.5b.gguf"):
        if cls._instance is None:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found at {model_path}")
            print("Loading model...")
            cls._instance = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=-1,  # offload all layers to GPU if available, 0 = CPU only
                verbose=False,
            )
            print("Model loaded.")
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Force a full reload on next get_instance() call. Use when changing n_ctx."""
        cls._instance = None
