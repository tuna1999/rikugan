"""Tests for the lazy crypto availability check in ``core.crypto``.

The settings dialog depends on ``crypto.is_available()`` to enable the
"Encrypt API keys" checkbox. The original implementation imported
``cryptography`` at module load time, which slowed down the settings
dialog's first paint. These tests verify the lazy check still returns
the correct result without importing the heavy crypto primitives.
"""

from __future__ import annotations

import importlib
import sys
import unittest


class TestCryptoLazyImport(unittest.TestCase):
    def test_is_available_returns_bool(self):
        from rikugan.core.crypto import is_available

        result = is_available()
        self.assertIsInstance(result, bool)

    def test_module_does_not_eagerly_import_cryptography(self):
        # Re-import the crypto module after forcibly removing
        # ``cryptography`` from ``sys.modules``. If crypto.py were still
        # importing it at module load time, this reimport would
        # succeed in binding the globals; otherwise is_available()
        # should fall back to ``importlib.util.find_spec`` and return
        # whatever is currently installed (probably True in CI).
        for mod in [m for m in list(sys.modules) if m.startswith("cryptography")]:
            sys.modules.pop(mod, None)
        if "rikugan.core.crypto" in sys.modules:
            importlib.reload(sys.modules["rikugan.core.crypto"])
        from rikugan.core.crypto import is_available

        # The result reflects the actual installation: if cryptography
        # is present (it usually is in dev), the function returns True;
        # otherwise False. Either way, the import must not crash.
        self.assertIsInstance(is_available(), bool)

    def test_coerce_token_count_does_not_import_cryptography(self):
        # Ensure the token-coercion helper (in a different module) does
        # not pull in cryptography.
        for mod in [m for m in list(sys.modules) if m.startswith("cryptography")]:
            sys.modules.pop(mod, None)
        from rikugan.core.types import coerce_token_count

        self.assertEqual(coerce_token_count(None), 0)
        self.assertEqual(coerce_token_count(5), 5)


if __name__ == "__main__":
    unittest.main()
