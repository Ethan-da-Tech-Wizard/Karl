"""
Karl Startup Diagnostics Engine
=================================
Invoked via:  python main.py --diagnose

Checks:
  1. Dependency audit   — importability + versions of key packages
  2. Hardware scout     — CPU ISA flags (AVX2/AVX-512/FMA), CUDA/Metal GPU
  3. Model verification — GGUF files in data/models/, active model presence + magic
  4. Network port audit — whether the default WebSocket port (8080) is free

Outputs:
  • Colour-coded terminal table ([OK  ] / [WARN] / [FAIL] rows)
  • JSON report at data/logs/diagnostics_report.json

Returns:
  0  — all critical checks passed
  1  — at least one critical check failed
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

_REPORT_PATH = "data/logs/diagnostics_report.json"
_GGUF_MAGIC = b"GGUF"

# ── ANSI helpers ──────────────────────────────────────────────────────────────
_USE_ANSI = sys.stdout.isatty()


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _USE_ANSI else s


def _green(s: str) -> str:  return _c("32", s)
def _red(s: str) -> str:    return _c("31", s)
def _yellow(s: str) -> str: return _c("33", s)
def _cyan(s: str) -> str:   return _c("36", s)
def _bold(s: str) -> str:   return _c("1", s)
def _dim(s: str) -> str:    return _c("2", s)


_OK   = _green("[OK  ]")
_WARN = _yellow("[WARN]")
_FAIL = _red("[FAIL]")


def _row(badge: str, label: str, detail: str = "") -> str:
    return f"  {badge} {label:<30} {detail}".rstrip()


# ── 1. Dependency Audit ───────────────────────────────────────────────────────

_PACKAGES: list[tuple[str, str, str]] = [
    # (display_name, importable_module,   version_attr_on_module)
    ("PyQt6",                "PyQt6.QtCore",          "PYQT_VERSION_STR"),
    ("llama_cpp",            "llama_cpp",             "__version__"),
    ("sentence_transformers","sentence_transformers",  "__version__"),
    ("faiss",                "faiss",                 "__version__"),
]

_CRITICAL_DEPS = {"PyQt6", "llama_cpp"}


def _metadata_version(name: str) -> str | None:
    for candidate in (name, name.replace("_", "-"),
                      name + "-cpu", name + "-gpu"):
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            pass
    return None


def check_dependencies() -> dict[str, Any]:
    results: dict[str, Any] = {}
    for display, module_path, attr in _PACKAGES:
        try:
            mod = importlib.import_module(module_path)
            version = getattr(mod, attr, None) or _metadata_version(display) or "unknown"
            results[display] = {"status": "ok", "version": str(version)}
        except ImportError as exc:
            results[display] = {"status": "fail", "error": str(exc)}
    return results


# ── 2. Hardware Capability Scout ─────────────────────────────────────────────

def _linux_cpu_flags() -> set[str]:
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("flags"):
                    return set(line.split(":", 1)[1].split())
    except OSError:
        pass
    return set()


def _macos_sysctl(key: str) -> str:
    try:
        res = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True, text=True, timeout=3,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def check_hardware() -> dict[str, Any]:
    plat = platform.system()
    result: dict[str, Any] = {"platform": plat}

    # CPU instruction-set flags
    cpu_flags: dict[str, bool | None] = {}
    if plat == "Linux":
        flags = _linux_cpu_flags()
        cpu_flags = {
            "avx2":   "avx2"    in flags,
            "avx512": "avx512f" in flags,
            "fma":    "fma"     in flags,
        }
    elif plat == "Darwin":
        cpu_flags = {
            "avx2":   _macos_sysctl("hw.optional.avx2_0") == "1",
            "avx512": _macos_sysctl("hw.optional.avx512f") == "1",
            "fma":    _macos_sysctl("hw.optional.fma")    == "1",
        }
    else:
        # Windows: would need cpuid; skip gracefully
        cpu_flags = {"avx2": None, "avx512": None, "fma": None}
    result["cpu_flags"] = cpu_flags

    # GPU frameworks
    gpu_info: dict[str, Any] = {}
    try:
        import torch  # noqa: PLC0415
        cuda_ok = torch.cuda.is_available()
        gpu_info["torch_cuda"] = {
            "available":      cuda_ok,
            "device":         torch.cuda.get_device_name(0) if cuda_ok else None,
            "driver_version": torch.version.cuda if cuda_ok else None,
        }
        metal_ok = (
            hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        )
        gpu_info["torch_metal"] = {"available": metal_ok}
    except Exception as exc:
        gpu_info["torch_error"] = str(exc)
    result["gpu"] = gpu_info

    return result


# ── 3. Model Verification ─────────────────────────────────────────────────────

def _read_active_filename() -> str | None:
    try:
        with open("data/active_model.json", "r", encoding="utf-8") as fh:
            return json.load(fh).get("filename")
    except Exception:
        return None


def _gguf_magic_ok(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == _GGUF_MAGIC
    except OSError:
        return False


def check_models() -> dict[str, Any]:
    models_dir = "data/models"
    active_filename = _read_active_filename()
    result: dict[str, Any] = {
        "models_dir":      models_dir,
        "active_filename": active_filename,
        "files":           [],
    }

    if not os.path.isdir(models_dir):
        result["status"]  = "warn"
        result["message"] = f"models directory not found: {models_dir}"
        return result

    gguf_files = sorted(f for f in os.listdir(models_dir) if f.endswith(".gguf"))

    for filename in gguf_files:
        path = os.path.join(models_dir, filename)
        try:
            size_bytes = os.path.getsize(path)
        except OSError:
            size_bytes = 0
        magic_ok = _gguf_magic_ok(path)
        result["files"].append({
            "filename":    filename,
            "active":      filename == active_filename,
            "size_bytes":  size_bytes,
            "size_gb":     round(size_bytes / (1024 ** 3), 2),
            "gguf_magic_ok": magic_ok,
            "status":      "ok" if magic_ok else "fail",
        })

    if not gguf_files:
        result["status"]  = "warn"
        result["message"] = "no .gguf files found in data/models/"
    elif active_filename and active_filename not in gguf_files:
        result["status"]  = "fail"
        result["message"] = f"active model not found: {active_filename}"
    else:
        result["status"] = "ok"

    return result


# ── 4. Network Port Audit ─────────────────────────────────────────────────────

def check_port(port: int = 8080) -> dict[str, Any]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
        return {"port": port, "status": "ok",   "message": f"port {port} is free"}
    except OSError as exc:
        return {"port": port, "status": "warn",  "message": f"port {port} in use: {exc}"}


# ── Terminal renderer ─────────────────────────────────────────────────────────

def _render(report: dict[str, Any]) -> bool:
    """
    Print the colour-coded diagnostics table.
    Returns True if no *critical* check failed.
    """
    div = _cyan("─" * 52)
    header_bar = _bold(_cyan("═" * 52))

    print()
    print(header_bar)
    print(_bold("  Karl Startup Diagnostics"))
    print(header_bar)

    critical_failures: list[str] = []

    # ── Dependencies ─────────────────────────────────────────────────────────
    print(f"\n{div}")
    print(_bold("  Dependencies"))
    print(div)
    for name, info in report["checks"]["dependencies"].items():
        if info["status"] == "ok":
            print(_row(_OK, name, _dim(info.get("version", ""))))
        else:
            is_critical = name in _CRITICAL_DEPS
            badge = _FAIL if is_critical else _WARN
            print(_row(badge, name, _red(info.get("error", "import failed"))))
            if is_critical:
                critical_failures.append(f"dependency:{name}")

    # ── Hardware ─────────────────────────────────────────────────────────────
    print(f"\n{div}")
    print(_bold("  Hardware"))
    print(div)
    hw = report["checks"]["hardware"]
    for flag, present in hw.get("cpu_flags", {}).items():
        label = f"CPU {flag.upper()}"
        if present is None:
            print(_row(_WARN, label, "detection unsupported on this platform"))
        elif present:
            print(_row(_OK, label, ""))
        else:
            print(_row(_WARN, label, "not detected"))

    gpu = hw.get("gpu", {})
    if "torch_error" in gpu:
        print(_row(_WARN, "GPU frameworks", _yellow(gpu["torch_error"])))
    else:
        cuda = gpu.get("torch_cuda", {})
        if cuda.get("available"):
            device = cuda.get("device", "")
            drv    = cuda.get("driver_version") or ""
            detail = f"{device}" + (f"  cuda {drv}" if drv else "")
            print(_row(_OK, "CUDA", _dim(detail)))
        else:
            print(_row(_WARN, "CUDA", "not available"))

        metal = gpu.get("torch_metal", {})
        if metal.get("available"):
            print(_row(_OK, "Metal (Apple Silicon)", ""))

    # ── Models ───────────────────────────────────────────────────────────────
    print(f"\n{div}")
    print(_bold("  Models"))
    print(div)
    mc = report["checks"]["models"]
    if mc["status"] == "fail":
        print(_row(_FAIL, "active model", _red(mc.get("message", ""))))
        critical_failures.append("model:active_not_found")
    elif mc["status"] == "warn":
        print(_row(_WARN, "models", _yellow(mc.get("message", ""))))
    else:
        files = mc.get("files", [])
        if not files:
            print(_row(_WARN, "models", "no .gguf files found"))
        for f in files:
            label = f["filename"]
            if f["active"]:
                label += "  " + _dim("[active]")
            detail = f"{f['size_gb']:.2f} GB"
            if f["gguf_magic_ok"]:
                print(_row(_OK, label, _dim(detail)))
            else:
                print(_row(_FAIL, label, _red(f"{detail}  — GGUF magic invalid (corrupt?)")))
                critical_failures.append(f"model:{f['filename']}:corrupt")

    # ── Network ──────────────────────────────────────────────────────────────
    print(f"\n{div}")
    print(_bold("  Network"))
    print(div)
    net = report["checks"]["network"]
    if net["status"] == "ok":
        print(_row(_OK, f"Port {net['port']}", _dim(net["message"])))
    else:
        print(_row(_WARN, f"Port {net['port']}", _yellow(net["message"])))

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    print(header_bar)
    if critical_failures:
        print(_bold(_red(f"  FAILED  — {len(critical_failures)} critical check(s) did not pass:")))
        for item in critical_failures:
            print(f"    {_red('✗')} {item}")
    else:
        print(_bold(_green("  PASSED  — all critical checks OK")))
    print(f"  {_dim('Report:')} {_REPORT_PATH}")
    print(header_bar)
    print()

    return not critical_failures


# ── Entry point ───────────────────────────────────────────────────────────────

def run_diagnostics() -> int:
    """
    Run all checks, print the terminal table, and write the JSON report.
    Returns 0 on success, 1 on critical failure.
    """
    ts = datetime.now(timezone.utc).isoformat()

    report: dict[str, Any] = {
        "ts":       ts,
        "platform": platform.platform(),
        "python":   sys.version,
        "checks": {
            "dependencies": check_dependencies(),
            "hardware":     check_hardware(),
            "models":       check_models(),
            "network":      check_port(8080),
        },
    }

    all_passed = _render(report)
    report["overall_status"] = "ok" if all_passed else "fail"

    try:
        os.makedirs(os.path.dirname(_REPORT_PATH), exist_ok=True)
        with open(_REPORT_PATH, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"  warning: could not write report file: {exc}", file=sys.stderr)

    return 0 if all_passed else 1
