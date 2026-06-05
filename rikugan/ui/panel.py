"""Backward-compatible panel import path."""

from __future__ import annotations

from ..core.host import is_ida

if is_ida():
    from ..ida.ui.panel import RikuganPanel
else:
    from .panel_core import RikuganPanelCore as RikuganPanel  # type: ignore[assignment]  # noqa: F401
