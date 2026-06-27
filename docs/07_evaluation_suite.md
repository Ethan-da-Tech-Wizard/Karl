# Karl — Evaluation Suite

Karl's evaluation harness lets you benchmark the active local model and
adapter against structured JSONL datasets — entirely offline. It is
accessible from the Eval Suite workspace in the PyQt6 app and from the
CLI via `eval/run_eval.py`.

---

## Architecture

```
eval/
├── harness.py         ← EvalHarness class + CaseResult/EvalReport dataclasses
├── graders.py         ← 5 pure-function graders + GRADER_REGISTRY
├── run_eval.py        ← CLI entry point
├── benchmark_rag.py   ← RAG retrieval benchmarking tool
└── datasets/          ← eval JSONL datasets (source-controlled)
```

---

## Dataset JSONL Format

Each line of an eval dataset is a JSON object:

```json
{
  "id":           "unique-case-id",
  "prompt":       "User question or instruction",
  "context":      "Optional inline context (used if no context_file or RAG)",
  "context_file": "Optional path to a .txt/.md file to use as context",
  "expected":     "Expected answer (string or JSON depending on grader)",
  "grader":       "exact_match | json_valid | keyword_hit | groundedness | not_in_context",
  "schema_keys":  ["key1", "key2"],
  "keywords":     ["word1", "word2"],
  "require_all":  true
}
```

Lines beginning with `#` and blank lines are silently skipped.

---

## EvalHarness

`eval/harness.py` — `class EvalHarness`

### Constructor

```python
EvalHarness(rag_pipeline=None)
```

- `rag_pipeline`: Optional pre-initialised `RAGPipeline`. If `None`, RAG
  retrieval is skipped and context falls back to `context_file` or the
  inline `context` field.

### `run()` Method

```python
EvalHarness.run(
    dataset_path:      str,
    workflow_name:     str,
    template_override: str | None = None,
    hyperparams:       dict | None = None,
    progress_cb:       Callable[[int, int], None] | None = None,
    model_name:        str | None = None,
    adapter_name:      str | None = None,
) -> EvalReport
```

#### Pre-flight Model Guard

Before any case executes the harness calls `ModelLoader.get_instance()` and
raises `RuntimeError` with a user-friendly message if the model file is
missing. This prevents the obscure `FileNotFoundError` from surfacing mid-loop.

On multi-GPU hosts the guard also runs a dummy 1-token generation to verify
CUDA device synchronization before the first real case.

#### Per-Case Loop

For each case in the dataset:

1. `progress_cb(current, total)` is called if provided (wires to the Eval
   Suite progress bar in the UI).
2. **Context resolution** (`_resolve_context`): RAG retrieval > `context_file` > inline `context`.
3. **System prompt construction** (`_build_system_prompt`): calls
   `get_template(template_name, rag_context=..., schema=..., code=...)`.
4. **Model generation** (`_run_model`): calls `ModelLoader.get_instance()`
   → `build_prompt()` → `llm()` → strips `<think>...</think>` from output
   before grading.
5. **Dynamic timeout**: timeout per case = `max(60s, rolling_avg_latency × 3)`.
   Cases that exceed this are aborted via `executor.submit().result(timeout=...)`.
   After a timeout `ModelLoader.unlock_instance()` is called to release any
   held lock.
6. **Grading** (`_grade`): dispatches to the named grader function.
7. **Eval-failure curation**: if a case fails grading, the harness saves
   the expected answer as `eval_chosen` and the model's actual output as
   `eval_rejected` to `data/training/curated.jsonl` (feeds the DPO pipeline).

#### Post-Run

- Aggregated `EvalReport` (pass rate, avg latency, avg score, per-case list) is returned.
- A summary JSON is written to `data/eval_last.json` for the Flywheel dashboard.

### `save_report()` Method

```python
EvalHarness.save_report(report: EvalReport, output_dir: str = "eval/results") -> str
```

Writes a timestamped JSONL file. First line is `{"type": "summary", ...}`;
subsequent lines are `{"type": "case", ...}` for each case result.

---

## EvalReport & CaseResult

```python
@dataclass
class CaseResult:
    case_id:      str
    prompt:       str
    workflow:     str
    template:     str
    output:       str
    grader:       str
    grade:        dict          # {passed: bool, score: float, detail: str}
    latency_s:    float
    context_used: list[str]
    error:        str | None

@dataclass
class EvalReport:
    workflow:       str
    template:       str
    dataset:        str
    total:          int
    passed:         int
    failed:         int
    errors:         int
    pass_rate:      float
    avg_latency_s:  float
    avg_score:      float
    timestamp:      str         # ISO 8601 UTC
    cases:          list[CaseResult]
```

---

## Graders

All graders are pure functions in `eval/graders.py`. Every grader returns:

```python
{"passed": bool, "score": float, "detail": str}
```

They are side-effect-free and can run in CI, the headless harness, or
interactively.

### 1. `exact_match`

```python
exact_match(output: str, expected: str) -> dict
```

Passes if `output.strip().lower() == expected.strip().lower()`.
Score is binary: `1.0` pass, `0.0` fail.
Best for: short deterministic answers (IDs, labels, yes/no).

### 2. `json_valid`

```python
json_valid(output: str, schema_keys: list[str] | None = None) -> dict
```

Strips markdown fences (` ```json ... ``` `) then parses the output as JSON.
If `schema_keys` is provided, checks that all keys exist in the top-level
object (or the first element if the output is a JSON array).
Score is partial: `(found_keys / total_keys)` when some keys are missing.
An empty JSON array is an accepted pass (model correctly found no findings).

### 3. `keyword_hit`

```python
keyword_hit(output: str, keywords: list[str], require_all: bool = True) -> dict
```

Checks whether the output contains the required keywords (case-insensitive).
- `require_all=True` (default): ALL keywords must appear → binary pass/fail.
- `require_all=False`: ANY one keyword suffices → binary pass/fail.
Score is always `hits / total_keywords`.

### 4. `groundedness`

```python
groundedness(output: str, context_chunks: list[str], min_overlap_words: int = 3) -> dict
```

Measures whether the model's output is grounded in the retrieved context
chunks.

Algorithm:
1. Build a flat word set from all context chunks.
2. Split the output into sentences on `.`, `!`, `?`.
3. For each sentence with ≥ 4 words: check if it shares ≥ `min_overlap_words`
   words with the context word set.
4. Sentences with < 4 words receive the benefit of the doubt (counted as grounded).
5. Score = `grounded_sentences / total_sentences`.
6. Passes if score ≥ **60%**.

Also immediately passes (score 1.0) if the output contains the string
`"NOT IN CONTEXT"` — this is the correct refusal behaviour.

### 5. `not_in_context`

```python
not_in_context(output: str) -> dict
```

Inverse of `groundedness`: passes **only** when the model's output contains
`"NOT IN CONTEXT"` (case-insensitive). Used in cases where the expected answer
is the refusal itself (i.e. the question has no answer in the retrieved docs).

---

## Grader Registry

```python
GRADER_REGISTRY: dict[str, callable] = {
    "exact_match":   exact_match,
    "json_valid":    json_valid,
    "keyword_hit":   keyword_hit,
    "groundedness":  groundedness,
    "not_in_context": not_in_context,
}

run_grader(name: str, output: str, **kwargs) -> dict
```

`run_grader` dispatches by name and raises `KeyError` if the name is not
registered. Dataset JSONL files reference graders by their registry key.

---

## Context Resolution Priority

```
RAG retrieval (if rag_pipeline != None and workflow.rag_top_k > 0)
  → context_file (if case["context_file"] exists on disk)
    → inline context field (case["context"])
      → [] (no context)
```

---

## CLI Usage

```bash
# Minimal
python eval/run_eval.py \
    --workflow grounded_answer \
    --dataset eval/datasets/grounded_answer.jsonl

# Full options
python eval/run_eval.py \
    --workflow grounded_answer \
    --dataset eval/datasets/grounded_answer.jsonl \
    --template reasoning_minimal \
    --model deepseek-r1-7b.gguf \
    --adapter math_solver \
    --output eval/results/ \
    --dry-run
```

---

## Eval Failure DPO Pipeline

Every failed eval case is automatically saved to the training curator
so the failures can be used to improve the model:

- The **expected answer** is saved with `source="eval_chosen"`.
- The **model's actual output** is saved with `source="eval_rejected"`.

In Training Studio → Export tab, `export_dpo()` pairs `eval_chosen` with
`eval_rejected` examples on the same prompt to produce a DPO training
dataset for Unsloth.

---

## Test Suite

Unit tests for the evaluation suite:

| Test File | Coverage |
|-----------|----------|
| `tests/test_eval_harness.py` | Harness run loop, case processing, report structure |
| `tests/test_cognitive_parser.py` | `parse_thought_stream` with normal and edge inputs |
| `tests/test_cognitive_parser_fuzz.py` | Fuzz tests: malformed tags, truncated streams, capslock variants |
| `tests/test_hardware_scout.py` | `get_hardware_profile()` return structure |

---

## Integration with Flywheel

The Eval Suite is the measurement stage of Karl's self-improvement flywheel:

```
Eval run
  → pass_rate saved to data/eval_last.json
  → failures curated as eval_chosen/eval_rejected pairs
  → Training Studio exports DPO dataset
  → LoRA/QLoRA training produces a new adapter
  → New adapter loaded in ModelLoader
  → Eval run again to measure improvement
```
