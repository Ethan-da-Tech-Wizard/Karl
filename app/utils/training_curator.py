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
EVAL_RESULTS_DIR = "data/eval_results"


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


def _is_degraded(record: dict) -> bool:
    """Return True if the record carries a thermal/latency warning flag."""
    return "warning" in record


def _classify_example(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if "python" in prompt_lower or "code block" in prompt_lower or "def solve" in prompt_lower:
        return "coding"
    elif "matrix" in prompt_lower or "determinant" in prompt_lower or "graph" in prompt_lower or "vertices" in prompt_lower or "committee" in prompt_lower:
        return "symbolic"
    else:
        return "arithmetic"


def export_unsloth(output_path: str = "data/training/export_unsloth.jsonl"):
    """
    Export the curated dataset in pure Unsloth/HuggingFace format —
    only the 'messages' field, no metadata.
    Maintains balanced classes by down-sampling over-represented categories.
    """
    _ensure_dir()
    raw = get_all_examples()
    examples = [ex for ex in raw if not _is_degraded(ex)]
    skipped = len(raw) - len(examples)
    print(f"Curation Curation: Exported {len(examples)} examples. Filtered out {skipped} degraded examples.")

    # Classify all examples
    categorized = {}
    for ex in examples:
        messages = ex.get("messages", [])
        if len(messages) < 2:
            continue
        user_msg = messages[1].get("content", "")
        cat = _classify_example(user_msg)
        categorized.setdefault(cat, []).append(ex)
        
    if not categorized:
        return output_path
        
    # Find the minimum non-zero count of examples in any category to establish the balancing cap
    counts = [len(lst) for lst in categorized.values()]
    min_count = min(counts) if counts else 0
    
    # Balance the dataset by slicing up to min_count for each category
    balanced_examples = []
    for cat, lst in categorized.items():
        balanced_examples.extend(lst[:min_count])
        
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in balanced_examples:
            out = {"messages": ex["messages"]}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    return output_path


def export_dpo(output_path: str = "data/training/export_unsloth_dpo.jsonl") -> str:
    """
    Pairs thumbs_up/corrected (chosen) with thumbs_down (rejected) on the same prompt.
    Writes to JSONL in standard HuggingFace/Unsloth DPO format.
    Maintains balanced classes by down-sampling over-represented categories.
    """
    _ensure_dir()
    raw = get_all_examples()
    examples = [ex for ex in raw if not _is_degraded(ex)]
    skipped = len(raw) - len(examples)
    print(f"Curation Curation: Exported {len(examples)} examples. Filtered out {skipped} degraded examples.")

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
    pairs_by_category = {}
    for (system_prompt, user_msg), group in groups.items():
        chosen_list = group["chosen"]
        rejected_list = group["rejected"]
        
        if not chosen_list or not rejected_list:
            continue
            
        cat = _classify_example(user_msg)
        
        # Balance locally: match 1-to-1 chosen-rejected to prevent combinatorial explosion
        matched_count = min(len(chosen_list), len(rejected_list))
        for i in range(matched_count):
            c_resp = chosen_list[i]
            r_resp = rejected_list[i]
            pair = {
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
            }
            pairs_by_category.setdefault(cat, []).append(pair)
            
    # Down-sample over-represented classes
    if pairs_by_category:
        counts = [len(lst) for lst in pairs_by_category.values()]
        min_count = min(counts) if counts else 0
        
        balanced_pairs = []
        for cat, lst in pairs_by_category.items():
            balanced_pairs.extend(lst[:min_count])
    else:
        balanced_pairs = []
        
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in balanced_pairs:
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


def save_eval_result(report: dict) -> str:
    """
    Persist an EvalReport dict to data/eval_results/{timestamp}_{model}_{adapter}.json.
    Also auto-generates DPO pairs from passing/failing items.
    Returns the saved file path.
    """
    import time
    os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    model = report.get("model_name", "unknown").replace("/", "_")[:30]
    adapter = (report.get("adapter_name") or "base").replace("/", "_")[:20]
    path = os.path.join(EVAL_RESULTS_DIR, f"{ts}_{model}_{adapter}.json")

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

    items = report.get("items", [])
    for item in items:
        system_prompt = item.get("system_prompt", "")
        user_msg = item.get("question", "")
        model_response = item.get("model_response", "")
        passed = item.get("passed", False)
        expected = item.get("expected_answer", "")

        if not user_msg or not model_response:
            continue

        if passed:
            save_example(system_prompt, user_msg, model_response, source="eval_chosen")
        else:
            save_example(system_prompt, user_msg, model_response, source="eval_rejected")
            if expected:
                save_example(system_prompt, user_msg, expected, source="eval_chosen")

    return path


def list_eval_results() -> list[dict]:
    """Return all saved eval results as metadata dicts, newest first."""
    if not os.path.exists(EVAL_RESULTS_DIR):
        return []
    results = []
    for fname in os.listdir(EVAL_RESULTS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(EVAL_RESULTS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "path": path,
                "filename": fname,
                "model_name": data.get("model_name", "?"),
                "adapter_name": data.get("adapter_name", "base"),
                "accuracy": data.get("accuracy", 0.0),
                "mrr": data.get("mrr", 0.0),
                "item_count": len(data.get("items", [])),
                "dataset": data.get("dataset_name", "?"),
                "timestamp": data.get("timestamp", fname[:15]),
                "mtime": os.path.getmtime(path),
            })
        except Exception:
            pass
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results


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

    def save_eval_result(self, report: dict) -> str:
        return save_eval_result(report)

    def list_eval_results(self) -> list[dict]:
        return list_eval_results()
