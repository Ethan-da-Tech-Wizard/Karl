"""
Output Comparator — karl_finetune
====================================
Loads base and fine-tuned eval results, scores them side by side,
and generates a markdown report in outputs/reports/.

Scoring dimensions:
  keyword_hit   — does the output contain expected keywords?
  length_ratio  — fine-tuned output longer/shorter than base? (proxy for detail)
  tone_markers  — professional tone words present? (sorry, help, resolve, etc.)

Usage:
  python -m karl_finetune.compare_outputs
  python -m karl_finetune.compare_outputs --reports outputs/reports
  python -m karl_finetune.compare_outputs --base outputs/reports/eval_base.jsonl \
                                           --tuned outputs/reports/eval_tuned.jsonl
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Words associated with professional / helpful tone
TONE_MARKERS = [
    "sorry", "apologize", "help", "assist", "resolve", "troubleshoot",
    "understand", "appreciate", "thank", "please", "ensure", "support",
    "follow up", "let me know", "happy to",
]


# ── Scoring ───────────────────────────────────────────────────────────────────

def _keyword_score(output: str, keywords: list[str]) -> float:
    if not keywords:
        return None
    output_lower = output.lower()
    hits = sum(1 for k in keywords if k.lower() in output_lower)
    return round(hits / len(keywords), 3)


def _tone_score(output: str) -> float:
    output_lower = output.lower()
    hits = sum(1 for m in TONE_MARKERS if m in output_lower)
    return round(hits / len(TONE_MARKERS), 3)


def _length_ratio(output_tuned: str, output_base: str) -> float | None:
    base_len = len(output_base.split())
    if base_len == 0:
        return None
    return round(len(output_tuned.split()) / base_len, 2)


def _score_case(base_out: str, tuned_out: str, expected_keywords: list[str]) -> dict:
    base_kw   = _keyword_score(base_out,  expected_keywords)
    tuned_kw  = _keyword_score(tuned_out, expected_keywords)
    base_tone  = _tone_score(base_out)
    tuned_tone = _tone_score(tuned_out)
    ratio      = _length_ratio(tuned_out, base_out)

    kw_delta   = round(tuned_kw  - base_kw,   3) if base_kw  is not None else None
    tone_delta = round(tuned_tone - base_tone, 3)

    return {
        "keyword_hit":   {"base": base_kw,   "tuned": tuned_kw,   "delta": kw_delta},
        "tone_score":    {"base": base_tone,  "tuned": tuned_tone, "delta": tone_delta},
        "length_ratio":  ratio,
    }


# ── Report generation ─────────────────────────────────────────────────────────

def _verdict(delta: float | None) -> str:
    if delta is None:
        return "—"
    if delta > 0.05:
        return "✅ improved"
    if delta < -0.05:
        return "⬇ regressed"
    return "≈ unchanged"


def generate_report(base_results: list[dict], tuned_results: list[dict],
                    training_summary: dict | None = None) -> str:
    """Build a markdown report string."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Karl Fine-Tuning Report",
        f"\nGenerated: {ts}",
        "",
    ]

    # ── Training summary ──────────────────────────────────────────────────────
    if training_summary:
        lines += [
            "## Training",
            f"- **Base model:** {training_summary.get('model_name', '?')}",
            f"- **Adapter:** {training_summary.get('adapter_dir', '?')}",
            f"- **Training examples:** {training_summary.get('train_examples', '?')}",
            f"- **Epochs:** {training_summary.get('epochs', '?')}",
            f"- **LoRA rank:** {training_summary.get('lora_r', '?')} / alpha {training_summary.get('lora_alpha', '?')}",
            f"- **Learning rate:** {training_summary.get('learning_rate', '?')}",
            f"- **Training time:** {training_summary.get('elapsed_seconds', '?')}s",
            "",
        ]

    # ── Aggregate scores ──────────────────────────────────────────────────────
    base_by_id  = {r["id"]: r for r in base_results}
    tuned_by_id = {r["id"]: r for r in tuned_results}
    common_ids  = [r["id"] for r in base_results if r["id"] in tuned_by_id]

    agg_kw_base = agg_kw_tuned = 0.0
    agg_tone_base = agg_tone_tuned = 0.0
    valid_kw = valid_tone = 0

    per_case_scores = []
    for cid in common_ids:
        b = base_by_id[cid]
        t = tuned_by_id[cid]
        scores = _score_case(b["output"], t["output"], b.get("expected_keywords", []))
        per_case_scores.append((cid, b, t, scores))

        if scores["keyword_hit"]["base"] is not None:
            agg_kw_base  += scores["keyword_hit"]["base"]
            agg_kw_tuned += scores["keyword_hit"]["tuned"]
            valid_kw     += 1

        agg_tone_base  += scores["tone_score"]["base"]
        agg_tone_tuned += scores["tone_score"]["tuned"]
        valid_tone     += 1

    n = len(common_ids)
    avg_kw_base  = round(agg_kw_base  / valid_kw,   3) if valid_kw   else None
    avg_kw_tuned = round(agg_kw_tuned / valid_kw,   3) if valid_kw   else None
    avg_tone_base  = round(agg_tone_base  / valid_tone, 3) if valid_tone else None
    avg_tone_tuned = round(agg_tone_tuned / valid_tone, 3) if valid_tone else None

    lines += [
        f"## Aggregate Results ({n} cases)",
        "",
        "| Metric | Base | Fine-Tuned | Verdict |",
        "|---|---|---|---|",
    ]
    if avg_kw_base is not None:
        kw_delta = round(avg_kw_tuned - avg_kw_base, 3)
        lines.append(f"| Keyword hit rate | {avg_kw_base:.1%} | {avg_kw_tuned:.1%} | {_verdict(kw_delta)} |")
    tone_delta = round(avg_tone_tuned - avg_tone_base, 3) if avg_tone_base is not None else None
    if avg_tone_base is not None:
        lines.append(f"| Tone score       | {avg_tone_base:.1%} | {avg_tone_tuned:.1%} | {_verdict(tone_delta)} |")
    lines.append("")

    # ── Recommendation ────────────────────────────────────────────────────────
    improvements = sum(
        1 for _, _, _, s in per_case_scores
        if (s["keyword_hit"]["delta"] or 0) > 0 or s["tone_score"]["delta"] > 0
    )
    regressions = sum(
        1 for _, _, _, s in per_case_scores
        if (s["keyword_hit"]["delta"] or 0) < -0.05 or s["tone_score"]["delta"] < -0.05
    )

    lines += ["## Recommendation", ""]
    if improvements > regressions and improvements > n // 2:
        lines += [
            "Fine-tuning **helped**. The adapter improved tone consistency and keyword adherence.",
            "Consider deploying the adapter for production use of this task pattern.",
            "",
            "> Use RAG for factual knowledge. Use this adapter for behavioral consistency.",
        ]
    elif regressions > improvements:
        lines += [
            "Fine-tuning **regressed** performance on this eval set.",
            "Possible causes: too few examples, too many epochs (overfitting), poor dataset quality.",
            "Recommendation: validate the dataset, reduce epochs, or add more diverse examples.",
        ]
    else:
        lines += [
            "Results are **mixed**. Some cases improved, some regressed.",
            "Review per-case outputs below to identify patterns before deploying.",
        ]
    lines.append("")

    # ── Per-case breakdown ────────────────────────────────────────────────────
    lines += ["## Per-Case Breakdown", ""]
    for cid, b, t, scores in per_case_scores:
        kw  = scores["keyword_hit"]
        tone = scores["tone_score"]
        ratio = scores["length_ratio"]

        lines += [
            f"### {cid}",
            f"**Instruction:** {b.get('instruction', '')}",
        ]
        if b.get("input", "").strip():
            lines.append(f"**Input:** {b['input']}")

        lines += [
            "",
            "**Base output:**",
            f"> {b['output']}",
            "",
            "**Fine-tuned output:**",
            f"> {t['output']}",
            "",
            "**Scores:**",
            f"| Metric | Base | Fine-Tuned | Delta |",
            f"|---|---|---|---|",
        ]
        if kw["base"] is not None:
            lines.append(f"| Keyword hit | {kw['base']:.1%} | {kw['tuned']:.1%} | {kw['delta']:+.1%} |")
        lines.append(f"| Tone score  | {tone['base']:.1%} | {tone['tuned']:.1%} | {tone['delta']:+.1%} |")
        if ratio is not None:
            lines.append(f"| Length ratio (tuned/base) | — | {ratio}× | — |")
        lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def compare(base_path: str, tuned_path: str, reports_dir: str = "outputs/reports"):
    base_results  = []
    tuned_results = []

    for path, bucket in [(base_path, base_results), (tuned_path, tuned_results)]:
        p = Path(path)
        if not p.exists():
            print(f"  ✗  Results file not found: {path}")
            print("     Run eval first:")
            print("       python -m karl_finetune.run_eval configs/eval_config.json --mode base")
            print("       python -m karl_finetune.run_eval configs/eval_config.json --mode tuned")
            return
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    bucket.append(json.loads(line))

    # Load training summary if present
    training_summary = None
    reports = Path(reports_dir)
    for adapter_dir_guess in ["outputs/adapters/karl_lora", "outputs/adapters"]:
        summary_path = Path(adapter_dir_guess) / "training_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                training_summary = json.load(f)
            break

    print(f"\n  Comparing {len(base_results)} base + {len(tuned_results)} tuned results...")

    report_md = generate_report(base_results, tuned_results, training_summary)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = reports / f"comparison_{ts}.md"
    reports.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # Print aggregate to console
    print(report_md[:1200])
    if len(report_md) > 1200:
        print(f"  ... (full report in {report_path})")

    print(f"\n  ✅  Report saved to {report_path}\n")
    return str(report_path)


def main():
    p = argparse.ArgumentParser(description="Compare base vs fine-tuned model outputs")
    p.add_argument("--base",    default="outputs/reports/eval_base.jsonl",
                   help="Base model eval results JSONL")
    p.add_argument("--tuned",   default="outputs/reports/eval_tuned.jsonl",
                   help="Fine-tuned model eval results JSONL")
    p.add_argument("--reports", default="outputs/reports",
                   help="Directory for output report")
    args = p.parse_args()
    compare(args.base, args.tuned, args.reports)


if __name__ == "__main__":
    main()
