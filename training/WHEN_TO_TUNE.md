# When to Prompt, Use RAG, Tune, or Upgrade

Karl's rule of thumb:

1. Try prompt structure first.
2. Use RAG for missing facts.
3. Curate examples for repeated format or behavior failures.
4. Tune only after validation shows enough clean examples.
5. Upgrade the model when the capability gap is real.

## Decision Table

| Symptom | Likely cause | Best fix |
|---|---|---|
| The answer needs information not in the model context. | Knowledge gap | Ingest the source document with RAG. |
| The fact is in context but the answer ignores it. | Prompt or grounding issue | Use `grounded_answer` and inspect retrieved chunks. |
| The answer is correct but the format drifts. | Style/format instability | Collect corrected examples and consider SFT. |
| The answer is usually right but inconsistent. | Distribution issue | Add more approved and corrected examples, then validate. |
| The task requires a repeated multi-step workflow. | Instruction complexity | Use a workflow template plus curated examples. |
| The model hallucinates despite context. | Faithfulness/reasoning issue | Tighten grounded prompt, run evals, consider larger model. |
| The behavior is correct but too slow. | Runtime/model-size issue | Use a smaller model or different quantization. |
| The model lacks the capability entirely. | Model capability gap | Upgrade model tier or use a stronger base model. |
| You need preference alignment. | Chosen/rejected preference gap | DPO, after rejected responses are captured. |

## Quick Tree

```text
Is the required fact in the context window?
  No  -> Use RAG.
  Yes -> Is the prompt/workflow clear?
          No  -> Improve template or workflow.
          Yes -> Is the failure mostly format/tone?
                  Yes -> Curate examples and consider SFT.
                  No  -> Is it a reasoning/faithfulness failure?
                          Yes -> Run evals, try grounded prompts, consider model upgrade.
                          No  -> Keep prompting; do not tune yet.
```

## Karl's Current Training Path

Karl currently supports SFT-style data collection:

1. Generate a response.
2. Click `approve` if it is good.
3. Click `teach` to write the ideal response if it is not.
4. Data is saved to `data/training/curated.jsonl`.
5. Export with the Tuning page button or:

```powershell
python -c "from app.utils.training_curator import export_unsloth; export_unsloth()"
```

The export path is:

```text
data/training/export_unsloth.jsonl
```

Each exported record uses:

```json
{"messages": [...]}
```

## Before Tuning

Run:

```powershell
python training/validate_dataset.py
```

Look for:

- At least 20 examples for any meaningful signal.
- 50+ examples for a more stable tuning run.
- Corrected examples making up a healthy share of the dataset.
- No empty messages.
- No large cluster of duplicates.
- Examples short enough for the planned sequence length.

At the current handoff, the local dataset is intentionally not tuning-ready
because it contains too few examples.

## What SFT Can Improve

- JSON or markdown response format.
- Tone and verbosity.
- Stable task-specific phrasing.
- Repeated workflow compliance.

## What SFT Will Not Reliably Fix

- Missing facts; use RAG.
- Core reasoning weakness; use a stronger model.
- Severe hallucination under new domains; improve grounding and eval first.
- Preference optimization; implement DPO data capture first.
