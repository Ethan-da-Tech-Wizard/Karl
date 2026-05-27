"""
Karl Eval CLI — run_eval.py
============================
Command-line entry point for the eval harness.

Usage examples:
  # Run grounded_answer workflow with default template
  python eval/run_eval.py --workflow grounded_answer --dataset eval/datasets/grounded_answer.jsonl

  # Override template and cap tokens
  python eval/run_eval.py --workflow document_extractor --template json_extractor --max-tokens 256

  # Headless, no model needed (uses --dry-run to test graders only)
  python eval/run_eval.py --workflow code_review --dataset eval/datasets/code_review.jsonl --dry-run

Exit codes:
  0 — all cases passed (or --dry-run completed)
  1 — one or more cases failed
  2 — argument error or dataset not found
"""

import argparse
import json
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflows import list_workflows, get_workflow
from core.prompt_templates import list_templates
from eval.harness import EvalHarness
from eval.graders import run_grader


DEFAULT_DATASETS = {
    "document_extractor": "eval/datasets/document_extractor.jsonl",
    "grounded_answer":    "eval/datasets/grounded_answer.jsonl",
    "code_review":        "eval/datasets/code_review.jsonl",
    "general_chat":       "eval/datasets/general_chat.jsonl",
}


def parse_args():
    p = argparse.ArgumentParser(
        description="Karl Eval Harness — run structured evals against the local LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--workflow", "-w",
        required=True,
        choices=[name for name, _ in list_workflows()],
        help="Workflow to evaluate",
    )
    p.add_argument(
        "--dataset", "-d",
        default=None,
        help="Path to JSONL eval dataset. Defaults to eval/datasets/<workflow>.jsonl",
    )
    p.add_argument(
        "--template", "-t",
        default=None,
        choices=list_templates(),
        help="Override the workflow's default prompt template",
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max tokens per generation (default: 512)",
    )
    p.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: 0.2 for eval stability)",
    )
    p.add_argument(
        "--save", "-s",
        action="store_true",
        default=True,
        help="Save report to eval/results/ (default: True)",
    )
    p.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save report to disk",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip model inference. Grade synthetic outputs to test grader logic.",
    )
    p.add_argument(
        "--list-workflows",
        action="store_true",
        help="List available workflows and exit",
    )
    p.add_argument(
        "--list-templates",
        action="store_true",
        help="List available templates and exit",
    )
    return p.parse_args()


def dry_run_mode(dataset_path: str, workflow_name: str):
    """
    Grader-only test: reads dataset, uses the 'expected' field as the model
    output, and grades it. Should always pass. Useful for CI or grader testing.
    """
    print("\n  DRY RUN — grading 'expected' values as outputs (no model loaded)")

    cases = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    passed = 0
    for i, case in enumerate(cases, 1):
        grader = case.get("grader", "keyword_hit")
        expected_raw = case.get("expected", "")
        expected_str = json.dumps(expected_raw) if isinstance(expected_raw, (dict, list)) else str(expected_raw)

        kwargs = {}
        if grader == "json_valid":
            kwargs["schema_keys"] = case.get("schema_keys", [])
        elif grader == "keyword_hit":
            kwargs["keywords"] = case.get("keywords", [expected_str])
            kwargs["require_all"] = case.get("require_all", True)
        elif grader == "exact_match":
            kwargs["expected"] = expected_str
        elif grader == "groundedness":
            kwargs["context_chunks"] = [case.get("context", expected_str)]

        try:
            result = run_grader(grader, expected_str, **kwargs)
            status = "✓" if result["passed"] else "✗"
            if result["passed"]:
                passed += 1
        except Exception as e:
            status = "E"
            result = {"detail": str(e)}

        print(f"  [{i}] {case.get('id', f'case_{i:03d}'):<20} {status}  {result.get('detail', '')}")

    total = len(cases)
    print(f"\n  Dry run complete: {passed}/{total} passed")
    return passed == total


def main():
    args = parse_args()

    if args.list_workflows:
        print("\nAvailable workflows:")
        for name, label in list_workflows():
            wf = get_workflow(name)
            print(f"  {name:<22} — {label}  (template: {wf['template']})")
        sys.exit(0)

    if args.list_templates:
        print("\nAvailable templates:")
        for t in list_templates():
            print(f"  {t}")
        sys.exit(0)

    # Resolve dataset path
    dataset = args.dataset or DEFAULT_DATASETS.get(args.workflow)
    if not dataset:
        print(f"ERROR: No dataset path for workflow '{args.workflow}'. Use --dataset.", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(dataset):
        print(f"ERROR: Dataset not found: {dataset}", file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        ok = dry_run_mode(dataset, args.workflow)
        sys.exit(0 if ok else 1)

    # Run eval
    hyperparams = {
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": 0.95,
    }

    harness = EvalHarness()
    report = harness.run(
        dataset_path=dataset,
        workflow_name=args.workflow,
        template_override=args.template,
        hyperparams=hyperparams,
    )

    report.print_summary()

    save = args.save and not args.no_save
    if save:
        path = harness.save_report(report)
        print(f"  Report saved: {path}")

    # Exit 0 if all passed, 1 if any failed
    sys.exit(0 if report.failed == 0 and report.errors == 0 else 1)


if __name__ == "__main__":
    main()
