"""
When to Use Prompt Engineering vs RAG vs Fine-Tuning
======================================================
Decision guide for Karl Workbench. Use this before reaching for fine-tuning.

The rule: try prompting first, then RAG, then curate data, then tune.
Each step is more expensive than the last. Most failures are fixed earlier.
"""

# RAG vs Fine-Tuning Decision Guide

| Symptom | Likely Cause | Correct Fix |
|---------|-------------|-------------|
| Model answers with wrong *fact* | Knowledge gap | **RAG** — ingest the document |
| Model answers wrong *even with the fact in context* | Prompt structure or model reasoning | **Prompt engineering** — restructure template |
| Model uses the right fact but wrong *format* | Format misalignment | **SFT** — a few corrected examples fix format drift |
| Model answers correctly but *inconsistently* | Distribution issue | **SFT** — add more curated examples, balance dataset |
| Model cannot follow a complex *multi-step workflow* | Instruction complexity | **SFT + prompt structure** — use few-shot examples + clearer prompt |
| Model hallucinates details *despite having context* | Attention / faithfulness | **Grounded prompt** (`grounded_answer` template) + stricter eval |
| Model behavior correct but *too slow for the use case* | Latency issue | **Smaller model** or quantization — not a tuning problem |
| Model needs a capability not present at all | True skill gap | **Continue-pretraining** or use a larger model — SFT alone won't help |
| Model needs to *prefer* one style over another | Preference alignment | **DPO** — requires preference pairs (chosen/rejected), not just SFT |

---

## Quick Decision Tree

```
Is the answer present in the context window?
├── NO → RAG first. Ingest the relevant document.
└── YES → Is the prompt clearly structured?
          ├── NO → Prompt engineering. Use a named template (json_extractor, grounded_answer, etc.)
          └── YES → Is the failure a format/style issue?
                    ├── YES → SFT. Collect 50+ corrected examples. Run validate_dataset.py first.
                    └── NO → Is it a reasoning or faithfulness failure?
                              ├── YES → Check thought stream. Try reasoning_minimal template.
                              └── NO → Escalate: larger model tier or DPO.
```

---

## Karl's Tuning Path (SFT Only, Local)

Karl collects SFT-shaped training data through the thumbs-up / correction workflow.
The export path is: `data/training/curated.jsonl` → `export_unsloth()` → `data/training/export_unsloth.jsonl`

### Before tuning, run validate_dataset.py and check:
- **Minimum examples:** ≥ 50 (warn), ≥ 100 (recommended)
- **Balance:** corrected examples should be ≥ 20% of dataset (otherwise SFT may just memorize thumbs-up style)
- **Token length:** flag examples > 512 tokens (may need max_seq_length adjustment)
- **Schema:** every example must have system / user / assistant roles

### Realistic local tuning scope (1.5B model, CPU-only):
- QLoRA with `lora_r=16`, `lora_alpha=32`, `load_in_4bit=True`
- 3–5 epochs on ~100 corrected examples
- Training time: ~20–60 min on modern CPU (Intel 12th Gen or equivalent)
- See `training/qlora_config_template.yaml` for starter config

### What SFT fixes reliably:
- Response format (JSON structure, markdown conventions)
- Tone and verbosity
- Task-specific instruction following with consistent examples

### What SFT does NOT fix:
- Factual knowledge gaps (use RAG)
- Fundamental reasoning failures (use a larger model)
- Hallucination under distribution shift (eval first, then consider DPO)

---

## References
- Anthropic Eval Cookbook — eval before tuning
- OpenAI Fine-tuning Best Practices — quality over quantity; target remaining gaps
- QLoRA paper (Dettmers et al. 2023) — 4-bit + low-rank adapters
- Google Gemma QLoRA Guide — practical 1B-class local tuning recipe
