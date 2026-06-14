"""
Perplexity & Throughput Benchmarking Engine — Karl Workbench
=============================================================
Evaluates GGUF quantization variants across three axes:

  • Perplexity  — negative log-likelihood quality score (lower = better quality)
  • Throughput  — tokens/second during a 200-token generation pass
  • VRAM        — peak GPU memory footprint (model weights + KV cache)

Algorithm
─────────
  1. Tokenise a fixed 2 000-word technical evaluation corpus.
  2. Trim to --eval-tokens (default 512) and run one forward pass with
     logits_all=True so llm.logits is populated for every position.
  3. For each position i, compute softmax over logits[i] → P, then
       NLL_i = −ln P(target_token_i+1)
     Perplexity = exp(mean(NLL)).

Output
──────
  • ASCII comparison grid printed to stdout.
  • data/quantization_comparison.json  (machine-readable full report).

Usage
─────
  python eval/perplexity_bench.py
  python eval/perplexity_bench.py --models-dir data/models
  python eval/perplexity_bench.py --eval-tokens 256 --gen-tokens 100
  python eval/perplexity_bench.py --include q4        # only Q4 variants
"""

import gc
import json
import math
import multiprocessing
import os
import sys
import time
import argparse
import logging

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llama_cpp import Llama
from app.engine.model_loader import ModelLoader
from core.hardware_scout import get_hardware_profile

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("karl.perplexity_bench")

MODELS_DIR   = "data/models"
REPORT_PATH  = "data/quantization_comparison.json"
N_CTX        = 2048   # context window allocated for every benchmark model
DEFAULT_EVAL_TOKENS = 512
DEFAULT_GEN_TOKENS  = 200


# ── Evaluation corpus ─────────────────────────────────────────────────────────
# Fixed ~2 000-word technical text (no external download required).
# Held constant across all models so perplexity scores are directly comparable.

EVAL_TEXT = """\
The transformer architecture has fundamentally reshaped natural language processing.
At its core, the self-attention mechanism allows each token in a sequence to attend
to every other token, computing weighted representations based on query, key, and
value projections drawn from learned weight matrices. This parallelism over the
sequence dimension enables efficient training on modern GPU hardware using batched
matrix operations and gradient checkpointing to manage memory pressure.

Language model pretraining uses the cross-entropy loss between the predicted token
distribution and the ground-truth next token. Given a sequence of tokens t_1 through
t_N, the model learns to minimise the negative log-likelihood defined as minus one
over N times the sum of log P of t_i given all preceding tokens. Perplexity, computed
by exponentiating this average NLL, provides an interpretable measure of how surprised
a model is by held-out evaluation text. A perplexity of ten roughly means the model is
as uncertain as if it were choosing uniformly among ten equally plausible tokens at
each position, whereas a perplexity near one signals near-perfect next-token prediction.

Quantization compresses model weights from 16-bit or 32-bit floating point to lower
bit widths such as 4-bit or 8-bit integers. The GGUF format stores quantization
metadata alongside the weights, allowing llama-cpp-python to dequantize on the fly
during matrix multiplication. Q4_K_M applies a mixed strategy: attention projection
matrices receive 6-bit quantization to preserve the fidelity of attention patterns,
while the larger feed-forward layers are compressed to 4-bit, balancing file size
reduction against quality degradation. Q8_0 uses uniform 8-bit quantization and
produces perplexity scores nearly indistinguishable from the full-precision baseline
at roughly half the storage footprint.

Modern speculative decoding pairs a large target model with a smaller and faster draft
model. The draft generates k candidate tokens in a single autoregressive pass. The
target model then verifies or rejects each candidate token in a single parallel forward
pass. Accepted tokens are committed to the output buffer. At the first rejection, the
draft sequence is discarded and the target regenerates from that position. This achieves
wall-clock speedups of two to four times without altering the output distribution of
the target model, because the acceptance criterion preserves the target's probability
distribution through a corrective rejection sampling step.

Retrieval-augmented generation extends the effective knowledge horizon of a language
model by injecting external document chunks into the prompt context at inference time.
A dense passage retriever embeds both the query and the entire corpus into the same
high-dimensional vector space using a bi-encoder architecture, then performs
approximate nearest-neighbour search using HNSW or IVF indices to identify the top-k
most semantically similar passages. The retrieved passages are concatenated with the
user query and passed to the generator, which conditions its output on the in-context
evidence rather than relying exclusively on the parametric knowledge encoded in its
weights during pretraining.

Memory bandwidth is the dominant bottleneck during autoregressive decoding because each
forward pass must read all model weight matrices once from GPU memory to produce a
single output token. For a seven-billion-parameter model stored at four bits per
parameter, the total weight storage is approximately 3.5 gigabytes. A consumer GPU
offering 200 gigabytes per second of memory bandwidth can transfer this weight matrix
in approximately 17 milliseconds, placing a physical ceiling of around 60 tokens per
second on single-batch throughput regardless of batch size or compute intensity.
Batching multiple independent requests amortises the bandwidth cost across the batch,
improving total system throughput while introducing additional latency for each
individual sequence in the batch due to the increased key-value cache size.

Instruction tuning fine-tunes a pretrained base model on curated demonstration data
consisting of instruction-response pairs, aligning the model output distribution with
human intent without altering the underlying representation learned during pretraining.
Direct preference optimisation provides a closed-form alternative to reinforcement
learning from human feedback by directly optimising the policy against a dataset of
paired preferred and rejected responses. The DPO objective implicitly defines a latent
reward model through the log-ratio of the updated policy and a frozen reference model,
eliminating the need for an explicit reward network and stabilising training by avoiding
the high variance associated with on-policy rollouts and reward model overoptimisation.

Mixture-of-experts architectures scale model capacity without proportionally increasing
the active parameter count at each forward pass. A learned router network produces a
probability distribution over a large set of expert feed-forward layers and selects
the top-k experts for each token. Auxiliary load-balancing losses during training
encourage uniform routing across experts to prevent collapse, where a small subset of
experts receives the majority of tokens while the remainder become undertrained. At
inference time, the routing decision is made per token per layer, enabling fine-grained
specialisation: some experts may implicitly learn to handle syntactic constructs while
others develop domain-specific reasoning capabilities in factual or mathematical domains.

Graph neural networks extend the convolution operation from regular grid topologies to
arbitrary irregular graph structures defined by an adjacency matrix. Message passing
schemes iteratively update each node embedding by aggregating transformed embeddings
from its one-hop neighbourhood followed by a nonlinear activation function. Attention-
based aggregation weights each neighbouring node contribution by a learned compatibility
score computed between the central node and each neighbour embedding, enabling the
network to dynamically focus on the most informative edges in heterogeneous graphs
containing multiple node and edge types with differing feature dimensionalities.

Positional encodings inject sequence order information into token embeddings before the
transformer layers process them. Sinusoidal encodings use fixed trigonometric functions
at increasing frequencies so that nearby positions produce similar encodings while
distant positions are clearly separated in the embedding space. Rotary position
embeddings apply a rotation matrix in the complex plane directly to the query and key
vectors within each attention head at each layer, allowing relative position information
to emerge naturally from the dot-product similarity computation without modifying the
value projections. Alibi and YARN extend the effective context window beyond the
training length by modifying the attention bias term rather than the embeddings
themselves, enabling generalisation to sequences substantially longer than those seen
during pretraining without catastrophic degradation of perplexity on in-distribution
text.
""".strip()


# ── VRAM measurement ──────────────────────────────────────────────────────────

def _query_free_vram_mb() -> float:
    """Sum of free VRAM across all GPUs in MB; 0.0 if GPUtil is unavailable."""
    try:
        profile = get_hardware_profile()
        return sum(g.get("memory_free_mb", 0.0) for g in profile.get("gpu_list", []))
    except Exception:
        return 0.0


def _vram_used_since(free_before: float) -> float:
    """MB consumed relative to a prior free-memory baseline; 0.0 on failure."""
    free_now = _query_free_vram_mb()
    if free_before <= 0.0 or free_now <= 0.0:
        return 0.0
    return round(max(0.0, free_before - free_now), 1)


# ── Softmax ───────────────────────────────────────────────────────────────────

def _softmax(logits_slice) -> np.ndarray:
    """Numerically stable softmax over a flat sequence of float logits."""
    arr = np.asarray(logits_slice, dtype=np.float32)
    arr -= arr.max()          # shift for numerical stability before exp
    e = np.exp(arr)
    return e / e.sum()


# ── Perplexity engine ─────────────────────────────────────────────────────────

def compute_perplexity(llm: Llama, eval_text: str, max_eval_tokens: int) -> float:
    """
    Compute the perplexity of *eval_text* under *llm* using the NLL formulation:

        Perplexity = exp( (1/N) Σ −ln P(token_i | token_1..token_{i-1}) )

    Requires the model to have been loaded with logits_all=True so that
    llm.logits is a flat buffer of shape (n_past × n_vocab) after llm.eval().

    Returns float('inf') on tokenisation or logit-buffer failures.
    """
    # --- tokenise and trim ------------------------------------------------
    encoded_text = eval_text.encode("utf-8", errors="replace")
    try:
        tokens = llm.tokenize(encoded_text, add_bos=True)
    except Exception as exc:
        logger.warning("tokenize() failed: %s", exc)
        return float("inf")

    # +1 so we have a target for the last prefix position
    tokens = list(tokens[: max_eval_tokens + 1])
    if len(tokens) < 2:
        return float("inf")

    prefix = tokens[:-1]   # feed these to the model
    targets = tokens[1:]   # predict these at each position

    # --- single forward pass ----------------------------------------------
    llm.reset()
    try:
        llm.eval(prefix)
    except Exception as exc:
        logger.warning("llm.eval() failed: %s", exc)
        llm.reset()
        return float("inf")

    n_vocab   = llm.n_vocab()
    all_logits = llm.logits  # flat list: len = n_past * n_vocab

    expected_len = len(prefix) * n_vocab
    if len(all_logits) < expected_len:
        logger.warning(
            "logits buffer too short (%d < %d) — model may not have logits_all=True",
            len(all_logits), expected_len,
        )
        llm.reset()
        return float("inf")

    # --- NLL accumulation -------------------------------------------------
    nlls: list[float] = []
    for i, target_id in enumerate(targets):
        start = i * n_vocab
        probs = _softmax(all_logits[start : start + n_vocab])

        if target_id < 0 or target_id >= n_vocab:
            continue
        p = float(probs[target_id])
        if p > 0.0:
            nlls.append(-math.log(p))

    llm.reset()

    if not nlls:
        return float("inf")

    return round(math.exp(sum(nlls) / len(nlls)), 4)


# ── Throughput measurement ────────────────────────────────────────────────────

_THROUGHPUT_SEED = (
    "The following is a detailed technical explanation of how transformer-based "
    "language models perform autoregressive text generation:"
)


def measure_throughput(llm: Llama, gen_tokens: int) -> float:
    """
    Generate *gen_tokens* tokens from a fixed seed prompt and return tok/s.
    Uses temperature=1.0 so the model exercises its full sampling path.
    """
    t0 = time.perf_counter()
    output = llm(
        _THROUGHPUT_SEED,
        max_tokens=gen_tokens,
        temperature=1.0,
        top_k=40,
        repeat_penalty=1.1,
        echo=False,
    )
    elapsed = time.perf_counter() - t0

    # Prefer the usage field; fall back to gen_tokens if unavailable.
    generated = gen_tokens
    try:
        generated = output["usage"]["completion_tokens"]
    except (KeyError, TypeError):
        pass

    return round(generated / elapsed, 2) if elapsed > 0.0 else 0.0


# ── Memory cleanup ────────────────────────────────────────────────────────────

def _release_model(llm: Llama | None) -> None:
    """Close *llm* and release GPU/CPU memory as thoroughly as possible."""
    if llm is not None:
        try:
            llm.close()
        except Exception:
            pass
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


# ── Per-model benchmark ───────────────────────────────────────────────────────

def benchmark_model(
    model_path: str,
    eval_tokens: int,
    gen_tokens: int,
) -> dict:
    """
    Load *model_path* with logits_all=True, measure perplexity + throughput +
    VRAM, then unload cleanly.  Never raises — errors are returned in "error".
    """
    filename = os.path.basename(model_path)
    file_gb  = round(os.path.getsize(model_path) / (1024 ** 3), 3)
    threads  = max(1, multiprocessing.cpu_count() - 2)

    result: dict = {
        "filename":        filename,
        "file_gb":         file_gb,
        "perplexity":      None,
        "throughput_tps":  None,
        "peak_vram_mb":    None,
        "error":           None,
    }

    free_before = _query_free_vram_mb()
    llm: Llama | None = None

    try:
        print(f"    Loading …", end=" ", flush=True)
        llm = Llama(
            model_path=model_path,
            n_ctx=N_CTX,
            n_gpu_layers=-1,
            logits_all=True,   # required: populates llm.logits for all positions
            n_threads=threads,
            verbose=False,
        )
        print("done", flush=True)
    except Exception as exc:
        print(f"FAILED ({exc})", flush=True)
        result["error"] = f"Load failed: {exc}"
        _release_model(None)
        return result

    try:
        # ── (1) Perplexity ────────────────────────────────────────────────
        print(f"    Perplexity ({eval_tokens} tokens) …", end=" ", flush=True)
        ppl = compute_perplexity(llm, EVAL_TEXT, eval_tokens)
        result["perplexity"] = ppl
        print(f"{ppl:.2f}", flush=True)

        # ── (2) Throughput ────────────────────────────────────────────────
        print(f"    Throughput ({gen_tokens} tokens) …", end=" ", flush=True)
        tps = measure_throughput(llm, gen_tokens)
        result["throughput_tps"] = tps
        print(f"{tps:.1f} tok/s", flush=True)

        # ── (3) Peak VRAM -─────────────────────────────────────────────────
        # Free memory is lowest (VRAM usage is highest) during active inference.
        # We take the reading after both eval passes to capture the loaded state.
        result["peak_vram_mb"] = _vram_used_since(free_before)

    except Exception as exc:
        result["error"] = f"Eval failed: {exc}"
        logger.exception("Benchmark error for %s", filename)

    finally:
        _release_model(llm)
        llm = None

    return result


# ── ASCII grid printer ────────────────────────────────────────────────────────

def _fmt(value, spec: str, missing: str = "—") -> str:
    return missing if value is None else format(value, spec)


def print_ascii_grid(results: list[dict]) -> None:
    bar = "═" * 82
    thin = "─" * 82
    print(f"\n{bar}")
    print(f"  {'GGUF QUANTIZATION COMPARISON':^78}")
    print(f"{bar}")
    print(
        f"  {'Model':<32}  {'Size(GB)':>8}  {'PPL':>8}  {'tok/s':>7}  "
        f"{'VRAM MB':>8}  {'Status':<8}"
    )
    print(f"  {'─'*32}  {'─'*8}  {'─'*8}  {'─'*7}  {'─'*8}  {'─'*8}")
    for r in results:
        name = r["filename"]
        if len(name) > 31:
            name = name[:28] + "..."
        status = "ERROR" if r.get("error") else "OK"
        print(
            f"  {name:<32}  "
            f"{_fmt(r.get('file_gb'),       '.3f'):>8}  "
            f"{_fmt(r.get('perplexity'),    '.2f'):>8}  "
            f"{_fmt(r.get('throughput_tps'),'.1f'):>7}  "
            f"{_fmt(r.get('peak_vram_mb'),  '.0f'):>8}  "
            f"{status:<8}"
        )
        if r.get("error"):
            print(f"    ↳ {r['error']}")
    print(f"{thin}")
    print("  PPL:    Lower perplexity → better language-modelling quality")
    print("  tok/s:  Higher throughput → faster generation speed")
    print("  VRAM:   Peak footprint measured against free-memory baseline")
    print(f"{bar}\n")


# ── Main benchmarking loop ────────────────────────────────────────────────────

def run_benchmark(
    models_dir: str  = MODELS_DIR,
    eval_tokens: int = DEFAULT_EVAL_TOKENS,
    gen_tokens: int  = DEFAULT_GEN_TOKENS,
    report_path: str = REPORT_PATH,
    include: str | None = None,
) -> list[dict]:
    """
    Scan *models_dir* for GGUF files and benchmark each sequentially.
    Writes the combined result to *report_path* as JSON.
    Returns the list of result dicts (empty list on directory error).
    """
    if not os.path.isdir(models_dir):
        print(f"ERROR: models directory not found: {models_dir}", file=sys.stderr)
        return []

    gguf_files = sorted(f for f in os.listdir(models_dir) if f.lower().endswith(".gguf"))
    if include:
        needle = include.lower()
        gguf_files = [f for f in gguf_files if needle in f.lower()]

    if not gguf_files:
        print(f"No GGUF files found in {models_dir}", file=sys.stderr)
        return []

    bar = "─" * 82
    print(f"\n{bar}")
    print(f"  Karl GGUF Quantization Perplexity & Throughput Benchmark")
    print(f"  Models dir  : {models_dir}  ({len(gguf_files)} GGUF files)")
    print(f"  Eval tokens : {eval_tokens}   Gen tokens : {gen_tokens}")
    print(f"  Report path : {report_path}")
    print(f"{bar}\n")

    results: list[dict] = []
    for idx, filename in enumerate(gguf_files, 1):
        model_path = os.path.join(models_dir, filename)
        print(f"  [{idx}/{len(gguf_files)}] {filename}  ({os.path.getsize(model_path)/(1024**3):.2f} GB)")
        r = benchmark_model(model_path, eval_tokens, gen_tokens)
        results.append(r)
        print()

    print_ascii_grid(results)

    # ── Save JSON report ──────────────────────────────────────────────────────
    report_dir = os.path.dirname(os.path.abspath(report_path))
    os.makedirs(report_dir, exist_ok=True)
    payload = {
        "eval_tokens": eval_tokens,
        "gen_tokens":  gen_tokens,
        "models_dir":  models_dir,
        "results":     results,
    }
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"  Report saved → {report_path}\n")

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Karl GGUF Quantization Perplexity & Throughput Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python eval/perplexity_bench.py\n"
            "  python eval/perplexity_bench.py --include q4_k\n"
            "  python eval/perplexity_bench.py --eval-tokens 256 --gen-tokens 100\n"
        ),
    )
    parser.add_argument(
        "--models-dir", "-m",
        default=MODELS_DIR,
        help=f"Directory to scan for GGUF files (default: {MODELS_DIR})",
    )
    parser.add_argument(
        "--eval-tokens", "-e",
        type=int, default=DEFAULT_EVAL_TOKENS, metavar="N",
        help=f"Tokens for perplexity evaluation (default: {DEFAULT_EVAL_TOKENS})",
    )
    parser.add_argument(
        "--gen-tokens", "-g",
        type=int, default=DEFAULT_GEN_TOKENS, metavar="N",
        help=f"Tokens generated for throughput measurement (default: {DEFAULT_GEN_TOKENS})",
    )
    parser.add_argument(
        "--report", "-r",
        default=REPORT_PATH,
        help=f"Output JSON report path (default: {REPORT_PATH})",
    )
    parser.add_argument(
        "--include", "-i",
        default=None, metavar="SUBSTR",
        help="Only benchmark models whose filename contains SUBSTR (case-insensitive)",
    )
    args = parser.parse_args()

    results = run_benchmark(
        models_dir  = args.models_dir,
        eval_tokens = args.eval_tokens,
        gen_tokens  = args.gen_tokens,
        report_path = args.report,
        include     = args.include,
    )
    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
