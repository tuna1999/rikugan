"""Agent-tree widget style dicts + getters.

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


# Agent tree styles
AGENT_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 4px; padding: 4px 10px; font-size: inherit; }"
        "QPushButton:hover { background: #3c3c3c; }"
        "QPushButton:disabled { color: #555; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 4px; padding: 4px 10px; font-size: inherit; }"
        "QPushButton:hover { background: #e8e0d8; }"
        "QPushButton:disabled { color: #92898a; }"
    ),
}

AGENT_TREE_STYLE = {
    "dark": """
        QTreeWidget {
            background: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            font-size: inherit;
            alternate-background-color: #252525;
        }
        QTreeWidget::item {
            padding: 2px 4px;
        }
        QTreeWidget::item:selected {
            background: #264f78;
            color: #ffffff;
        }
        QTreeWidget::item:hover {
            background: #2a2d2e;
        }
        QHeaderView::section {
            background: #2d2d2d;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            padding: 3px 6px;
            font-size: inherit;
        }
    """,
    "light": """
        QTreeWidget {
            background: #f8efe7;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            font-size: inherit;
            alternate-background-color: #f0e8e0;
        }
        QTreeWidget::item {
            padding: 2px 4px;
        }
        QTreeWidget::item:selected {
            background: #d7ba7d;
            color: #2c232e;
        }
        QTreeWidget::item:hover {
            background: #e8e0d8;
        }
        QHeaderView::section {
            background: #e8e0d8;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            padding: 3px 6px;
            font-size: inherit;
        }
    """,
}

AGENT_COMBO_STYLE = {
    "dark": (
        "QComboBox { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 4px; padding: 3px 6px; font-size: inherit; }"
    ),
    "light": (
        "QComboBox { background: #f8efe7; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 4px; padding: 3px 6px; font-size: inherit; }"
    ),
}

AGENT_STATUS_LABEL_STYLE = {
    "dark": "color: #808080; font-size: inherit;",
    "light": "color: #92898a; font-size: inherit;",
}

AGENT_PREVIEW_STYLE = {
    "dark": (
        "QTextEdit { background: #252525; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "font-size: inherit; padding: 4px; }"
    ),
    "light": (
        "QTextEdit { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "font-size: inherit; padding: 4px; }"
    ),
}

# Agent status colors
AGENT_STATUS_COLORS = {
    "dark": {
        "PENDING": "#808080",
        "RUNNING": "#dcdcaa",
        "COMPLETED": "#4ec9b0",
        "FAILED": "#f44747",
        "CANCELLED": "#808080",
    },
    "light": {
        "PENDING": "#92898a",
        "RUNNING": "#b16803",
        "COMPLETED": "#218871",
        "FAILED": "#ce4770",
        "CANCELLED": "#92898a",
    },
}

# Orchestra panel styles


def get_agent_btn_style() -> str:
    return AGENT_BTN_STYLE[_branch()]


def get_agent_tree_style() -> str:
    return AGENT_TREE_STYLE[_branch()]


def get_agent_combo_style() -> str:
    return AGENT_COMBO_STYLE[_branch()]


def get_agent_status_label_style() -> str:
    return AGENT_STATUS_LABEL_STYLE[_branch()]


def get_agent_preview_style() -> str:
    return AGENT_PREVIEW_STYLE[_branch()]


def get_agent_status_colors() -> dict[str, str]:
    return AGENT_STATUS_COLORS[_branch()]
