"""Tests that the IDA panel wrapper re-applies minimal_style on theme change.

Regression: the host-scoped minimal_style QSS was built once at construction
and never re-applied when the user switched theme mid-session, so message/
input/button objects kept the old palette. The panel now subscribes to
ThemeManager.themeChanged and rebuilds the QSS on every emit.
"""

from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tests.mocks.ida_mock import install_ida_mocks

install_ida_mocks()

from tests.qt_stubs import _qt_class, ensure_pyside6_stubs  # noqa: E402

ensure_pyside6_stubs()

# Stub rikugan.ui.panel_core so importing the IDA panel wrapper succeeds
# without pulling in the full panel_core Qt surface.
_panel_core_mod = types.ModuleType("rikugan.ui.panel_core")
_panel_core_mod.RikuganPanelCore = _qt_class("RikuganPanelCore")
sys.modules.setdefault("rikugan.ui.panel_core", _panel_core_mod)

_session_mod = types.ModuleType("rikugan.ida.ui.session_controller")
_session_mod.IdaSessionController = MagicMock()
_session_mod.SessionController = _session_mod.IdaSessionController
sys.modules["rikugan.ida.ui.session_controller"] = _session_mod

_actions_mod = types.ModuleType("rikugan.ida.ui.actions")
_actions_mod.RikuganUIHooks = MagicMock()
sys.modules["rikugan.ida.ui.actions"] = _actions_mod

from rikugan.ida.ui.panel import RikuganPanel  # noqa: E402
from rikugan.ui.theme.manager import ThemeManager  # noqa: E402


def _make_panel() -> RikuganPanel:
    """Create a RikuganPanel bypassing __init__, injecting a mock _core.

    Mirrors the helper in tests/tools/test_ida_panel.py so the subscription
    test does not have to run the full IDA __init__ (which spins up the
    PluginForm, watcher, etc.).
    """
    panel = object.__new__(RikuganPanel)
    panel._form_widget = None
    panel._root = None
    panel._core = MagicMock()
    panel._theme_watcher = None
    return panel


class TestSubscribeThemeChanges(unittest.TestCase):
    """The panel must connect _reapply_minimal_style to themeChanged."""

    def setUp(self):
        ThemeManager.reset()

    def tearDown(self):
        ThemeManager.reset()

    def test_subscribe_connects_reapply_slot(self):
        panel = _make_panel()
        manager = ThemeManager.instance()
        signal = manager.themeChanged

        panel._subscribe_theme_changes()

        # The slot connected is the adapter _on_theme_changed (it accepts the
        # tokens arg themeChanged emits, then calls _reapply_minimal_style).
        self.assertIn(panel._on_theme_changed, signal._connections)

    def test_theme_changed_emit_calls_reapply(self):
        panel = _make_panel()
        panel._reapply_minimal_style = MagicMock()
        manager = ThemeManager.instance()

        panel._subscribe_theme_changes()
        # Simulate ThemeManager emitting a theme change (carries tokens).
        manager.themeChanged.emit(object())

        panel._reapply_minimal_style.assert_called_once()

    def test_unsubscribe_removes_slot(self):
        panel = _make_panel()
        manager = ThemeManager.instance()

        panel._subscribe_theme_changes()
        self.assertIn(panel._on_theme_changed, manager.themeChanged._connections)

        panel._unsubscribe_theme_changes()
        self.assertNotIn(panel._on_theme_changed, manager.themeChanged._connections)


if __name__ == "__main__":
    unittest.main()
