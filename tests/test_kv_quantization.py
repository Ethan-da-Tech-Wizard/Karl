from unittest.mock import MagicMock, patch


def _reset_model_loader_state(ModelLoader):
    ModelLoader._instance = None
    ModelLoader._instance_locked = False
    ModelLoader._active_generation_count = 0
    ModelLoader._model_path = None
    ModelLoader._active_adapter = None
    ModelLoader._adapter_offloaded = False
    ModelLoader._draft_instance = None
    ModelLoader._draft_model_path = None


def _run_loader_with_patches(fake_llama):
    from app.engine.model_loader import ModelLoader

    orig = {
        "instance": ModelLoader._instance,
        "locked": ModelLoader._instance_locked,
        "count": ModelLoader._active_generation_count,
        "model_path": ModelLoader._model_path,
        "adapter": ModelLoader._active_adapter,
        "offloaded": ModelLoader._adapter_offloaded,
        "draft_instance": ModelLoader._draft_instance,
        "draft_model_path": ModelLoader._draft_model_path,
    }

    try:
        _reset_model_loader_state(ModelLoader)
        with patch("app.engine.model_loader.Llama", side_effect=fake_llama), \
             patch.object(
                 ModelLoader,
                 "_resolve_model_path",
                 return_value="data/models/deepseek-r1-1.5b.gguf",
             ), \
             patch.object(ModelLoader, "preflight_model_load", return_value=None), \
             patch.object(ModelLoader, "_bench_vram_bandwidth", return_value=None), \
             patch.object(ModelLoader, "_ggml_type_q8_0", return_value=8), \
             patch("app.engine.model_loader.get_hardware_profile", return_value={"gpu_list": []}), \
             patch("app.engine.config_store.get_ui_config", return_value={"quantized_kv_cache": True}), \
             patch("app.engine.config_store.read_json", return_value={}), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            try:
                ModelLoader.get_instance(model_path="data/models/deepseek-r1-1.5b.gguf")
            except RuntimeError:
                pass
    finally:
        ModelLoader._instance = orig["instance"]
        ModelLoader._instance_locked = orig["locked"]
        ModelLoader._active_generation_count = orig["count"]
        ModelLoader._model_path = orig["model_path"]
        ModelLoader._active_adapter = orig["adapter"]
        ModelLoader._adapter_offloaded = orig["offloaded"]
        ModelLoader._draft_instance = orig["draft_instance"]
        ModelLoader._draft_model_path = orig["draft_model_path"]


def test_quantized_kv_cache_passes_q8_type_overrides_to_llama():
    captured_kwargs = []

    def fake_llama(**kwargs):
        captured_kwargs.append(kwargs)
        raise RuntimeError("stop after constructor capture")

    _run_loader_with_patches(fake_llama)

    assert captured_kwargs, "Llama() was never called"
    assert captured_kwargs[0]["type_k"] == 8
    assert captured_kwargs[0]["type_v"] == 8


def test_quantized_kv_cache_falls_back_when_type_overrides_are_unsupported():
    captured_kwargs = []
    loaded = MagicMock()

    def fake_llama(**kwargs):
        captured_kwargs.append(dict(kwargs))
        if "type_k" in kwargs or "type_v" in kwargs:
            raise TypeError("unexpected keyword argument 'type_k'")
        return loaded

    _run_loader_with_patches(fake_llama)

    assert len(captured_kwargs) >= 2
    assert captured_kwargs[0]["type_k"] == 8
    assert captured_kwargs[0]["type_v"] == 8
    assert "type_k" not in captured_kwargs[1]
    assert "type_v" not in captured_kwargs[1]
