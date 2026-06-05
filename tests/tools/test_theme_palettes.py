"""Tests for rikugan.ui.theme palettes (DARK, LIGHT, IDA_NATIVE)."""

from __future__ import annotations

import re
import unittest
from dataclasses import asdict

from tests.qt_stubs import ensure_pyside6_stubs

ensure_pyside6_stubs()


class TestDarkPalette(unittest.TestCase):
    def test_dark_tokens_is_dark(self):
        """DARK_TOKENS.window must be a dark color (we use #1e1e1e)."""
        from rikugan.ui.theme.palette_dark import DARK_TOKENS
        self.assertEqual(DARK_TOKENS.window.lower(), "#1e1e1e")

    def test_dark_tokens_has_all_keys(self):
        """DARK_TOKENS must have all 17 required keys."""
        from rikugan.ui.theme.palette_dark import DARK_TOKENS
        self.assertEqual(len(asdict(DARK_TOKENS)), 17)

    def test_dark_tokens_hex_format(self):
        """All 17 values must be valid 6-char hex colors."""
        from rikugan.ui.theme.palette_dark import DARK_TOKENS
        pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for k, v in asdict(DARK_TOKENS).items():
            self.assertRegex(v, pattern, f"{k}={v}")

    def test_dark_text_contrast(self):
        """text color must have high luminance contrast against window."""
        from dataclasses import replace

        from rikugan.ui.theme.palette_dark import DARK_TOKENS
        from rikugan.ui.theme.tokens import is_dark_tokens
        self.assertTrue(is_dark_tokens(DARK_TOKENS))
        # text must NOT be dark (it should be the light foreground) —
        # verify by swapping window for the text color and checking
        # the swapped tokens are not dark.
        text_as_window = replace(DARK_TOKENS, window=DARK_TOKENS.text)
        self.assertFalse(is_dark_tokens(text_as_window))


class TestLightPalette(unittest.TestCase):
    def test_light_tokens_window_is_light(self):
        """LIGHT_TOKENS.window should have luminance > 0.5 (a light background)."""
        from rikugan.ui.theme.palette_light import LIGHT_TOKENS
        from rikugan.ui.theme.tokens import is_dark_tokens
        self.assertFalse(is_dark_tokens(LIGHT_TOKENS))

    def test_light_tokens_highlight_value(self):
        """Design lock: VS Code Light+ uses #0066cc for highlight."""
        from rikugan.ui.theme.palette_light import LIGHT_TOKENS
        self.assertEqual(LIGHT_TOKENS.highlight.lower(), "#0066cc")

    def test_light_tokens_has_all_keys(self):
        """LIGHT_TOKENS must have all 17 required keys."""
        from rikugan.ui.theme.palette_light import LIGHT_TOKENS
        self.assertEqual(len(asdict(LIGHT_TOKENS)), 17)

    def test_light_tokens_hex_format(self):
        """All 17 values must be valid 6-char hex colors."""
        from rikugan.ui.theme.palette_light import LIGHT_TOKENS
        pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for k, v in asdict(LIGHT_TOKENS).items():
            self.assertRegex(v, pattern, f"{k}={v}")

    def test_light_foreground_is_dark(self):
        """text must be a dark foreground color (high contrast against light window).

        Uses dataclasses.replace to swap window for text, then verifies
        the swapped value is dark. This is more readable than a 14-line
        inline ThemeTokens constructor and is 18-field-safe.
        """
        from dataclasses import replace

        from rikugan.ui.theme.palette_light import LIGHT_TOKENS
        from rikugan.ui.theme.tokens import is_dark_tokens
        text_as_window = replace(LIGHT_TOKENS, window=LIGHT_TOKENS.text)
        self.assertTrue(is_dark_tokens(text_as_window))


class _FakeApp:
    """Stand-in for QApplication that returns a fixed palette.

    Lives at module scope so the new TestIDAPaletteDerivation class can
    reach it without rebuilding for each test.
    """

    def __init__(self, pal) -> None:
        self._pal = pal

    def palette(self):
        return self._pal


class TestIDAPaletteDerivation(unittest.TestCase):
    """Tests for rikugan.ui.theme.palette_ida.derive_ida_tokens.

    The qt_stubs module-level injection replaces PySide6.QtGui.QPalette
    with a no-op class that does not preserve state set via setColor().
    These tests need the real PySide6 to exercise a live QPalette, so
    we force the real module back into sys.modules at class setup.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        # Drop the stub PySide6 modules installed by the module-level
        # ensure_pyside6_stubs() call so the real ones get re-imported.
        for name in list(sys.modules):
            if name.startswith("PySide6"):
                del sys.modules[name]
        from PySide6.QtGui import QColor, QPalette

        cls.QColor = QColor
        cls.QPalette = QPalette

    def test_derive_ida_tokens_dark(self):
        """Simulate IDA's dark palette and verify derivation."""
        from rikugan.ui.theme.palette_ida import derive_ida_tokens

        QColor = self.QColor
        QPalette = self.QPalette
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#252526"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#2d2d2d"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#d4d4d4"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#0e639c"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Mid, QColor("#3c3c3c"))
        pal.setColor(QPalette.ColorRole.Dark, QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Light, QColor("#5a5a5a"))

        tokens = derive_ida_tokens(source=_FakeApp(pal))
        self.assertEqual(len(asdict(tokens)), 17)
        self.assertEqual(tokens.window.lower(), "#1e1e1e")
        # Code text should match text in dark mode
        self.assertEqual(tokens.code_text.lower(), tokens.text.lower())

    def test_derive_ida_tokens_light(self):
        """Simulate IDA's light palette and verify derivation."""
        from rikugan.ui.theme.palette_ida import derive_ida_tokens

        QColor = self.QColor
        QPalette = self.QPalette
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#0066cc"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Mid, QColor("#cccccc"))
        pal.setColor(QPalette.ColorRole.Dark, QColor("#a0a0a0"))
        pal.setColor(QPalette.ColorRole.Light, QColor("#ffffff"))

        tokens = derive_ida_tokens(source=_FakeApp(pal))
        # Code bg should be alt_base
        self.assertEqual(tokens.code_bg.lower(), tokens.alt_base.lower())


if __name__ == "__main__":
    unittest.main()
