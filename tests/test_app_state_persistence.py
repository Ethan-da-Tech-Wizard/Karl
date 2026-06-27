"""Focused tests for AppState.load_from_disk() and AppState.save_to_disk()."""

import tests.qt_test_helper  # noqa: F401  — must come first to init QApplication

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.state import AppState, _PERSIST_FIELDS
from app.engine import config_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEAVY_PATCHES = [
    patch("app.state.RAGPipeline", return_value=MagicMock()),
    patch("app.state.MemoryManager", return_value=MagicMock()),
    patch("app.state.TraceLogger", return_value=MagicMock()),
    patch("app.state.TrainingCurator", return_value=MagicMock()),
    patch("app.state.ImageStore", return_value=MagicMock()),
]


def _start_patches():
    mocks = [p.start() for p in _HEAVY_PATCHES]
    return mocks


def _stop_patches():
    for p in _HEAVY_PATCHES:
        p.stop()


# ---------------------------------------------------------------------------
# Test fixture
# ---------------------------------------------------------------------------

class TestAppStatePersistence(unittest.TestCase):
    """AppState.load_from_disk / save_to_disk — isolated from disk and heavy deps."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()
        os.chdir(self._tmpdir)
        # Reset config_store registry cache (unrelated but avoids stale state)
        config_store._registry_cache = None
        config_store._registry_cache_mtime = None
        _start_patches()

    def tearDown(self):
        _stop_patches()
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    # ── defaults ─────────────────────────────────────────────────────────────

    def test_defaults_when_no_file(self):
        """Fresh AppState with no file on disk should have hardcoded defaults."""
        state = AppState()
        self.assertAlmostEqual(state.rag_threshold, 0.0)
        self.assertEqual(state.rag_top_k, 3)
        self.assertEqual(state.theme_mode, "midnight")
        self.assertEqual(state.theme_preset, "Karl Obsidian Core")
        self.assertIsNone(state.custom_accent)
        self.assertEqual(state.layout_preset, "Focused Workbench")
        self.assertFalse(state.reduced_motion)
        self.assertTrue(state.glow_enabled)
        self.assertAlmostEqual(state.animation_intensity, 1.0)
        self.assertAlmostEqual(state.glow_strength, 1.0)
        self.assertEqual(state.log_rotation_size_mb, 10)
        self.assertEqual(state.log_retention_days, 30)
        self.assertFalse(state.single_session_auth)
        self.assertTrue(state.thermal_protection_enabled)
        self.assertEqual(state.thermal_protection_threshold, 95)
        self.assertTrue(state.enable_dynamic_scheduling)
        self.assertAlmostEqual(state.thinking_temperature, 0.8)
        self.assertAlmostEqual(state.answering_temperature, 0.1)

    # ── save / load roundtrip ─────────────────────────────────────────────

    def test_save_to_disk_creates_file(self):
        state = AppState()
        result = state.save_to_disk()
        self.assertTrue(result)
        self.assertTrue(os.path.exists(config_store.UI_CONFIG_PATH))

    def test_save_and_load_roundtrip(self):
        """Modified values survive a save→new-instance→load cycle."""
        state1 = AppState()
        state1.rag_threshold = 0.42
        state1.rag_top_k = 7
        state1.theme_mode = "light"
        state1.theme_preset = "Matrix Verdant"
        state1.custom_accent = "#FF5733"
        state1.layout_preset = "Max Introspection"
        state1.reduced_motion = True
        state1.glow_enabled = False
        state1.animation_intensity = 0.5
        state1.glow_strength = 0.3
        state1.log_rotation_size_mb = 25
        state1.log_retention_days = 7
        state1.single_session_auth = True
        state1.thermal_protection_enabled = False
        state1.thermal_protection_threshold = 80
        state1.enable_dynamic_scheduling = False
        state1.thinking_temperature = 0.3
        state1.answering_temperature = 0.9
        state1.save_to_disk()

        state2 = AppState()
        self.assertAlmostEqual(state2.rag_threshold, 0.42)
        self.assertEqual(state2.rag_top_k, 7)
        self.assertEqual(state2.theme_mode, "light")
        self.assertEqual(state2.theme_preset, "Matrix Verdant")
        self.assertEqual(state2.custom_accent, "#FF5733")
        self.assertEqual(state2.layout_preset, "Max Introspection")
        self.assertTrue(state2.reduced_motion)
        self.assertFalse(state2.glow_enabled)
        self.assertAlmostEqual(state2.animation_intensity, 0.5)
        self.assertAlmostEqual(state2.glow_strength, 0.3)
        self.assertEqual(state2.log_rotation_size_mb, 25)
        self.assertEqual(state2.log_retention_days, 7)
        self.assertTrue(state2.single_session_auth)
        self.assertFalse(state2.thermal_protection_enabled)
        self.assertEqual(state2.thermal_protection_threshold, 80)
        self.assertFalse(state2.enable_dynamic_scheduling)
        self.assertAlmostEqual(state2.thinking_temperature, 0.3)
        self.assertAlmostEqual(state2.answering_temperature, 0.9)

    def test_save_preserves_none_custom_accent(self):
        """custom_accent=None roundtrips correctly (not coerced to 'None' string)."""
        state1 = AppState()
        state1.custom_accent = None
        state1.save_to_disk()

        state2 = AppState()
        self.assertIsNone(state2.custom_accent)

    # ── unknown keys ─────────────────────────────────────────────────────────

    def test_unknown_keys_in_file_are_ignored(self):
        """Extra keys in ui_config.json must not raise and must not appear on state."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"theme_preset": "Matrix Verdant", "future_feature": "yes"}, f)

        state = AppState()
        self.assertEqual(state.theme_preset, "Matrix Verdant")
        self.assertFalse(hasattr(state, "future_feature"))

    def test_extra_keys_not_written_back(self):
        """save_to_disk only writes _PERSIST_FIELDS plus the schema version key."""
        state = AppState()
        state.save_to_disk()
        with open(config_store.UI_CONFIG_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        for key in payload:
            self.assertTrue(
                key in _PERSIST_FIELDS or key == "version",
                f"unexpected key in saved config: {key}",
            )

    # ── corrupt JSON fallback ─────────────────────────────────────────────

    def test_corrupt_json_falls_back_to_defaults(self):
        """A corrupt ui_config.json must not crash AppState; defaults must apply."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write("{this is not json}")

        state = AppState()
        # Should have fallen back to hardcoded defaults
        self.assertEqual(state.theme_preset, "Karl Obsidian Core")
        self.assertAlmostEqual(state.rag_threshold, 0.0)
        self.assertEqual(state.rag_top_k, 3)

    def test_non_dict_json_falls_back_to_defaults(self):
        """A valid JSON file that's not a dict (e.g. a list) falls back cleanly."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump([1, 2, 3], f)

        state = AppState()
        self.assertEqual(state.theme_mode, "midnight")

    # ── type coercion ─────────────────────────────────────────────────────

    def test_int_fields_coerced_from_float_on_disk(self):
        """rag_top_k stored as 5.0 (float) on disk must be loaded as int 5."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"rag_top_k": 5.0}, f)

        state = AppState()
        self.assertIsInstance(state.rag_top_k, int)
        self.assertEqual(state.rag_top_k, 5)

    def test_float_fields_coerced_from_int_on_disk(self):
        """rag_threshold stored as 1 (int) must be loaded as float 1.0."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"rag_threshold": 1}, f)

        state = AppState()
        self.assertIsInstance(state.rag_threshold, float)
        self.assertAlmostEqual(state.rag_threshold, 1.0)

    def test_bool_fields_not_coerced_to_int(self):
        """glow_enabled=true on disk must remain bool, not int 1."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"glow_enabled": True}, f)

        state = AppState()
        self.assertIsInstance(state.glow_enabled, bool)
        self.assertTrue(state.glow_enabled)

    def test_bad_type_on_disk_reverts_to_default(self):
        """A field with an un-coercible value on disk falls back to its default."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"rag_top_k": "not-a-number"}, f)

        state = AppState()
        self.assertEqual(state.rag_top_k, 3)

    # ── explicit load_from_disk call ──────────────────────────────────────

    def test_explicit_load_from_disk_overrides_live_values(self):
        """Calling load_from_disk() on an existing state instance reloads from file."""
        state = AppState()
        state.rag_top_k = 99          # mutate in memory
        state.save_to_disk()          # write 99 to disk

        state.rag_top_k = 1           # change again without saving
        state.load_from_disk()        # reload from disk

        self.assertEqual(state.rag_top_k, 99)

    # ── partial file ─────────────────────────────────────────────────────

    def test_partial_file_fills_gaps_with_defaults(self):
        """Only the keys present in the file are overridden; others keep defaults."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"rag_top_k": 10}, f)

        state = AppState()
        self.assertEqual(state.rag_top_k, 10)          # overridden
        self.assertAlmostEqual(state.rag_threshold, 0.0)  # default kept

    # ── _PERSIST_FIELDS completeness ─────────────────────────────────────

    def test_persist_fields_matches_ui_config_defaults(self):
        """Every key in _PERSIST_FIELDS must also appear in UI_CONFIG_DEFAULTS."""
        for key in _PERSIST_FIELDS:
            self.assertIn(
                key, config_store.UI_CONFIG_DEFAULTS,
                f"_PERSIST_FIELDS has '{key}' but UI_CONFIG_DEFAULTS does not",
            )

    def test_heavy_objects_not_in_persist_fields(self):
        """Heavy runtime objects must never be listed in _PERSIST_FIELDS."""
        excluded = {"rag", "codex_rag", "memory", "logger", "curator", "image_store"}
        for name in excluded:
            self.assertNotIn(name, _PERSIST_FIELDS)


class TestConfigCorruptionRecovery(unittest.TestCase):
    """Corrupt ui_config.json is quarantined and replaced with fresh defaults."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()
        os.chdir(self._tmpdir)
        config_store._registry_cache = None
        config_store._registry_cache_mtime = None
        _start_patches()

    def tearDown(self):
        _stop_patches()
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _data_dir_files(self):
        return os.listdir("data") if os.path.isdir("data") else []

    def test_corrupt_json_quarantines_file(self):
        """Malformed JSON causes the file to be renamed .corrupt_<ts>, not silently dropped."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            f.write("{this is not json}")

        config_store.get_ui_config()

        files = self._data_dir_files()
        corrupt_files = [f for f in files if "corrupt" in f]
        self.assertTrue(corrupt_files, "expected a .corrupt_* file after bad JSON")
        # The original path must no longer exist (it was renamed)
        original_still_corrupt = False
        if os.path.exists(config_store.UI_CONFIG_PATH):
            with open(config_store.UI_CONFIG_PATH, "r", encoding="utf-8") as f:
                original_still_corrupt = f.read().startswith("{this")
        self.assertFalse(
            original_still_corrupt,
            "original corrupt content should not still be at the config path",
        )

    def test_corrupt_json_rewrites_fresh_defaults(self):
        """After quarantine, a new ui_config.json containing defaults is written."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            f.write("<<<not json>>>")

        config_store.get_ui_config()

        self.assertTrue(os.path.exists(config_store.UI_CONFIG_PATH),
                        "fresh defaults file should be written after quarantine")
        with open(config_store.UI_CONFIG_PATH) as f:
            fresh = json.load(f)
        self.assertEqual(fresh.get("theme_preset"), "Karl Obsidian Core")
        self.assertEqual(fresh.get("version"), config_store.CONFIG_VERSION)

    def test_non_dict_json_quarantines_file(self):
        """Valid JSON with a non-dict root (e.g. a list) is also quarantined."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump([1, 2, 3], f)

        config_store.get_ui_config()

        files = self._data_dir_files()
        corrupt_files = [f for f in files if "corrupt" in f]
        self.assertTrue(corrupt_files, "non-dict root should also be quarantined")

    def test_non_dict_json_rewrites_fresh_defaults(self):
        """After quarantine of a list-root file, defaults are restored to disk."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump(["a", "b"], f)

        config_store.get_ui_config()

        with open(config_store.UI_CONFIG_PATH) as f:
            fresh = json.load(f)
        self.assertIsInstance(fresh, dict)
        self.assertEqual(fresh.get("rag_top_k"), 3)

    def test_appstate_corrupt_json_returns_defaults(self):
        """AppState created after corrupt file is quarantined should have defaults."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            f.write("not-json!")

        state = AppState()
        self.assertEqual(state.theme_preset, "Karl Obsidian Core")
        self.assertAlmostEqual(state.rag_threshold, 0.0)


class TestConfigVersioning(unittest.TestCase):
    """Schema version key is written on every save and triggers migration on load."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()
        os.chdir(self._tmpdir)
        config_store._registry_cache = None
        config_store._registry_cache_mtime = None
        _start_patches()

    def tearDown(self):
        _stop_patches()
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_version_written_on_save(self):
        """save_ui_config always writes 'version': CONFIG_VERSION to disk."""
        config_store.save_ui_config({})
        with open(config_store.UI_CONFIG_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload.get("version"), config_store.CONFIG_VERSION)

    def test_appstate_save_includes_version(self):
        """AppState.save_to_disk() produces a file with the version key."""
        state = AppState()
        state.save_to_disk()
        with open(config_store.UI_CONFIG_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload.get("version"), config_store.CONFIG_VERSION)

    def test_version_missing_loads_without_error(self):
        """A file with no version key (pre-versioning) is loaded correctly."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump({"rag_top_k": 7}, f)  # no "version" key

        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["rag_top_k"], 7)
        self.assertEqual(cfg["theme_preset"], "Karl Obsidian Core")  # default kept

    def test_version_older_loads_with_migration(self):
        """A file with a version lower than CONFIG_VERSION triggers migration and loads."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump({"version": 0, "theme_mode": "light"}, f)

        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["theme_mode"], "light")

    def test_version_future_loads_without_crash(self):
        """A file written by a newer Karl (higher version) is loaded without exception."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump({"version": 9999, "glow_enabled": False}, f)

        cfg = config_store.get_ui_config()
        self.assertFalse(cfg["glow_enabled"])

    def test_version_non_int_treated_as_v0(self):
        """A non-integer version field is treated as v0 and does not raise."""
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump({"version": "latest", "rag_top_k": 5}, f)

        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["rag_top_k"], 5)


class TestConfigFieldValidation(unittest.TestCase):
    """Per-field type and range validation in get_ui_config()."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()
        os.chdir(self._tmpdir)
        config_store._registry_cache = None
        config_store._registry_cache_mtime = None

    def tearDown(self):
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_config(self, data: dict):
        os.makedirs("data", exist_ok=True)
        with open(config_store.UI_CONFIG_PATH, "w") as f:
            json.dump(data, f)

    def test_float_above_max_uses_default(self):
        """rag_threshold above 1.0 is out of range and falls back to default."""
        self._write_config({"rag_threshold": 5.0})
        cfg = config_store.get_ui_config()
        self.assertAlmostEqual(cfg["rag_threshold"], 0.0)

    def test_float_below_min_uses_default(self):
        """A negative rag_threshold is rejected in favour of the default."""
        self._write_config({"rag_threshold": -0.1})
        cfg = config_store.get_ui_config()
        self.assertAlmostEqual(cfg["rag_threshold"], 0.0)

    def test_int_below_min_uses_default(self):
        """rag_top_k of 0 is below the minimum of 1 and falls back to default."""
        self._write_config({"rag_top_k": 0})
        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["rag_top_k"], 3)

    def test_int_above_max_uses_default(self):
        """rag_top_k of 200 is above the maximum of 100 and falls back to default."""
        self._write_config({"rag_top_k": 200})
        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["rag_top_k"], 3)

    def test_bool_field_as_int_uses_default(self):
        """glow_enabled stored as integer 1 (not bool) is rejected."""
        self._write_config({"glow_enabled": 1})
        cfg = config_store.get_ui_config()
        # Must fall back to the hardcoded default (True) rather than accepting int 1
        self.assertIsInstance(cfg["glow_enabled"], bool)
        self.assertTrue(cfg["glow_enabled"])

    def test_bool_field_as_string_uses_default(self):
        """glow_enabled stored as string 'true' is rejected."""
        self._write_config({"glow_enabled": "true"})
        cfg = config_store.get_ui_config()
        self.assertIsInstance(cfg["glow_enabled"], bool)

    def test_str_field_as_int_uses_default(self):
        """theme_preset stored as an integer is rejected."""
        self._write_config({"theme_preset": 42})
        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["theme_preset"], "Karl Obsidian Core")

    def test_valid_boundary_values_accepted(self):
        """Values exactly at the boundary of valid ranges must be accepted."""
        self._write_config({
            "rag_threshold": 0.0,       # min
            "animation_intensity": 2.0, # max
            "rag_top_k": 1,             # min
            "thermal_protection_threshold": 105,  # max
        })
        cfg = config_store.get_ui_config()
        self.assertAlmostEqual(cfg["rag_threshold"], 0.0)
        self.assertAlmostEqual(cfg["animation_intensity"], 2.0)
        self.assertEqual(cfg["rag_top_k"], 1)
        self.assertEqual(cfg["thermal_protection_threshold"], 105)

    def test_custom_accent_none_is_valid(self):
        """custom_accent=null (None) is a valid value and must not be rejected."""
        self._write_config({"custom_accent": None})
        cfg = config_store.get_ui_config()
        self.assertIsNone(cfg["custom_accent"])

    def test_custom_accent_string_is_valid(self):
        """custom_accent as a hex string is valid."""
        self._write_config({"custom_accent": "#FF5733"})
        cfg = config_store.get_ui_config()
        self.assertEqual(cfg["custom_accent"], "#FF5733")

    def test_custom_accent_int_uses_default(self):
        """custom_accent as an integer (neither str nor None) is rejected."""
        self._write_config({"custom_accent": 12345})
        cfg = config_store.get_ui_config()
        self.assertIsNone(cfg["custom_accent"])  # default is None

    def test_temperature_out_of_range_uses_default(self):
        """thinking_temperature above 2.0 is out of range."""
        self._write_config({"thinking_temperature": 3.0})
        cfg = config_store.get_ui_config()
        self.assertAlmostEqual(cfg["thinking_temperature"], 0.8)

    def test_valid_config_passes_through_unchanged(self):
        """A well-formed config is returned verbatim (no spurious resets)."""
        self._write_config({
            "rag_threshold": 0.65,
            "rag_top_k": 5,
            "theme_preset": "Matrix Verdant",
            "glow_enabled": False,
            "animation_intensity": 0.75,
            "thinking_temperature": 1.2,
        })
        cfg = config_store.get_ui_config()
        self.assertAlmostEqual(cfg["rag_threshold"], 0.65)
        self.assertEqual(cfg["rag_top_k"], 5)
        self.assertEqual(cfg["theme_preset"], "Matrix Verdant")
        self.assertFalse(cfg["glow_enabled"])
        self.assertAlmostEqual(cfg["animation_intensity"], 0.75)
        self.assertAlmostEqual(cfg["thinking_temperature"], 1.2)


if __name__ == "__main__":
    unittest.main()
