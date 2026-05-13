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
                n_ctx=2048,
                verbose=False
            )
            print("Model loaded.")
        return cls._instance
