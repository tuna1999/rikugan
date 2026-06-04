"""Tests for rikugan.core.config theme_mode migration and validation."""

from __future__ import annotations

import sys
import unittest
from dataclasses import asdict

from tests.qt_stubs import ensure_pyside6_stubs

ensure_pyside6_stubs()

# Force-remove any stub that other test files (test_panel_core,
# test_settings_dialog) may have registered for rikugan.core.config so we
# always import the real module here.
sys.modules.pop("rikugan.core.config", None)
from rikugan.core.config import (  # noqa: E402
    RikuganConfig,
    _migrate_v1_to_v2,
    _validate_theme_mode,
)


class TestV1ToV2Migration(unittest.TestCase):
    def test_v1_dark_maps_to_dark(self):
        data = {"theme": "dark", "other_field": "x"}
        result = _migrate_v1_to_v2(data)
        self.assertEqual(result["theme_mode"], "dark")
        self.assertNotIn("theme", result)
        self.assertEqual(result["other_field"], "x")

    def test_v1_ida_native_maps_to_ida(self):
        data = {"theme": "ida_native"}
        self.assertEqual(_migrate_v1_to_v2(data)["theme_mode"], "ida")

    def test_v1_light_maps_to_light(self):
        data = {"theme": "light"}
        self.assertEqual(_migrate_v1_to_v2(data)["theme_mode"], "light")

    def test_v1_unknown_falls_back_to_auto(self):
        data = {"theme": "rainbow"}
        self.assertEqual(_migrate_v1_to_v2(data)["theme_mode"], "auto")

    def test_v2_passthrough(self):
        data = {"theme_mode": "light"}
        self.assertEqual(_migrate_v1_to_v2(data), {"theme_mode": "light"})

    def test_both_theme_and_theme_mode_prefers_v2(self):
        """If both keys exist (corrupt config), theme_mode wins."""
        data = {"theme": "dark", "theme_mode": "light"}
        result = _migrate_v1_to_v2(data)
        self.assertEqual(result["theme_mode"], "light")
        # The "theme" key is still removed to normalize
        self.assertNotIn("theme", result)

    def test_no_theme_or_theme_mode(self):
        """Empty config / unrelated fields → unchanged."""
        data = {"other": "x"}
        self.assertEqual(_migrate_v1_to_v2(data), {"other": "x"})


class TestThemeModeValidation(unittest.TestCase):
    def test_valid_modes_unchanged(self):
        for mode in ("auto", "dark", "light", "ida"):
            data = {"theme_mode": mode}
            self.assertEqual(_validate_theme_mode(data)["theme_mode"], mode)

    def test_invalid_mode_falls_back_to_auto(self):
        data = {"theme_mode": "neon_pink"}
        result = _validate_theme_mode(data)
        self.assertEqual(result["theme_mode"], "auto")

    def test_missing_mode_gets_default(self):
        data: dict = {}
        self.assertEqual(_validate_theme_mode(data)["theme_mode"], "auto")


class TestRikuganConfigDefault(unittest.TestCase):
    def test_default_theme_mode_is_auto(self):
        config = RikuganConfig()
        self.assertEqual(config.theme_mode, "auto")

    def test_old_theme_field_does_not_exist(self):
        config = RikuganConfig()
        # The 'theme' field should be gone (renamed to theme_mode)
        self.assertFalse(hasattr(config, "theme") or "theme" in asdict(config))


if __name__ == "__main__":
    unittest.main()
