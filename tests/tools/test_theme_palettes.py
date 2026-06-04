"""Tests for rikugan.ui.theme palettes (DARK, LIGHT, IDA_NATIVE)."""

from __future__ import annotations

import re
import unittest
from dataclasses import asdict

from tests.qt_stubs import ensure_pyside6_stubs
ensure_pyside6_stubs()

from rikugan.ui.theme.tokens import ThemeTokens


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
        from rikugan.ui.theme.palette_dark import DARK_TOKENS
        from rikugan.ui.theme.tokens import is_dark_tokens
        # is_dark_tokens confirms window is dark; contrast is between
        # text (light) and window (dark)
        self.assertTrue(is_dark_tokens(DARK_TOKENS))
        # text must NOT be dark (it should be the light foreground) —
        # verify by using the text color as a hypothetical window.
        self.assertFalse(is_dark_tokens(
            ThemeTokens(
                window=DARK_TOKENS.text,
                window_text=DARK_TOKENS.text,
                base=DARK_TOKENS.base, alt_base=DARK_TOKENS.alt_base,
                text=DARK_TOKENS.text,
                button=DARK_TOKENS.button, button_text=DARK_TOKENS.button_text,
                highlight=DARK_TOKENS.highlight,
                highlight_text=DARK_TOKENS.highlight_text,
                mid=DARK_TOKENS.mid, light=DARK_TOKENS.light,
                dark=DARK_TOKENS.dark,
                success=DARK_TOKENS.success, warning=DARK_TOKENS.warning,
                error=DARK_TOKENS.error, code_text=DARK_TOKENS.code_text,
                code_bg=DARK_TOKENS.code_bg,
            )
        ))


if __name__ == "__main__":
    unittest.main()
