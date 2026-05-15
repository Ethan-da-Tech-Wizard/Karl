"""
Privacy Guard — karl_finetune
==============================
Scans dataset text for sensitive patterns before training.
Fine-tuning can memorise training data. Secrets ingested during training
can be reproduced verbatim by the trained model.

Usage:
    from karl_finetune.privacy_guard import scan_text, scan_dataset
    findings = scan_dataset("data/train.jsonl")
"""

import json
import re
from pathlib import Path

# ── Patterns ──────────────────────────────────────────────────────────────────

SENSITIVE_PATTERNS: dict[str, str] = {
    "email":           r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone_us":        r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn":             r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card":     r"\b(?:\d[ -]?){13,16}\b",
    "ip_address":      r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "possible_api_key": r"\b[A-Za-z0-9_\-]{32,}\b",
    "bearer_token":    r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}",
    "private_key_pem": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "aws_key":         r"\bAKIA[0-9A-Z]{16}\b",
}


def scan_text(text: str) -> list[str]:
    """
    Return list of sensitive pattern labels found in `text`.
    Empty list means clean.
    """
    findings = []
    for label, pattern in SENSITIVE_PATTERNS.items():
        if re.search(pattern, text):
            findings.append(label)
    return findings


def scan_dataset(path: str) -> dict[int, list[str]]:
    """
    Scan all text fields in a JSONL dataset file.

    Supports both:
      - instruction/input/output format
      - messages format (ShareGPT / curated.jsonl)

    Returns {line_number: [finding_labels, ...]}.
    Empty dict = clean dataset.
    """
    results: dict[int, list[str]] = {}
    fpath = Path(path)
    if not fpath.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    with open(fpath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Collect all text fields
            texts: list[str] = []
            for field in ("instruction", "input", "output"):
                if field in record:
                    texts.append(str(record[field]))
            for msg in record.get("messages", []):
                texts.append(str(msg.get("content", "")))
            if "rejected" in record:
                texts.append(str(record["rejected"]))

            combined = " ".join(texts)
            findings = scan_text(combined)
            if findings:
                results[line_num] = findings

    return results


def print_scan_report(results: dict[int, list[str]], total_lines: int) -> bool:
    """Print a formatted scan report. Returns True if clean."""
    if not results:
        print(f"  ✓  Privacy scan: clean ({total_lines} lines checked)")
        return True

    print(f"  ⚠  Privacy scan: {len(results)} line(s) with sensitive patterns:")
    for line_num, findings in sorted(results.items()):
        print(f"       Line {line_num}: {', '.join(findings)}")
    print("     Review and redact before training. Fine-tuned models can reproduce training data.")
    return False
