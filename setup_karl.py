#!/usr/bin/env python3
"""
setup_karl.py — Cross-platform bootstrapper for Karl.

Detects OS, GPU hardware, and Python environment; builds the correct
llama-cpp-python compilation flags; creates and populates a virtual
environment; then launches the application.

Usage:
    python setup_karl.py --install           # Full environment setup
    python setup_karl.py --install --force   # Recreate venv from scratch
    python setup_karl.py --install --cpu     # Force CPU-only llama-cpp build
    python setup_karl.py --install --cuda    # Force CUDA build (skip detection)
    python setup_karl.py --install --metal   # Force Metal build (macOS only)
    python setup_karl.py --run               # Launch Karl (auto-installs if needed)
    python setup_karl.py --run [args...]     # Launch with extra flags forwarded to main.py
    python setup_karl.py --info              # Print detected system info and exit
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# ── Constants ─────────────────────────────────────────────────────────────────

REPO_ROOT    = Path(__file__).resolve().parent
VENV_NAMES   = ("venv", ".venv")          # Prefer "venv"; fall back to ".venv"
REQUIREMENTS = REPO_ROOT / "requirements.txt"
MAIN_PY      = REPO_ROOT / "main.py"
DATA_DIRS    = [
    "data/models",
    "data/training",
    "data/logs/traces",
    "data/logs/archive",
    "data/logs/raw",
    "data/sessions",
    "data/adapters",
    "eval/results",
]

# Minimum Python version required by Karl (PyQt6 requires 3.9+).
MIN_PYTHON = (3, 9)


# ── Color output ──────────────────────────────────────────────────────────────

def _enable_windows_ansi() -> None:
    """Enable VT100 ANSI escape sequences on Windows 10+ terminals."""
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32          # type: ignore[attr-defined]
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


_enable_windows_ansi()

# Guard: if stdout is not a terminal (e.g. piped), strip color codes.
_COLOR = sys.stdout.isatty()

_RESET  = "\033[0m"  if _COLOR else ""
_BOLD   = "\033[1m"  if _COLOR else ""
_GREEN  = "\033[92m" if _COLOR else ""
_YELLOW = "\033[93m" if _COLOR else ""
_RED    = "\033[91m" if _COLOR else ""
_CYAN   = "\033[96m" if _COLOR else ""
_DIM    = "\033[2m"  if _COLOR else ""


def _ok(msg: str)   -> None: print(f"{_GREEN}  ✓  {msg}{_RESET}")
def _info(msg: str) -> None: print(f"{_CYAN}  ·  {msg}{_RESET}")
def _warn(msg: str) -> None: print(f"{_YELLOW}  ⚠  {msg}{_RESET}")
def _err(msg: str)  -> None: print(f"{_RED}  ✗  {msg}{_RESET}", file=sys.stderr)
def _sep()          -> None: print(f"{_DIM}{'─' * 60}{_RESET}")
def _head(msg: str) -> None: print(f"\n{_BOLD}{_CYAN}{msg}{_RESET}")


# ── Detection ─────────────────────────────────────────────────────────────────

class SystemInfo(NamedTuple):
    os_name:     str        # "Windows" | "Darwin" | "Linux"
    arch:        str        # e.g. "arm64", "x86_64"
    gpu_type:    str        # "cuda" | "metal" | "cpu"
    gpu_label:   str        # human-readable GPU description
    in_venv:     bool       # True if currently inside a venv
    python_ver:  str        # e.g. "3.12.3"
    venv_dir:    Path | None  # existing venv path, if found


def detect_system() -> SystemInfo:
    os_name = platform.system()        # "Windows", "Darwin", "Linux"
    arch    = platform.machine()       # "arm64", "x86_64", "AMD64", …

    # ── GPU detection ─────────────────────────────────────────────────────────
    gpu_type  = "cpu"
    gpu_label = "None detected (CPU-only build)"

    if os_name == "Darwin" and arch in ("arm64", "aarch64"):
        # Apple Silicon — Metal is always available.
        chip = _probe_apple_chip()
        gpu_type  = "metal"
        gpu_label = f"Apple {chip} (Metal / MPS)"
    else:
        # Try NVIDIA first via nvidia-smi.
        nvidia = _probe_nvidia()
        if nvidia:
            gpu_type  = "cuda"
            gpu_label = nvidia
        # On macOS x86_64 there's no Metal; on AMD GPUs there's no CUDA.
        # Fall through to cpu.

    # ── Venv detection ────────────────────────────────────────────────────────
    in_venv = (
        sys.prefix != sys.base_prefix
        or os.environ.get("VIRTUAL_ENV") is not None
        or os.environ.get("CONDA_DEFAULT_ENV") is not None
    )
    venv_dir = _find_existing_venv()

    return SystemInfo(
        os_name    = os_name,
        arch       = arch,
        gpu_type   = gpu_type,
        gpu_label  = gpu_label,
        in_venv    = in_venv,
        python_ver = platform.python_version(),
        venv_dir   = venv_dir,
    )


def _probe_nvidia() -> str | None:
    """Return a GPU description string if nvidia-smi is available and working."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
            if lines:
                parts = [p.strip() for p in lines[0].split(",")]
                name    = parts[0] if len(parts) > 0 else "Unknown NVIDIA GPU"
                driver  = parts[1] if len(parts) > 1 else "?"
                mem_mib = parts[2] if len(parts) > 2 else "?"
                extra   = f"  ({len(lines)} GPU{'s' if len(lines) > 1 else ''})" if len(lines) > 1 else ""
                return f"NVIDIA {name} · driver {driver} · {mem_mib} MiB VRAM{extra}"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _probe_apple_chip() -> str:
    """Return the Apple chip name (e.g. 'M2 Pro') or 'Silicon' as a fallback."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        brand = result.stdout.strip()
        # Typical value: "Apple M2 Pro" or "Apple M1"
        if brand.startswith("Apple"):
            return brand.removeprefix("Apple ").strip()
    except (FileNotFoundError, OSError):
        pass
    return "Silicon"


def _find_existing_venv() -> Path | None:
    """Return the path to an existing venv directory, or None."""
    for name in VENV_NAMES:
        candidate = REPO_ROOT / name
        marker = candidate / ("Scripts" if platform.system() == "Windows" else "bin") / (
            "python.exe" if platform.system() == "Windows" else "python"
        )
        if marker.exists():
            return candidate
    return None


# ── Cmake flags builder ───────────────────────────────────────────────────────

def build_cmake_args(gpu_type: str, override: str | None = None) -> str:
    """
    Return the CMAKE_ARGS string for llama-cpp-python compilation.

    override: "cuda" | "metal" | "cpu" | None  (from CLI flag)
    """
    effective = override or gpu_type

    if effective == "metal":
        # Both flag variants for forward/backward compat across llama-cpp versions.
        return "-DGGML_METAL=on -DLLAMA_METAL=on"
    if effective == "cuda":
        return "-DGGML_CUDA=on -DLLAMA_CUDA=on"
    return ""   # CPU-only — no special flags needed


# ── Venv management ───────────────────────────────────────────────────────────

def _venv_executables(venv_dir: Path) -> dict[str, Path]:
    """Return paths to python and pip inside *venv_dir*."""
    is_win = platform.system() == "Windows"
    scripts = venv_dir / ("Scripts" if is_win else "bin")
    return {
        "python": scripts / ("python.exe" if is_win else "python"),
        "pip":    scripts / ("pip.exe"    if is_win else "pip"),
    }


def find_or_create_venv(*, force: bool = False) -> Path:
    """
    Return the venv directory, creating it first if necessary.
    If *force* is True, delete any existing venv and start fresh.
    """
    existing = _find_existing_venv()

    if force and existing:
        _info(f"Removing existing venv at {existing} (--force)…")
        shutil.rmtree(existing)
        existing = None

    if existing:
        _ok(f"Found existing venv: {existing}")
        return existing

    venv_dir = REPO_ROOT / VENV_NAMES[0]   # always create as "venv/"
    _info(f"Creating virtual environment at {venv_dir}…")
    _run([sys.executable, "-m", "venv", str(venv_dir)], desc="python -m venv")
    _ok(f"Virtual environment created: {venv_dir}")
    return venv_dir


# ── Subprocess runner ─────────────────────────────────────────────────────────

def _run(
    cmd: list[str],
    *,
    desc: str = "",
    env: dict[str, str] | None = None,
    check: bool = True,
    stream: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run *cmd*, streaming output line-by-line with a DIM prefix.
    Raises SystemExit on non-zero exit when *check* is True.
    """
    merged_env = {**os.environ, **(env or {})}
    display = desc or " ".join(cmd[:3])
    _info(f"Running: {_DIM}{display}{_RESET}")

    if stream:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=merged_env,
        )
        output_lines: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            # Color-code obvious error/warning lines.
            if any(tok in line.lower() for tok in ("error:", "failed", "exception")):
                print(f"  {_RED}{line}{_RESET}")
            elif any(tok in line.lower() for tok in ("warning:", "warn:")):
                print(f"  {_YELLOW}{line}{_RESET}")
            else:
                print(f"  {_DIM}{line}{_RESET}")
        proc.wait()
        rc = proc.returncode
        if check and rc != 0:
            _err(f"Command failed (exit {rc}): {' '.join(cmd[:4])}")
            raise SystemExit(rc)
        return subprocess.CompletedProcess(cmd, rc, "\n".join(output_lines), "")
    else:
        result = subprocess.run(cmd, env=merged_env, capture_output=True, text=True)
        if check and result.returncode != 0:
            _err(f"Command failed (exit {result.returncode}): {' '.join(cmd[:4])}")
            if result.stderr.strip():
                _err(result.stderr.strip())
            raise SystemExit(result.returncode)
        return result


# ── Installation steps ────────────────────────────────────────────────────────

def install_dependencies(pip: Path) -> None:
    """Upgrade pip, then install requirements.txt."""
    _head("Installing dependencies")

    _run(
        [str(pip), "install", "--upgrade", "pip"],
        desc="pip install --upgrade pip",
    )
    _ok("pip upgraded")

    if not REQUIREMENTS.exists():
        _warn(f"requirements.txt not found at {REQUIREMENTS} — skipping base deps")
        return

    _run(
        [str(pip), "install", "-r", str(REQUIREMENTS)],
        desc="pip install -r requirements.txt",
    )
    _ok("Base dependencies installed")


def install_llama_cpp(pip: Path, cmake_args: str) -> None:
    """
    Install llama-cpp-python with the correct CMAKE_ARGS.
    Uses --no-binary to force recompilation from source when cmake_args are set.
    """
    _head("Compiling llama-cpp-python")

    if cmake_args:
        _info(f"CMAKE_ARGS: {_BOLD}{cmake_args}{_RESET}")
        extra_env = {"CMAKE_ARGS": cmake_args}
        # Force source build so cmake flags are honoured.
        extra_flags = ["--no-binary", "llama-cpp-python", "--force-reinstall"]
    else:
        _info("No GPU cmake flags — CPU-only build (wheel from PyPI)")
        extra_env = {}
        extra_flags = []

    # Extract the pinned version from requirements.txt so we install exactly
    # the same version as the rest of the stack.
    version_spec = _extract_requirement("llama-cpp-python")
    pkg = f"llama-cpp-python{version_spec}" if version_spec else "llama-cpp-python"

    _run(
        [str(pip), "install", pkg, *extra_flags],
        desc=f"pip install {pkg}",
        env=extra_env,
    )
    _ok(f"llama-cpp-python installed{' (GPU-accelerated)' if cmake_args else ''}")


def _extract_requirement(name: str) -> str:
    """Return the version specifier for *name* from requirements.txt, e.g. '==0.3.25'."""
    if not REQUIREMENTS.exists():
        return ""
    needle = name.lower()
    with open(REQUIREMENTS, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            pkg_part = stripped.split()[0].lower()
            if pkg_part.startswith(needle):
                spec = pkg_part[len(name):]   # e.g. "==0.3.25" or ""
                return spec
    return ""


def ensure_data_dirs() -> None:
    """Create the runtime data directory skeleton if not already present."""
    for rel in DATA_DIRS:
        d = REPO_ROOT / rel
        d.mkdir(parents=True, exist_ok=True)
    _ok("Runtime data directories verified")


def maybe_download_model(python: Path) -> None:
    """Offer to download the base model if it is missing."""
    model_path = REPO_ROOT / "data" / "models" / "deepseek-r1-1.5b.gguf"
    if model_path.exists():
        _ok(f"Base model present: {model_path.name}")
        return

    _warn("Base model not found: data/models/deepseek-r1-1.5b.gguf")
    try:
        answer = input(
            f"  {_YELLOW}Download it now? [Y/n]: {_RESET}"
        ).strip().lower()
    except EOFError:
        answer = "n"

    if answer in ("", "y", "yes"):
        download_script = REPO_ROOT / "download_test_model.py"
        if download_script.exists():
            _run([str(python), str(download_script)], desc="download_test_model.py")
        else:
            _warn("download_test_model.py not found — download the model manually.")
    else:
        _warn("Skipping model download. Karl will prompt on first launch.")


# ── Full install flow ─────────────────────────────────────────────────────────

def cmd_install(args: argparse.Namespace, info: SystemInfo) -> None:
    _head("Karl Setup — Install")
    _sep()

    _print_info(info)
    _sep()

    # Build cmake args (CLI override takes precedence over auto-detection).
    gpu_override: str | None = None
    if args.cpu:
        gpu_override = "cpu"
    elif args.cuda:
        gpu_override = "cuda"
    elif args.metal:
        gpu_override = "metal"

    cmake_args = build_cmake_args(info.gpu_type, gpu_override)
    effective_gpu = gpu_override or info.gpu_type
    _info(f"Build target: {_BOLD}{effective_gpu.upper()}{_RESET}")

    # Venv
    venv_dir = find_or_create_venv(force=args.force)
    execs = _venv_executables(venv_dir)
    pip    = execs["pip"]
    python = execs["python"]

    if not pip.exists():
        _err(f"pip not found at expected path: {pip}")
        raise SystemExit(1)

    # Install base deps
    install_dependencies(pip)

    # Install llama-cpp-python with GPU flags
    install_llama_cpp(pip, cmake_args)

    # Data dirs
    _head("Ensuring data directories")
    ensure_data_dirs()

    # Base model
    _head("Base model check")
    maybe_download_model(python)

    _sep()
    _ok(f"{_BOLD}Karl installation complete.{_RESET}")
    _info(f"Launch with:  {_BOLD}python setup_karl.py --run{_RESET}")


# ── Launch flow ───────────────────────────────────────────────────────────────

def cmd_run(args: argparse.Namespace, info: SystemInfo) -> None:
    """Launch Karl, auto-installing first if the venv is missing."""
    venv_dir = info.venv_dir

    if venv_dir is None:
        _warn("No virtual environment found — running --install first.")
        cmd_install(args, info)
        # Re-detect after install
        venv_dir = _find_existing_venv()
        if venv_dir is None:
            _err("Installation did not produce a venv. Aborting launch.")
            raise SystemExit(1)

    python = _venv_executables(venv_dir)["python"]

    if not python.exists():
        _err(f"Python not found in venv: {python}")
        _info("Run  python setup_karl.py --install  to rebuild the environment.")
        raise SystemExit(1)

    if not MAIN_PY.exists():
        _err(f"main.py not found: {MAIN_PY}")
        raise SystemExit(1)

    _head("Launching Karl")
    _info(f"Python: {python}")
    _info(f"Entry:  {MAIN_PY}")

    # Forward any extra positional args from the CLI to main.py.
    launch_cmd = [str(python), str(MAIN_PY)] + args.passthrough

    _sep()
    # Replace the current process image on Unix for zero-overhead hand-off.
    # On Windows, os.execv is available but the semantics differ; fall back to
    # subprocess so the bootstrapper process waits and propagates the exit code.
    if platform.system() != "Windows":
        os.chdir(REPO_ROOT)
        os.execv(str(python), launch_cmd)
    else:
        os.chdir(REPO_ROOT)
        result = subprocess.run(launch_cmd)
        raise SystemExit(result.returncode)


# ── Info command ──────────────────────────────────────────────────────────────

def cmd_info(info: SystemInfo) -> None:
    _head("Karl System Information")
    _sep()
    _print_info(info)
    cmake = build_cmake_args(info.gpu_type)
    _info(f"Computed CMAKE_ARGS: {_BOLD}{cmake or '(none — CPU build)'}{_RESET}")
    _sep()


def _print_info(info: SystemInfo) -> None:
    os_pretty = {
        "Darwin":  f"macOS ({info.arch})",
        "Windows": f"Windows ({info.arch})",
        "Linux":   f"Linux ({info.arch})",
    }.get(info.os_name, f"{info.os_name} ({info.arch})")

    _info(f"OS:         {os_pretty}")
    _info(f"Python:     {info.python_ver}  ({'in venv' if info.in_venv else 'system'})")
    _info(f"GPU:        {info.gpu_label}")

    if info.venv_dir:
        _info(f"Venv:       {info.venv_dir}")
    else:
        _warn("Venv:       not found (run --install)")


# ── Python version guard ──────────────────────────────────────────────────────

def _check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        _err(
            f"Karl requires Python {'.'.join(map(str, MIN_PYTHON))}+. "
            f"You are running {platform.python_version()}."
        )
        raise SystemExit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="setup_karl.py",
        description="Karl cross-platform bootstrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", action="store_true", help="Set up venv and install dependencies")
    mode.add_argument("--run",     action="store_true", help="Launch Karl (installs if needed)")
    mode.add_argument("--info",    action="store_true", help="Print system detection results and exit")

    # Install modifiers
    parser.add_argument("--force",  action="store_true", help="Wipe and recreate the venv from scratch")
    parser.add_argument("--cpu",    action="store_true", help="Force CPU-only llama-cpp-python build")
    parser.add_argument("--cuda",   action="store_true", help="Force CUDA build (skip auto-detection)")
    parser.add_argument("--metal",  action="store_true", help="Force Metal build (macOS only)")

    # Extra args forwarded to main.py when using --run
    parser.add_argument(
        "passthrough",
        nargs=argparse.REMAINDER,
        help="Extra flags forwarded to main.py (only with --run)",
    )

    return parser


def main() -> None:
    _check_python_version()

    parser = _build_parser()
    args = parser.parse_args()

    # Ensure we run from the repo root so relative paths work.
    os.chdir(REPO_ROOT)

    info = detect_system()

    if args.info:
        cmd_info(info)
        return

    if args.install:
        cmd_install(args, info)
        return

    if args.run:
        cmd_run(args, info)
        return


if __name__ == "__main__":
    main()
