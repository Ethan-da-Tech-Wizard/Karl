#!/usr/bin/env python3
"""Download and configure Karl's speculative-decoding draft model."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path


URL = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/"
    "qwen2.5-0.5b-instruct-q8_0.gguf"
)
TARGET = Path("data/models/qwen2.5-0.5b-instruct-q8_0.gguf")
CONFIG = Path("data/draft_model.json")
CHUNK_SIZE = 1024 * 1024


def _format_bytes(value: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _format_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours:d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def download(url: str, target: Path, force: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0 and not force:
        print(f"Draft model already exists: {target}")
        return

    tmp = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Karl/SpeculativeSetup"})
    start = time.monotonic()
    downloaded = 0

    with urllib.request.urlopen(req) as response, tmp.open("wb") as out:
        total_header = response.headers.get("Content-Length")
        total = int(total_header) if total_header and total_header.isdigit() else None
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            elapsed = max(time.monotonic() - start, 0.001)
            rate = downloaded / elapsed
            remaining = ((total - downloaded) / rate) if total and rate > 0 else None
            if total:
                pct = downloaded / total * 100.0
                status = (
                    f"\r{pct:6.2f}%  {_format_bytes(downloaded)} / {_format_bytes(total)}  "
                    f"{_format_bytes(rate)}/s  ETA {_format_eta(remaining)}"
                )
            else:
                status = f"\r{_format_bytes(downloaded)}  {_format_bytes(rate)}/s  ETA {_format_eta(None)}"
            print(status, end="", flush=True)

    print()
    tmp.replace(target)
    print(f"Saved draft model to {target}")


def write_config(target: Path, config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "draft_model_path": str(target),
        "n_ctx": 4096,
        "n_gpu_layers": -1,
    }
    with config_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(f"Wrote speculative decoding config to {config_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Karl's Qwen 0.5B draft GGUF.")
    parser.add_argument("--url", default=URL)
    parser.add_argument("--target", default=str(TARGET))
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--force", action="store_true", help="Re-download even if the target exists")
    args = parser.parse_args()

    target = Path(args.target)
    try:
        download(args.url, target, force=args.force)
        write_config(target, Path(args.config))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Speculative setup failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
