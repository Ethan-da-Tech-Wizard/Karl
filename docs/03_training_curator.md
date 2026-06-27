# Training Curator — Technical Reference

`app/utils/training_curator.py`

---

## Storage Paths

| Path | Contents |
|------|----------|
| `data/training/curated.jsonl` | Append-only JSONL, one example per line |
| `data/training/export_unsloth.jsonl` | SFT export (overwritten on each export) |
| `data/training/export_unsloth_dpo.jsonl` | DPO export (overwritten on each export) |
| `data/eval_results/<ts>_<model>_<adapter>.json` | Eval report snapshots |

`curated.jsonl` is append-only with no file locking.  Concurrent writers from
separate processes will race; single-process usage (the normal case) is safe.

---

## Curated Example Format

```json
{
  "timestamp": "2026-06-01T12:00:00+00:00",
  "source": "thumbs_up",
  "messages": [
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

`source` values:

| Value | Meaning |
|-------|---------|
| `thumbs_up` | User accepted the generation |
| `corrected` | User edited and accepted a corrected response |
| `thumbs_down` | User explicitly rejected the response |
| `eval_chosen` | Auto-generated: passing eval item or expected answer |
| `eval_rejected` | Auto-generated: failing eval item |

---

## SFT Export (`export_unsloth`)

```python
export_unsloth(output_path="data/training/export_unsloth.jsonl") -> str
```

Output format — only the `messages` key; no metadata:

```json
{"messages": [{"role": "system", "content": "..."}, ...]}
```

Processing steps:
1. Filter out thermally-degraded examples (those with a `"warning"` key).
2. Classify each example as `coding`, `symbolic`, or `arithmetic` based on
   keyword matching on the user message.
3. Truncate each category to `min(count_per_category)` to produce a balanced
   dataset.
4. Write all balanced examples to the output file.

Returns the output path string.

---

## DPO Export (`export_dpo`)

```python
export_dpo(output_path="data/training/export_unsloth_dpo.jsonl") -> str
```

Output format per pair:

```json
{
  "prompt":   [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "chosen":   [{"role": "assistant", "content": "..."}],
  "rejected": [{"role": "assistant", "content": "..."}]
}
```

Processing steps:
1. Filter thermally-degraded examples.
2. Group by `(system_prompt, user_msg)` key.
3. Pair each chosen (`thumbs_up` / `corrected` / `eval_chosen`) with a
   rejected (`thumbs_down` / `eval_rejected`) on the same prompt.
4. Balance across `coding` / `symbolic` / `arithmetic` categories.
5. Write balanced pairs to the output file.

Prompts with only chosen or only rejected responses are silently skipped.

---

## Eval Integration (`save_eval_result`)

```python
save_eval_result(report: dict) -> str
```

- Writes the report atomically to `data/eval_results/` via `.tmp` → `os.replace()`.
- For each item in `report["items"]`:
  - Passing item → `save_example(..., source="eval_chosen")`
  - Failing item → `save_example(..., source="eval_rejected")`
    and if `expected_answer` is provided, also saves it as `"eval_chosen"`.

This makes every eval run a source of DPO training signal without extra user action.

---

## Log Retention

The curated dataset itself has no automatic pruning — it grows without bound.
See `app/utils/trace_logger.py` for the *trace log* retention policy
(age-based + disk quota enforcement on the `.jsonl` / `.gz` / `.enc` / `.tokens` files
in `data/logs/`).
