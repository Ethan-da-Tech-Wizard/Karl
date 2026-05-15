"""
Training Data Curator — M11

Captures Karl's generations as fine-tuning examples.
Every thumbs-up (or corrected thumbs-down) is appended to
data/training/curated.jsonl in Unsloth/HuggingFace chat format.

Export via export_unsloth() to get a ready-to-train JSONL file.
"""
import os
import json
from datetime import datetime, timezone

CURATED_PATH = "data/training/curated.jsonl"


def _ensure_dir():
    os.makedirs(os.path.dirname(CURATED_PATH), exist_ok=True)


def save_example(
    system_prompt: str,
    user_msg: str,
    good_response: str,
    source: str = "thumbs_up",
    rejected_response: str | None = None,
):
    """
    Append one training example to the curated dataset.

    Args:
        system_prompt:     The system prompt active at generation time.
        user_msg:          The user's input that triggered the response.
        good_response:     The accepted/corrected assistant response (no <think> block).
        source:            'thumbs_up' | 'corrected'
        rejected_response: Original (bad) response — populated for 'corrected' examples.
                           Used to build DPO pairs.
    """
    _ensure_dir()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "messages": [
            {"role": "system",    "content": system_prompt},
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": good_response},
        ],
    }
    if rejected_response is not None:
        record["rejected"] = rejected_response
    with open(CURATED_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_all_examples() -> list:
    """Return all curated examples as a list of dicts."""
    if not os.path.exists(CURATED_PATH):
        return []
    examples = []
    with open(CURATED_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return examples


def get_stats() -> dict:
    """Return quick stats about the curated dataset."""
    examples = get_all_examples()
    thumbs_up  = sum(1 for e in examples if e.get("source") == "thumbs_up")
    corrected  = sum(1 for e in examples if e.get("source") == "corrected")
    return {
        "total":      len(examples),
        "thumbs_up":  thumbs_up,
        "corrected":  corrected,
    }


def export_unsloth(output_path: str = "data/training/export_unsloth.jsonl"):
    """
    Export the curated dataset in pure Unsloth/HuggingFace format —
    only the 'messages' field, no metadata.
    """
    _ensure_dir()
    examples = get_all_examples()
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in examples:
            out = {"messages": ex["messages"]}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    return output_path, len(examples)


def export_dpo(output_path: str = "data/training/export_dpo.jsonl"):
    """
    Export DPO (Direct Preference Optimisation) pairs.

    Only 'corrected' examples that have a stored rejected response are exported.
    Output format (compatible with TRL DPOTrainer):
      {
        "prompt":   [system_msg, user_msg],
        "chosen":   [{"role": "assistant", "content": corrected}],
        "rejected": [{"role": "assistant", "content": original}]
      }

    Returns (output_path, pair_count).
    """
    _ensure_dir()
    examples = [
        e for e in get_all_examples()
        if e.get("source") == "corrected" and e.get("rejected")
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in examples:
            msgs = ex["messages"]
            record = {
                "prompt":   [msgs[0], msgs[1]],
                "chosen":   [msgs[2]],
                "rejected": [{"role": "assistant", "content": ex["rejected"]}],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_path, len(examples)


def get_dpo_stats() -> dict:
    """Return how many DPO-ready pairs exist in the dataset."""
    examples = get_all_examples()
    dpo_ready = sum(
        1 for e in examples
        if e.get("source") == "corrected" and e.get("rejected")
    )
    return {"dpo_pairs": dpo_ready}


def delete_example(index: int):
    """Delete example at given 0-based index."""
    examples = get_all_examples()
    if 0 <= index < len(examples):
        examples.pop(index)
        _ensure_dir()
        with open(CURATED_PATH, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
