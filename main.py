"""
Karl -- entry point.
All library noise is suppressed here, before any third-party import runs.
"""

# ruff: noqa: E402

# ── 1. Environment variables ──────────────────────────────────────────────────
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Silence HuggingFace network calls and telemetry
os.environ["HF_HUB_OFFLINE"]               = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"]    = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_OFFLINE"]         = "1"
os.environ["TOKENIZERS_PARALLELISM"]       = "false"
os.environ["TRITON_SUPPRESS_WARNINGS"]     = "1"

# ── 2. Python warnings ────────────────────────────────────────────────────────
import warnings
warnings.filterwarnings("ignore")

# ── 3. Redirect the OS-level stderr during noisy library imports ──────────────
# Some C-extensions (triton, torch cpp) write directly to fd=2 before Python
# warning filters run. We swap stderr for /dev/null at the file-descriptor level
# for the duration of the heavy imports, then restore it.

class _NullFD:
    """Context manager: redirects fd 2 (stderr) to os.devnull at C level."""
    def __enter__(self):
        self._orig_fd2 = os.dup(2)          # save real stderr fd
        self._devnull  = os.open(os.devnull, os.O_WRONLY)
        os.dup2(self._devnull, 2)            # point fd 2 at /dev/null
        return self

    def __exit__(self, *_):
        os.dup2(self._orig_fd2, 2)           # restore real stderr
        os.close(self._orig_fd2)
        os.close(self._devnull)


with _NullFD():
    # All noisy imports go here -- their C-level stderr goes to /dev/null
    import torch          # noqa: F401  (triggers triton + cpp warnings)
    import faiss          # noqa: F401
    from sentence_transformers import SentenceTransformer  # noqa: F401

# ── 4. Python-level logging: mute library loggers ─────────────────────────────
import logging

for _name in [
    "torch", "torch.distributed",
    "torch.distributed.elastic.multiprocessing.redirects",
    "triton", "transformers", "sentence_transformers",
    "huggingface_hub", "huggingface_hub.utils",
    "filelock", "faiss", "urllib3", "requests",
]:
    _log = logging.getLogger(_name)
    _log.setLevel(logging.CRITICAL)
    _log.propagate = False

# Silence absl (used by torch internally for the "W0523..." lines)
try:
    import absl.logging as _absl_log
    _absl_log.set_verbosity(_absl_log.FATAL)
    logging.getLogger("absl").setLevel(logging.CRITICAL)
except Exception:
    pass

# ── 5. Application ────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Karl")

    # Minimal inline base stylesheet (pure ASCII, no file read).
    # Full theme applied by MainWindow after init.
    app.setStyleSheet(
        "QMainWindow, QWidget {"
        "background-color: #0D0D0F; color: #DDDDE0;"
        "font-family: 'Segoe UI', Inter, Arial, sans-serif; font-size: 11pt; }"
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
