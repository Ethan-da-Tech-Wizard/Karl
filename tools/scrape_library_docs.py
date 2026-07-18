#!/usr/bin/env python3
"""
Library Doc Scraper & QA Compiler
==================================
Recursively inspects installed python packages, extracts class/function docstrings
and signatures, and queries the local LLM to generate synthetic SFT datasets.
"""

from __future__ import annotations

import argparse
import inspect
import importlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("karl.scrape_library_docs")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.model_loader import ModelLoader

OUT_PATH = ROOT / "data/training/code/scraped_library_sft.jsonl"

_MAX_RECURSION_DEPTH = 2


def scrape_package(package_name: str, max_examples: int = 50) -> list[dict[str, Any]]:
    """
    Crawls the package modules and extracts signatures and docstrings.

    Walks the package's public namespace (top-level plus up to two levels of
    submodules), recording documented, public classes/functions/methods that
    are actually defined in this package (not merely re-exported from an
    unrelated dependency).

    Args:
        package_name: Name of the Python module/package.
        max_examples: Limit on number of signatures to extract.

    Returns:
        List of dictionaries with signature details.
    """
    logger.info("Scraping package metadata for '%s'...", package_name)
    try:
        module = importlib.import_module(package_name)
    except ImportError as exc:
        logger.error("Could not import '%s': %s", package_name, exc)
        return []

    results: list[dict[str, Any]] = []
    seen_qualnames: set[str] = set()
    visited_modules: set[str] = set()

    def _belongs_to_package(obj: Any) -> bool:
        owner = getattr(obj, "__module__", "") or ""
        return owner == package_name or owner.startswith(package_name + ".")

    def _record(qualname: str, obj: Any, kind: str) -> None:
        if qualname in seen_qualnames:
            return
        doc = inspect.getdoc(obj)
        if not doc:
            return
        try:
            signature = str(inspect.signature(obj))
        except (TypeError, ValueError):
            signature = "(...)"
        seen_qualnames.add(qualname)
        results.append({
            "package": package_name,
            "qualname": qualname,
            "kind": kind,
            "signature": signature,
            "docstring": doc,
        })

    def _walk(mod: Any, prefix: str, depth: int) -> None:
        if len(results) >= max_examples or depth > _MAX_RECURSION_DEPTH:
            return
        mod_name = getattr(mod, "__name__", "")
        if mod_name in visited_modules:
            return
        visited_modules.add(mod_name)

        # Functions before classes before submodules: alphabetical member
        # order otherwise lets exception classes (Connect*, *Error, ...)
        # crowd out the more instructive top-level functions (get, post, ...)
        # before max_examples is reached.
        members = [(n, o) for n, o in inspect.getmembers(mod) if not n.startswith("_")]
        functions = [(n, o) for n, o in members if (inspect.isfunction(o) or inspect.isbuiltin(o)) and _belongs_to_package(o)]
        classes = [(n, o) for n, o in members if inspect.isclass(o) and _belongs_to_package(o)]
        submodules = [(n, o) for n, o in members if inspect.ismodule(o) and getattr(o, "__name__", "").startswith(package_name)]

        for name, obj in functions:
            if len(results) >= max_examples:
                return
            _record(f"{prefix}.{name}" if prefix else name, obj, "function")

        for name, obj in classes:
            if len(results) >= max_examples:
                return
            qualname = f"{prefix}.{name}" if prefix else name
            _record(qualname, obj, "class")
            for meth_name, meth in inspect.getmembers(obj, predicate=inspect.isfunction):
                if meth_name.startswith("_") or len(results) >= max_examples:
                    continue
                _record(f"{qualname}.{meth_name}", meth, "method")

        for name, obj in submodules:
            if len(results) >= max_examples:
                return
            _walk(obj, f"{prefix}.{name}" if prefix else name, depth + 1)

    _walk(module, "", 0)
    return results[:max_examples]


_FORMAT_INSTRUCTIONS = (
    "Respond in exactly this format, nothing else:\n"
    "INSTRUCTION: <the question, one line>\n"
    "RESPONSE:\n"
    "```python\n"
    "<code example>\n"
    "```"
)

_META_PROMPT_TEMPLATE = (
    "You are creating one training example for a coding assistant. Given a Python "
    "library API signature and its documentation, respond with:\n"
    "1. A realistic coding question a developer might ask that this API answers "
    "(e.g. \"How do I implement X using {qualname}?\").\n"
    "2. A short, correct, idiomatic Python code example that answers it.\n\n"
    "Library: {package}\n"
    "API ({kind}): {qualname}\n"
    "Signature: {qualname}{signature}\n"
    "Documentation:\n{docstring}\n\n"
    "{format_instructions}"
)

_INSTRUCTION_RE = re.compile(r"INSTRUCTION:[ \t]*(.*?)\s*(?=RESPONSE:|\Z)", re.DOTALL | re.IGNORECASE)
_RESPONSE_RE = re.compile(r"RESPONSE:\s*(.+)\Z", re.DOTALL | re.IGNORECASE)


def _build_meta_prompt(signature_info: dict[str, Any]) -> str:
    docstring = str(signature_info.get("docstring", "")).strip()
    if len(docstring) > 1200:
        docstring = docstring[:1200] + "..."
    return _META_PROMPT_TEMPLATE.format(
        package=signature_info.get("package", ""),
        qualname=signature_info.get("qualname", ""),
        kind=signature_info.get("kind", "function"),
        signature=signature_info.get("signature", "(...)"),
        docstring=docstring or "(no docstring)",
        format_instructions=_FORMAT_INSTRUCTIONS,
    )


def _parse_llm_output(raw: str) -> Optional[tuple[str, str]]:
    instr_match = _INSTRUCTION_RE.search(raw)
    resp_match = _RESPONSE_RE.search(raw)
    if not instr_match or not resp_match:
        return None
    instruction = instr_match.group(1).strip()
    response = resp_match.group(1).strip()
    if not instruction or not response:
        return None
    return instruction, response


def generate_sft_qa(signature_info: dict[str, Any], model_name: Optional[str] = None) -> Optional[dict]:
    """
    Query local LLM to convert signatures into instruction-response SFT pairs.

    Args:
        signature_info: Dict containing method details (as returned by scrape_package).
        model_name: Optional GGUF filename override, resolved under data/models/.

    Returns:
        Conversational SFT dictionary or None if generation failed.
    """
    from core.cognitive_parser import parse_thought_stream
    from core.default_prompts import SWARM_CODER_SYSTEM_PROMPT
    from core.interaction_loop import build_prompt

    model_path = os.path.join("data", "models", model_name) if model_name else None
    try:
        llm = ModelLoader.get_instance(model_path=model_path)
    except Exception as exc:
        logger.warning("Could not load model for instruction generation: %s", exc)
        return None

    meta_prompt = _build_meta_prompt(signature_info)
    history = [{"role": "user", "content": meta_prompt}]
    prompt = build_prompt(
        "You generate high-quality, concise training examples for a coding assistant.",
        history,
    )

    try:
        result = llm(prompt, max_tokens=512, temperature=0.4, top_p=0.9, stop=["<|im_end|>"])
    except Exception as exc:
        logger.warning("LLM call failed for %s: %s", signature_info.get("qualname"), exc)
        return None

    raw = result["choices"][0]["text"]
    _thought, parsed = parse_thought_stream(raw, start_in_thought=prompt.rstrip().endswith("<think>"))
    pair = _parse_llm_output(parsed or raw)
    if pair is None:
        return None
    instruction, response = pair

    return {
        "messages": [
            {"role": "system", "content": SWARM_CODER_SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ],
        "source": "library_scrape",
        "package": signature_info.get("package", ""),
        "qualname": signature_info.get("qualname", ""),
        "kind": signature_info.get("kind", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape local library signatures and generate training datasets.")
    parser.add_argument("--package", required=True, help="Target Python package name (e.g. websockets, numpy)")
    parser.add_argument("--max-examples", type=int, default=50, help="Maximum SFT pairs to generate")
    parser.add_argument("--model", default=None, help="Base model filename in data/models/")
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite scraped_library_sft.jsonl instead of appending (default: append, so repeated runs across packages accumulate)"
    )
    args = parser.parse_args()

    try:
        importlib.import_module(args.package)
    except ImportError:
        logger.error("Package '%s' is not installed in the current environment.", args.package)
        return 1

    signatures = scrape_package(args.package, max_examples=args.max_examples)
    logger.info("Found %d classes/functions in '%s'", len(signatures), args.package)

    rows: list[dict] = []
    skipped = 0
    for i, sig in enumerate(signatures, 1):
        logger.info("[%d/%d] %s :: %s", i, len(signatures), sig["package"], sig["qualname"])
        row = generate_sft_qa(sig, model_name=args.model)
        if row:
            rows.append(row)
        else:
            skipped += 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "a"
    with OUT_PATH.open(mode, encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    logger.info("Synthesized %d SFT example(s), skipped %d (unparsable model output).", len(rows), skipped)
    logger.info("Wrote dataset to %s", OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
