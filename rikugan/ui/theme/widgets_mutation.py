"""Mutation-log + tool-approval widget style dicts + getters.

Extracted verbatim from ``rikugan/ui/styles.py`` to shrink that
mega-module without touching any QSS byte. Each dict carries both its
``dark`` and ``light`` branches; getters select on the live theme flag
read lazily from ``styles`` to avoid an import cycle.
"""

from __future__ import annotations


def _branch() -> str:
    """Return ``'dark'`` or ``'light'`` for the active effective theme."""
    from ..styles import is_dark_theme  # lazy import to break the cycle

    return "dark" if is_dark_theme() else "light"


MUTATION_INDICATOR_STYLE = {
    "dark": {
        "reversible": "color: #4ec9b0; font-size: inherit;",
        "irreversible": "color: #808080; font-size: inherit;",
    },
    "light": {
        "reversible": "color: #218871; font-size: inherit;",
        "irreversible": "color: #92898a; font-size: inherit;",
    },
}

MUTATION_DESC_STYLE = {
    "dark": "color: #d4d4d4; font-size: inherit;",
    "light": "color: #2c232e; font-size: inherit;",
}

MUTATION_BADGE_STYLE = {
    "dark": "color: #808080; font-size: inherit; padding: 1px 4px; background: #2d2d2d; border-radius: 3px;",
    "light": "color: #92898a; font-size: inherit; padding: 1px 4px; background: #e8e0d8; border-radius: 3px;",
}

MUTATION_UNDO_BTN_STYLE = {
    "dark": (
        "QPushButton { color: #4ec9b0; background: #2d2d2d; "
        "border: 1px solid #4ec9b0; border-radius: 3px; "
        "padding: 3px 10px; font-size: inherit; }"
        "QPushButton:hover { background: #3d3d3d; }"
        "QPushButton:disabled { color: #555; border-color: #555; }"
    ),
    "light": (
        "QPushButton { color: #218871; background: #f8efe7; "
        "border: 1px solid #218871; border-radius: 3px; "
        "padding: 3px 10px; font-size: inherit; }"
        "QPushButton:hover { background: #e8e0d8; }"
        "QPushButton:disabled { color: #92898a; border-color: #92898a; }"
    ),
}

MUTATION_TITLE_STYLE = {
    "dark": "color: #d4d4d4; font-weight: bold; font-size: inherit;",
    "light": "color: #2c232e; font-weight: bold; font-size: inherit;",
}

MUTATION_COUNT_STYLE = {
    "dark": "color: #808080; font-size: inherit;",
    "light": "color: #92898a; font-size: inherit;",
}

# Tool approval widget styles
TOOL_APPROVAL_FRAME_STYLE = {
    "dark": "QFrame#message_question { border: 1px solid #dcdcaa; border-radius: 6px; background: #2d2d1e; }",
    "light": "QFrame#message_question { border: 1px solid #b16803; border-radius: 6px; background: #f0e8e0; }",
}

TOOL_APPROVAL_HEADER_STYLE = {
    "dark": "color: #dcdcaa; font-weight: bold; font-size: inherit;",
    "light": "color: #b16803; font-weight: bold; font-size: inherit;",
}

TOOL_APPROVAL_CODE_EDITOR_STYLE = {
    "dark": (
        "QPlainTextEdit { "
        "  color: #d4d4d4; background: #1e1e2e; "
        "  font-size: inherit; border: 1px solid #3c3c3c; border-radius: 4px; "
        "  padding: 4px; "
        "}"
        "QScrollBar:vertical { width: 8px; background: #1e1e2e; }"
        "QScrollBar::handle:vertical { background: #3c3c3c; border-radius: 4px; }"
        "QScrollBar:horizontal { height: 8px; background: #1e1e2e; }"
        "QScrollBar::handle:horizontal { background: #3c3c3c; border-radius: 4px; }"
    ),
    "light": (
        "QPlainTextEdit { "
        "  color: #2c232e; background: #f8efe7; "
        "  font-size: inherit; border: 1px solid #d2c9c4; border-radius: 4px; "
        "  padding: 4px; "
        "}"
        "QScrollBar:vertical { width: 8px; background: #f8efe7; }"
        "QScrollBar::handle:vertical { background: #d2c9c4; border-radius: 4px; }"
        "QScrollBar:horizontal { height: 8px; background: #f8efe7; }"
        "QScrollBar::handle:horizontal { background: #d2c9c4; border-radius: 4px; }"
    ),
}

TOOL_APPROVAL_ALLOW_BTN_STYLE = {
    "dark": (
        "QToolButton { background: #2ea043; color: #ffffff; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; font-weight: bold; }"
        "QToolButton:hover { background: #3fb950; }"
    ),
    "light": (
        "QToolButton { background: #218871; color: #ffffff; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; font-weight: bold; }"
        "QToolButton:hover { background: #2ea58a; }"
    ),
}

TOOL_APPROVAL_ALWAYS_BTN_STYLE = {
    "dark": (
        "QToolButton { background: #1a5c2d; color: #ffffff; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; font-weight: bold; }"
        "QToolButton:hover { background: #2ea043; }"
    ),
    "light": (
        "QToolButton { background: #1a5c2d; color: #ffffff; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; font-weight: bold; }"
        "QToolButton:hover { background: #218871; }"
    ),
}

TOOL_APPROVAL_DENY_BTN_STYLE = {
    "dark": (
        "QToolButton { background: #c42b1c; color: #ffffff; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; font-weight: bold; }"
        "QToolButton:hover { background: #e04030; }"
    ),
    "light": (
        "QToolButton { background: #c0392b; color: #ffffff; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; font-weight: bold; }"
        "QToolButton:hover { background: #d64a3a; }"
    ),
}

TOOL_APPROVAL_DISABLED_BTN_STYLE = {
    "dark": (
        "QToolButton { background: #1a5c2d; color: #808080; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; }"
    ),
    "light": (
        "QToolButton { background: #1a5c2d; color: #92898a; border: none; "
        "border-radius: 4px; padding: 4px 16px; font-size: inherit; }"
    ),
}


def get_mutation_indicator_style(reversible: bool) -> str:
    """Mutation indicator style for the current theme + reversibility."""
    theme = _branch()
    key = "reversible" if reversible else "irreversible"
    return MUTATION_INDICATOR_STYLE[theme][key]


def get_mutation_desc_style() -> str:
    return MUTATION_DESC_STYLE[_branch()]


def get_mutation_badge_style() -> str:
    return MUTATION_BADGE_STYLE[_branch()]


def get_mutation_undo_btn_style() -> str:
    return MUTATION_UNDO_BTN_STYLE[_branch()]


def get_mutation_title_style() -> str:
    return MUTATION_TITLE_STYLE[_branch()]


def get_mutation_count_style() -> str:
    return MUTATION_COUNT_STYLE[_branch()]


def get_tool_approval_frame_style() -> str:
    return TOOL_APPROVAL_FRAME_STYLE[_branch()]


def get_tool_approval_header_style() -> str:
    return TOOL_APPROVAL_HEADER_STYLE[_branch()]


def get_tool_approval_code_editor_style() -> str:
    return TOOL_APPROVAL_CODE_EDITOR_STYLE[_branch()]


def get_tool_approval_allow_btn_style() -> str:
    return TOOL_APPROVAL_ALLOW_BTN_STYLE[_branch()]


def get_tool_approval_always_btn_style() -> str:
    return TOOL_APPROVAL_ALWAYS_BTN_STYLE[_branch()]


def get_tool_approval_deny_btn_style() -> str:
    return TOOL_APPROVAL_DENY_BTN_STYLE[_branch()]


def get_tool_approval_disabled_btn_style() -> str:
    return TOOL_APPROVAL_DISABLED_BTN_STYLE[_branch()]
