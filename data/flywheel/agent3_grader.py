#!/usr/bin/env python3
"""
Agent 3: Automated Grader & Training Curator
Part of the Karl self-improvement flywheel.

Reads execution JSONs from data/flywheel/execution/ produced by Agent 2,
verifies each model response, and curates SFT/DPO training data into
data/training/curated.jsonl.

Verification types:
  unit_test      — run verification_script via subprocess; exit 0 = pass
  exact_match    — run verification_script via subprocess
  symbolic_match — subprocess + optional sympy numeric fallback

Run:
  python data/flywheel/agent3_grader.py [--interval N] [--once]
"""

import os
import sys
import json
import time
import logging
import tempfile
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root resolution — file lives at data/flywheel/agent3_grader.py
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("karl.agent3_grader")

EXECUTION_DIR = str(_ROOT / "data" / "flywheel" / "execution")
CURATED_PATH  = str(_ROOT / "data" / "training" / "curated.jsonl")
STATS_PATH    = str(_ROOT / "data" / "flywheel" / "agent3_stats.json")

os.makedirs(EXECUTION_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CURATED_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _load_stats() -> dict:
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "processed": 0,
        "passed": 0,
        "failed": 0,
        "sft_examples": 0,
        "dpo_pairs": 0,
        "last_updated": "",
    }


def _save_stats(stats: dict):
    stats["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = STATS_PATH + ".tmp"
    try:
        os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        os.replace(tmp, STATS_PATH)
    except Exception as e:
        logger.warning("Failed to write stats: %s", e)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def run_verification(exec_record: dict) -> tuple[bool, str]:
    """
    Dispatch to the appropriate verifier.
    Returns (passed, detail_string).
    """
    vtype  = exec_record.get("verification_type", "exact_match")
    script = exec_record.get("verification_script", "")
    resp   = exec_record.get("model_response", "")

    if not script:
        return False, "no verification_script"

    passed, detail = _verify_subprocess(script, resp)

    # Secondary sympy pass for symbolic problems when subprocess fails
    if not passed and vtype == "symbolic_match":
        sym_passed, sym_detail = _verify_sympy(
            exec_record.get("ground_truth_answer", ""), resp
        )
        if sym_passed:
            return True, sym_detail

    return passed, detail


def _verify_subprocess(verification_script: str, model_response: str) -> tuple[bool, str]:
    """
    Write verification_script + a call to verify(response) into a temp file
    and run it via subprocess.  Exit code 0 = pass.
    """
    runner = (
        f"{verification_script}\n\n"
        "import sys as _sys, json as _json\n"
        f"_resp = _json.loads({json.dumps(json.dumps(model_response))})\n"
        "try:\n"
        "    _result = verify(_resp)\n"
        "    _sys.exit(0 if _result else 1)\n"
        "except Exception as _e:\n"
        "    print('verify() raised:', _e, file=_sys.stderr)\n"
        "    _sys.exit(2)\n"
    )
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(runner)
            tmp_path = tmp.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        passed = result.returncode == 0
        detail = (result.stdout + result.stderr).strip()[:400]
        return passed, detail or ("pass" if passed else "fail")
    except subprocess.TimeoutExpired:
        return False, "verification timed out (10s)"
    except Exception as e:
        return False, f"verification error: {e}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def _verify_sympy(ground_truth: str, model_response: str) -> tuple[bool, str]:
    """Extract a number from ground_truth and look for it in model_response via sympy."""
    try:
        import re
        import sympy

        gt_nums = re.findall(r"-?\d+(?:\.\d+)?", ground_truth)
        if not gt_nums:
            return False, "no numeric ground truth for sympy"
        gt_val = sympy.sympify(gt_nums[-1])

        resp_nums = re.findall(r"-?\d+(?:\.\d+)?", model_response)
        for n in resp_nums:
            try:
                if sympy.simplify(sympy.sympify(n) - gt_val) == 0:
                    return True, f"sympy: {n} == {gt_val}"
            except Exception:
                pass
        return False, f"sympy: ground truth {gt_val} not found in response"
    except ImportError:
        return False, "sympy not available"
    except Exception as e:
        return False, f"sympy error: {e}"


# ---------------------------------------------------------------------------
# Correction generation
# ---------------------------------------------------------------------------

def generate_correction(exec_record: dict) -> tuple[str, str]:
    """
    Produce a corrected thought trace and solution for a failing execution.
    Tries the local LLM first; falls back to a ground-truth stub.

    Returns (thought_trace, corrected_response).
    """
    ground_truth = exec_record.get("ground_truth_answer", "")
    problem      = exec_record.get("problem_statement", "")
    vtype        = exec_record.get("verification_type", "")

    # ── LLM-based correction ────────────────────────────────────────────────
    try:
        from app.engine.model_loader import ModelLoader
        from core.interaction_loop import build_prompt

        if ModelLoader.is_loaded():
            llm = ModelLoader.get_instance()
            correction_prompt = (
                f"You are a precise tutor correcting a wrong answer.\n\n"
                f"Problem:\n{problem}\n\n"
                f"The student's incorrect answer was:\n"
                f"{exec_record.get('model_response', '')}\n\n"
                f"The correct answer is: {ground_truth}\n\n"
                "Provide a complete, step-by-step correct solution ending with "
                "the final answer clearly stated."
            )
            prompt_text = build_prompt(
                "You are a precise mathematical and programming tutor.",
                [{"role": "user", "content": correction_prompt}],
            )
            raw = llm(
                prompt_text,
                max_tokens=1024,
                temperature=0.1,
                top_p=0.95,
                stop=["<|im_end|>"],
            )
            full = raw["choices"][0]["text"].strip()
            if "</think>" in full:
                head, _, tail = full.partition("</think>")
                thought   = head.replace("<think>", "").strip()
                corrected = tail.strip()
            else:
                thought, corrected = "", full
            if corrected:
                return thought, corrected
    except Exception as e:
        logger.debug("LLM correction unavailable: %s", e)

    # ── Ground-truth stub fallback ──────────────────────────────────────────
    if vtype == "unit_test":
        thought = (
            "The model's code failed the unit tests. "
            f"A correct implementation must satisfy: {ground_truth}."
        )
        corrected = (
            f"The correct answer is: {ground_truth}\n\n"
            "A correct implementation must pass all provided test cases, "
            "including edge cases such as empty inputs."
        )
    elif vtype in ("exact_match", "symbolic_match"):
        thought = (
            f"Let me work through this step-by-step.\n"
            f"The correct answer is {ground_truth}."
        )
        corrected = (
            f"Working through the problem carefully:\n"
            f"The correct final answer is: {ground_truth}"
        )
    else:
        thought   = f"The correct answer is: {ground_truth}"
        corrected = f"The correct answer is: {ground_truth}"

    return thought, corrected


# ---------------------------------------------------------------------------
# Curation writers
# ---------------------------------------------------------------------------

def save_sft_example(exec_record: dict):
    """Save a passing execution as a thumbs-up SFT example."""
    try:
        from app.utils.training_curator import save_example
        save_example(
            system_prompt="",
            user_msg=exec_record.get("problem_statement", ""),
            good_response=exec_record.get("model_response", ""),
            source="thumbs_up",
        )
    except Exception as e:
        logger.error("save_sft_example failed: %s", e)


def save_dpo_pair(
    exec_record: dict, corrected_thought: str, corrected_response: str
):
    """
    Append a DPO pair to curated.jsonl using the instruction/chosen/rejected schema.
    """
    model_thought   = exec_record.get("model_thought", "")
    model_response  = exec_record.get("model_response", "")

    # Wrap with <think> tags when a thought trace is available
    chosen = (
        f"<think>\n{corrected_thought}\n</think>\n{corrected_response}"
        if corrected_thought
        else corrected_response
    )
    rejected = (
        f"<think>\n{model_thought}\n</think>\n{model_response}"
        if model_thought
        else model_response
    )

    record = {
        "instruction": exec_record.get("problem_statement", ""),
        "input": "",
        "chosen": chosen,
        "rejected": rejected,
        "source": "curated_dpo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(os.path.dirname(CURATED_PATH), exist_ok=True)
    with open(CURATED_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Per-file processor
# ---------------------------------------------------------------------------

def process_execution_file(path: str, stats: dict):
    fname = os.path.basename(path)
    logger.info("Grading: %s", fname)

    try:
        with open(path, "r", encoding="utf-8") as f:
            exec_record = json.load(f)
    except Exception as e:
        logger.error("Failed to load %s: %s", fname, e)
        try:
            os.remove(path)
        except Exception:
            pass
        return

    try:
        passed, detail = run_verification(exec_record)
        stats["processed"] += 1

        vtype = exec_record.get("verification_type", "?")

        if passed:
            logger.info("  PASS [%s] %s", vtype, fname)
            save_sft_example(exec_record)
            stats["passed"]       += 1
            stats["sft_examples"] += 1
        else:
            logger.info("  FAIL [%s] %s — %s", vtype, fname, detail[:80])
            thought, corrected = generate_correction(exec_record)
            save_dpo_pair(exec_record, thought, corrected)
            stats["failed"]    += 1
            stats["dpo_pairs"] += 1

        os.remove(path)
        logger.info("  Deleted execution file: %s", fname)

    except Exception as e:
        logger.error("Unexpected error processing %s: %s", fname, e, exc_info=True)
        # Do not delete on unexpected error — allow retry on next poll cycle
    finally:
        _save_stats(stats)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Agent 3: Automated Grader & Training Curator"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Poll interval in seconds when execution dir is empty (default: 1)",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Process all current files then exit (no infinite loop)",
    )
    args = parser.parse_args()

    logger.info("Agent 3 started. Watching: %s", EXECUTION_DIR)
    stats = _load_stats()

    while True:
        try:
            files = sorted(
                f for f in os.listdir(EXECUTION_DIR)
                if f.endswith(".json") and not f.endswith(".tmp")
            )

            if not files:
                if args.once:
                    logger.info("No files remaining. Exiting (--once).")
                    break
                time.sleep(args.interval)
                continue

            for fname in files:
                fpath = os.path.join(EXECUTION_DIR, fname)
                if os.path.exists(fpath):
                    process_execution_file(fpath, stats)

            if args.once:
                logger.info("Batch complete. Exiting (--once).")
                break

        except Exception as e:
            logger.error("Main loop error: %s", e)
            time.sleep(5)

    logger.info(
        "Agent 3 done — processed=%d  passed=%d  failed=%d  sft=%d  dpo=%d",
        stats["processed"], stats["passed"], stats["failed"],
        stats["sft_examples"], stats["dpo_pairs"],
    )


if __name__ == "__main__":
    main()
