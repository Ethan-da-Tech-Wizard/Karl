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


def save_example(system_prompt: str, user_msg: str, good_response: str, source: str = "thumbs_up"):
    """
    Append one training example to the curated dataset.

    Args:
        system_prompt: The system prompt active at generation time.
        user_msg:      The user's input that triggered the response.
        good_response: The accepted/corrected assistant response (no <think> block).
        source:        'thumbs_up' | 'corrected'
    """
    _ensure_dir()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "messages": [
            {"role": "system",    "content": system_prompt},
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": good_response}
        ]
    }
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
    return output_path


def export_dpo(output_path: str = "data/training/export_unsloth_dpo.jsonl") -> str:
    """
    Pairs thumbs_up/corrected (chosen) with thumbs_down (rejected) on the same prompt.
    Writes to JSONL in standard HuggingFace/Unsloth DPO format:
    {
      "prompt": [{"role": "system", "content": ...}, {"role": "user", "content": ...}],
      "chosen": [{"role": "assistant", "content": chosen_content}],
      "rejected": [{"role": "assistant", "content": rejected_content}]
    }
    """
    _ensure_dir()
    examples = get_all_examples()
    
    # Group examples by prompt key: (system_prompt, user_msg)
    groups = {}
    for ex in examples:
        messages = ex.get("messages", [])
        if len(messages) < 3:
            continue
        
        system_prompt = messages[0].get("content", "")
        user_msg = messages[1].get("content", "")
        response = messages[2].get("content", "")
        source = ex.get("source", "unknown")
        
        key = (system_prompt, user_msg)
        if key not in groups:
            groups[key] = {"chosen": [], "rejected": []}
            
        if source in ("thumbs_up", "corrected", "eval_chosen"):
            groups[key]["chosen"].append(response)
        elif source in ("thumbs_down", "eval_rejected"):
            groups[key]["rejected"].append(response)
            
    # Generate DPO pairs
    pairs = []
    for (system_prompt, user_msg), group in groups.items():
        chosen_list = group["chosen"]
        rejected_list = group["rejected"]
        
        # If we have at least one chosen and one rejected response for this prompt, pair them
        for c_resp in chosen_list:
            for r_resp in rejected_list:
                pairs.append({
                    "prompt": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    "chosen": [
                        {"role": "assistant", "content": c_resp}
                    ],
                    "rejected": [
                        {"role": "assistant", "content": r_resp}
                    ]
                })
                
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            
    return output_path


def delete_example(index: int):
    """Delete example at given 0-based index."""
    examples = get_all_examples()
    if 0 <= index < len(examples):
        examples.pop(index)
        _ensure_dir()
        with open(CURATED_PATH, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")


class TrainingCurator:
    """
    Class wrapper around the module-level curator functions.
    AppState instantiates this so workspaces can call self.state.curator.method().
    """

    def save_example(self, prompt: str, response: str,
                     source: str = "thumbs_up", system_prompt: str = ""):
        """Save a training example. Args match how Workbench calls this."""
        save_example(system_prompt, prompt, response, source)

    def get_all_examples(self):
        return get_all_examples()

    def get_stats(self):
        return get_stats()

    def export_unsloth(self, output_path: str = "data/training/export_unsloth.jsonl"):
        return export_unsloth(output_path)

    def export_dpo(self, output_path: str = "data/training/export_unsloth_dpo.jsonl"):
        return export_dpo(output_path)

    def delete_example(self, index: int):
        return delete_example(index)
