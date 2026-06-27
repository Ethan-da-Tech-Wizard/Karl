"""
Local Feature Flag Registry and Boot Guard utilities.

Feature flags are persisted in data/feature_flags.json as a flat JSON dict.
The boot guard uses data/boot_in_progress.lock to detect crashes during PyQt
initialisation and automatically enter Safe Mode on the next boot.
"""

from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger("karl.feature_flags")

# ── Canonical paths ───────────────────────────────────────────────────────────

FLAGS_FILE = "data/feature_flags.json"
LOCK_FILE  = "data/boot_in_progress.lock"

# ── Feature Flag Store ────────────────────────────────────────────────────────


class FeatureFlagStore:
    """Read/write feature flags to a JSON file with in-memory caching.

    Args:
        path: Override the default flags file location (useful in tests).
    """

    # Registered flags and their shipping defaults.
    DEFAULTS: dict[str, bool] = {
        "experimental_speculative_decoding": False,
        "multimodal_vision_ocr":             False,
        "agentic_swarming_loops":            True,
    }

    # Subset of flags considered "experimental" — these are disabled in Safe Mode.
    EXPERIMENTAL: frozenset[str] = frozenset({
        "experimental_speculative_decoding",
        "multimodal_vision_ocr",
    })

    # Class-level indicator so any module can check safe-mode status without
    # holding a reference to a specific store instance.
    safe_mode_active: bool = False

    def __init__(self, path: str = FLAGS_FILE) -> None:
        self._path = path
        # Start from the compiled defaults then overlay the persisted values.
        self._flags: dict[str, bool] = dict(self.DEFAULTS)
        self._load()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            self._save()   # write defaults on first run
            return
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("flags file is not a JSON object")
            # Only load keys that are registered — ignore unknown entries.
            for key, default in self.DEFAULTS.items():
                raw = data.get(key)
                self._flags[key] = bool(raw) if isinstance(raw, bool) else default
            logger.debug("Feature flags loaded from %s: %s", self._path, self._flags)
        except Exception as exc:
            logger.warning("Could not load feature flags (%s) — using defaults.", exc)
            self._flags = dict(self.DEFAULTS)
            self._save()

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._flags, fh, indent=2)
        except Exception as exc:
            logger.warning("Could not persist feature flags: %s", exc)

    # ── public API ────────────────────────────────────────────────────────────

    def is_enabled(self, flag_name: str) -> bool:
        """Return the boolean value of *flag_name* (False for unknown flags)."""
        return bool(self._flags.get(flag_name, False))

    def set_flag(self, flag_name: str, value: bool) -> None:
        """Enable or disable *flag_name* and persist to disk.

        Raises:
            KeyError: When *flag_name* is not a registered flag.
        """
        if flag_name not in self.DEFAULTS:
            raise KeyError(f"Unknown feature flag: {flag_name!r}")
        self._flags[flag_name] = bool(value)
        self._save()
        logger.info("Feature flag %r set to %s.", flag_name, value)

    def enter_safe_mode(self) -> None:
        """Disable every experimental flag and mark safe mode as active."""
        for flag in self.EXPERIMENTAL:
            self._flags[flag] = False
        self._save()
        FeatureFlagStore.safe_mode_active = True
        logger.warning(
            "Safe Mode activated — experimental flags disabled: %s",
            sorted(self.EXPERIMENTAL),
        )

    def all_flags(self) -> dict[str, bool]:
        """Return a copy of the current flag state."""
        return dict(self._flags)


# ── Boot Guard ────────────────────────────────────────────────────────────────


def check_boot_lock(lock_path: str = LOCK_FILE) -> bool:
    """Return True if a crash lock from a previous run exists."""
    return os.path.exists(lock_path)


def create_boot_lock(lock_path: str = LOCK_FILE) -> None:
    """Write the boot lock file with the current timestamp."""
    try:
        os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
        with open(lock_path, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
        logger.debug("Boot lock created: %s", lock_path)
    except Exception as exc:
        logger.warning("Could not create boot lock: %s", exc)


def release_boot_lock(lock_path: str = LOCK_FILE) -> None:
    """Remove the boot lock file (called after successful window render)."""
    try:
        os.remove(lock_path)
        logger.debug("Boot lock released: %s", lock_path)
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.warning("Could not remove boot lock: %s", exc)


def run_boot_guard(
    store: FeatureFlagStore,
    lock_path: str = LOCK_FILE,
) -> bool:
    """Check for a prior-crash lock and act accordingly.

    * **Lock present** — a previous boot crashed before the window rendered.
      Enters Safe Mode on *store*, logs a critical warning, returns ``True``.
    * **Lock absent** — normal boot.  Creates the lock so a crash during this
      boot will be detected next time.  Returns ``False``.
    """
    if check_boot_lock(lock_path):
        logger.critical(
            "Boot lock detected (%s). Previous initialization crashed. "
            "Entering Safe Mode and disabling all experimental features.",
            lock_path,
        )
        store.enter_safe_mode()
        return True

    create_boot_lock(lock_path)
    return False
