import argparse
import importlib.util
from pathlib import Path

import pytest

from tools.auto_train_lora import build_sft_config_kwargs, detect_target_modules


class FakeModel:
    def named_modules(self):
        names = [
            "model.layers.0.self_attn.q_proj",
            "model.layers.0.self_attn.k_proj",
            "model.layers.0.self_attn.v_proj",
            "model.layers.0.self_attn.o_proj",
            "model.layers.0.mlp.gate_proj",
            "model.layers.0.mlp.up_proj",
            "model.layers.0.mlp.down_proj",
            "lm_head",
        ]
        return [(name, object()) for name in names]


def test_detect_target_modules_keeps_known_projection_order():
    assert detect_target_modules(FakeModel()) == [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]


def test_detect_target_modules_has_attention_fallback():
    class EmptyModel:
        def named_modules(self):
            return [("embed_tokens", object())]

    assert detect_target_modules(EmptyModel()) == ["q_proj", "v_proj"]


def test_build_sft_config_enables_packing_and_cosine_schedule():
    args = argparse.Namespace(
        max_length=4096,
        batch_size=1,
        grad_accum=8,
        lr=2e-4,
        warmup_ratio=0.03,
        epochs=1,
        logging_steps=1,
    )

    kwargs = build_sft_config_kwargs(args, Path("data/adapters/test/checkpoints"))

    assert kwargs["packing"] is True
    assert kwargs["max_length"] == 4096
    assert kwargs["lr_scheduler_type"] == "cosine"
    assert kwargs["warmup_ratio"] == 0.03
    assert kwargs["dataset_text_field"] == "text"


def test_sft_config_accepts_packing_and_cosine_kwargs_when_trl_available():
    if importlib.util.find_spec("trl") is None:
        pytest.skip("trl not installed")
    from trl import SFTConfig

    args = argparse.Namespace(
        max_length=4096,
        batch_size=1,
        grad_accum=8,
        lr=2e-4,
        warmup_ratio=0.03,
        epochs=1,
        logging_steps=1,
    )
    cfg = SFTConfig(**build_sft_config_kwargs(args, Path("data/adapters/test/checkpoints")))

    assert cfg.packing is True
    assert cfg.max_length == 4096
    assert str(cfg.lr_scheduler_type) == "SchedulerType.COSINE"
