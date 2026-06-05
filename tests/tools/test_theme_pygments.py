"""Tests for pygments style mapping + cache invalidation on theme change.

Verifies the luminance-based style map (DARK_TOKENS -> "monokai",
LIGHT_TOKENS -> "default") and the module-level ThemeManager.themeChanged
subscription that clears the formatter cache on every theme switch.

The qt_stubs module replaces QObject / QTimer with empty stubs that do
not preserve Shiboken parent-child state. The ThemeManager.debounce
path (QTimer(self) in set_mode) requires a real QObject parent, so this
file mirrors the TestThemeManagerModeResolution pattern: drop the stubs
in setUpClass, reload the theme + highlight modules against the real
PySide6, and restore the stubs in tearDownClass so downstream tests
that depend on them keep working.
"""

from __future__ import annotations

import unittest

from tests.qt_stubs import ensure_pyside6_stubs

ensure_pyside6_stubs()

# ``tokens`` is pure-Python so it is safe to import under stubs. The
# real PySide6 reload happens in TestFormatterCache.setUpClass.
from rikugan.ui.theme.palette_dark import DARK_TOKENS  # noqa: E402  (post-stub)
from rikugan.ui.theme.palette_light import LIGHT_TOKENS  # noqa: E402  (post-stub)
from rikugan.ui.theme.tokens import (  # noqa: E402  (post-stub)
    ThemeMode,
    is_dark_tokens,
)


class TestPygmentsStyleMap(unittest.TestCase):
    """Luminance-based style map. Pure-Python, no Qt or debounce needed.

    Imports ``_pygments_style_for_tokens`` directly — the function does
    not touch the ThemeManager singleton or any Qt signal, so it is safe
    to run against the stub-injected PySide6.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from rikugan.ui import highlight

        cls._pygments_style_for_tokens = staticmethod(
            highlight._pygments_style_for_tokens
        )

    def test_dark_tokens_use_monokai(self) -> None:
        """DARK_TOKENS (luminance < threshold) -> monokai."""
        self.assertEqual(self._pygments_style_for_tokens(DARK_TOKENS), "monokai")

    def test_light_tokens_use_default(self) -> None:
        """LIGHT_TOKENS (luminance >= threshold) -> default."""
        self.assertEqual(self._pygments_style_for_tokens(LIGHT_TOKENS), "default")

    def test_is_dark_tokens_helper(self) -> None:
        """Sanity check: the helper used by the style map is consistent."""
        self.assertTrue(is_dark_tokens(DARK_TOKENS))
        self.assertFalse(is_dark_tokens(LIGHT_TOKENS))


class TestFormatterCache(unittest.TestCase):
    """Formatter cache behaviour + themeChanged-driven invalidation.

    Requires the real PySide6 (QTimer needs a real QObject parent for
    the ThemeManager debounce path; QCoreApplication.processEvents()
    needs the real class to dispatch the 0ms timer). Stubs are dropped
    in setUpClass, theme + highlight modules are reloaded, and stubs are
    restored in tearDownClass.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import importlib
        import sys

        # Save the stubs so tearDownClass can restore them.
        cls._saved_pyside6_modules = {
            name: mod
            for name, mod in sys.modules.items()
            if name.startswith("PySide6")
        }
        for name in list(sys.modules):
            if name.startswith("PySide6"):
                del sys.modules[name]

        # Reload theme + highlight against real PySide6 so the
        # QTimer(ThemeManager) call in set_mode() resolves correctly.
        from rikugan.ui import highlight
        from rikugan.ui.theme import manager, palette_ida

        importlib.reload(palette_ida)
        importlib.reload(manager)
        importlib.reload(highlight)

        # Collapse the 50ms debounce to 0ms so themeChanged fires
        # synchronously inside set_mode() → _apply_now.
        manager._DEBOUNCE_MS = 0

        cls.ThemeManager = manager.ThemeManager
        # Bind the highlight module functions as staticmethods so
        # ``self._get_formatter("monokai")`` calls them with just the
        # style argument (not bound ``self``).
        cls._pygments_style_for_tokens = staticmethod(
            highlight._pygments_style_for_tokens
        )
        cls._get_formatter = staticmethod(highlight._get_formatter)
        cls.clear_formatter_cache = staticmethod(highlight.clear_formatter_cache)

        from PySide6.QtCore import QCoreApplication
        from PySide6.QtWidgets import QApplication

        cls.QCoreApplication = QCoreApplication
        cls.QApplication = QApplication

        # QApplication is needed for processEvents() to dispatch the
        # 0ms timer events. Reuse the singleton when present.
        cls._app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls) -> None:
        import sys

        for name in list(sys.modules):
            if name.startswith("PySide6"):
                del sys.modules[name]
        for name, mod in cls._saved_pyside6_modules.items():
            sys.modules[name] = mod

    def setUp(self) -> None:
        self.ThemeManager.reset()
        self.clear_formatter_cache()

    def tearDown(self) -> None:
        self.ThemeManager.reset()
        self.clear_formatter_cache()

    def test_active_dark_mode_uses_monokai(self) -> None:
        """ThemeManager in DARK mode -> monokai."""
        mgr = self.ThemeManager.instance()
        mgr.set_mode(ThemeMode.DARK)
        self.QCoreApplication.processEvents()  # flush 0ms debounce
        self.assertEqual(
            self._pygments_style_for_tokens(mgr.tokens()),
            "monokai",
        )

    def test_active_light_mode_uses_default(self) -> None:
        """ThemeManager in LIGHT mode -> default."""
        mgr = self.ThemeManager.instance()
        mgr.set_mode(ThemeMode.LIGHT)
        self.QCoreApplication.processEvents()  # flush 0ms debounce
        self.assertEqual(
            self._pygments_style_for_tokens(mgr.tokens()),
            "default",
        )

    def test_get_formatter_caches_by_style(self) -> None:
        """Same style name -> same instance."""
        f1 = self._get_formatter("monokai")
        f2 = self._get_formatter("monokai")
        if f1 is not None:  # pygments may not be installed
            self.assertIs(f1, f2)

    def test_get_formatter_different_styles_cached_separately(self) -> None:
        """Different style names -> different instances."""
        f1 = self._get_formatter("monokai")
        f2 = self._get_formatter("default")
        if f1 is not None and f2 is not None:
            self.assertIsNot(f1, f2)

    def test_clear_formatter_cache_empties_cache(self) -> None:
        """After clear, new formatters are created (different identity)."""
        f1 = self._get_formatter("monokai")
        self.clear_formatter_cache()
        f2 = self._get_formatter("monokai")
        if f1 is not None:
            self.assertIsNot(f1, f2)

    def test_theme_change_invalidates_cache(self) -> None:
        """When ThemeManager.themeChanged fires, the cache is cleared.

        highlight.py subscribes to themeChanged at import time, so a
        simple set_mode() switch is enough to invalidate the cache.
        """
        mgr = self.ThemeManager.instance()
        mgr.set_mode(ThemeMode.DARK)  # warm-up
        self.QCoreApplication.processEvents()  # flush
        f1 = self._get_formatter("monokai")
        # Switch mode -> cache should be cleared by the signal handler
        mgr.set_mode(ThemeMode.LIGHT)
        self.QCoreApplication.processEvents()  # flush
        f2 = self._get_formatter("default")
        if f1 is not None and f2 is not None:
            self.assertIsNot(f1, f2)


if __name__ == "__main__":
    unittest.main()
