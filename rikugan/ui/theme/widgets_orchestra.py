"""Orchestra / delegation / profiles widget style dicts + getters.

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


ORCHESTRA_PANEL_STYLE = {
    "dark": """
        QWidget#orchestra_panel {
            background: #1e1e1e;
        }
        QLabel {
            color: #d4d4d4;
        }
        QLabel.header {
            font-size: inherit;
            font-weight: bold;
            color: #4ec9b0;
        }
        QTreeWidget {
            background: #1e1e2e;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            font-size: inherit;
        }
        QTreeWidget::item {
            padding: 3px;
        }
        QTreeWidget::item:selected {
            background: #2d4a4a;
        }
        QHeaderView::section {
            background: #2d2d2d;
            color: #808080;
            border: none;
            border-right: 1px solid #3c3c3c;
            border-bottom: 1px solid #3c3c3c;
            padding: 4px;
            font-size: inherit;
            font-weight: bold;
        }
        QPushButton {
            background: #2d2d2d;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            padding: 4px 12px;
            font-size: inherit;
        }
        QPushButton:hover {
            background: #3c3c3c;
        }
        QPushButton:disabled {
            background: #252525;
            color: #555555;
        }
    """,
    "light": """
        QWidget#orchestra_panel {
            background: #f8efe7;
        }
        QLabel {
            color: #2c232e;
        }
        QLabel.header {
            font-size: inherit;
            font-weight: bold;
            color: #218871;
        }
        QTreeWidget {
            background: #f8efe7;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            border-radius: 4px;
            font-size: inherit;
        }
        QTreeWidget::item {
            padding: 3px;
        }
        QTreeWidget::item:selected {
            background: #d7ba7d;
            color: #2c232e;
        }
        QHeaderView::section {
            background: #e8e0d8;
            color: #72696d;
            border: none;
            border-right: 1px solid #d2c9c4;
            border-bottom: 1px solid #d2c9c4;
            padding: 4px;
            font-size: inherit;
            font-weight: bold;
        }
        QPushButton {
            background: #f0e8e0;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            border-radius: 4px;
            padding: 4px 12px;
            font-size: inherit;
        }
        QPushButton:hover {
            background: #e8e0d8;
        }
        QPushButton:disabled {
            background: #f0e8e0;
            color: #92898a;
        }
    """,
}

ORCHESTRA_STATS_STYLE = {
    "dark": "color: #808080; font-size: inherit;",
    "light": "color: #92898a; font-size: inherit;",
}

# Orchestra approval dialog styles
DELEGATION_DIALOG_STYLE = {
    "dark": """
        QDialog {
            background: #1e1e1e;
            color: #d4d4d4;
        }
        QLabel {
            color: #d4d4d4;
        }
        QLabel.header {
            font-size: inherit;
            font-weight: bold;
            color: #4ec9b0;
        }
        QLabel.section {
            font-size: inherit;
            font-weight: bold;
            color: #808080;
            margin-top: 8px;
        }
        QTextEdit, QScrollArea {
            background: #1e1e2e;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            font-size: inherit;
        }
        QScrollArea {
            border: none;
        }
        QTextEdit:read-only {
            background: #252536;
        }
        QDialogButtonBox {
            button-layout: 0;
        }
        QPushButton {
            background: #2d2d2d;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            padding: 6px 16px;
            font-size: inherit;
        }
        QPushButton:hover {
            background: #3c3c3c;
        }
        QPushButton#approve_btn {
            background: #2ea043;
            color: white;
            border-color: #2ea043;
        }
        QPushButton#approve_btn:hover {
            background: #3fb950;
        }
        QPushButton#deny_btn {
            background: #c42b1c;
            color: white;
            border-color: #c42b1c;
        }
        QPushButton#deny_btn:hover {
            background: #e83a2a;
        }
    """,
    "light": """
        QDialog {
            background: #f8efe7;
            color: #2c232e;
        }
        QLabel {
            color: #2c232e;
        }
        QLabel.header {
            font-size: inherit;
            font-weight: bold;
            color: #218871;
        }
        QLabel.section {
            font-size: inherit;
            font-weight: bold;
            color: #92898a;
            margin-top: 8px;
        }
        QTextEdit, QScrollArea {
            background: #f8efe7;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            border-radius: 4px;
            font-size: inherit;
        }
        QScrollArea {
            border: none;
        }
        QTextEdit:read-only {
            background: #f0e8e0;
        }
        QDialogButtonBox {
            button-layout: 0;
        }
        QPushButton {
            background: #f0e8e0;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            border-radius: 4px;
            padding: 6px 16px;
            font-size: inherit;
        }
        QPushButton:hover {
            background: #e8e0d8;
        }
        QPushButton#approve_btn {
            background: #218871;
            color: white;
            border-color: #218871;
        }
        QPushButton#approve_btn:hover {
            background: #2ea58a;
        }
        QPushButton#deny_btn {
            background: #c0392b;
            color: white;
            border-color: #c0392b;
        }
        QPushButton#deny_btn:hover {
            background: #d64a3a;
        }
    """,
}

DELEGATION_APPROVAL_WIDGET_STYLE = {
    "dark": ("QFrame#delegation_approval { border: 1px solid #4ec9b0; border-radius: 6px; background: #1e2e2e; }"),
    "light": ("QFrame#delegation_approval { border: 1px solid #218871; border-radius: 6px; background: #f0f5f3; }"),
}

DELEGATION_HEADER_STYLE = {
    "dark": "color: #4ec9b0; font-weight: bold; font-size: inherit;",
    "light": "color: #218871; font-weight: bold; font-size: inherit;",
}

DELEGATION_INFO_STYLE = {
    "dark": "color: #808080; font-size: inherit;",
    "light": "color: #92898a; font-size: inherit;",
}

DELEGATION_PREVIEW_STYLE = {
    "dark": "color: #d4d4d4; font-size: inherit;",
    "light": "color: #2c232e; font-size: inherit;",
}

# Profiles tab styles
PROFILES_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 4px; padding: 4px 12px; }"
        "QPushButton:hover { background: #3c3c3c; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 4px; padding: 4px 12px; }"
        "QPushButton:hover { background: #e8e0d8; }"
    ),
}

PROFILES_GROUP_STYLE = {
    "dark": (
        "QGroupBox { font-weight: bold; border: 1px solid #3c3c3c; "
        "border-radius: 4px; margin-top: 14px; padding-top: 4px; }"
        "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
        "padding: 0 6px; }"
    ),
    "light": (
        "QGroupBox { font-weight: bold; border: 1px solid #d2c9c4; "
        "border-radius: 4px; margin-top: 14px; padding-top: 4px; }"
        "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
        "padding: 0 6px; }"
    ),
}

PROFILES_HEADER_STYLE = {
    "dark": "color: #888; margin-top: 6px;",
    "light": "color: #72696d; margin-top: 6px;",
}


def get_orchestra_panel_style() -> str:
    return ORCHESTRA_PANEL_STYLE[_branch()]


def get_orchestra_stats_style() -> str:
    return ORCHESTRA_STATS_STYLE[_branch()]


def get_delegation_dialog_style() -> str:
    return DELEGATION_DIALOG_STYLE[_branch()]


def get_delegation_approval_widget_style() -> str:
    return DELEGATION_APPROVAL_WIDGET_STYLE[_branch()]


def get_delegation_header_style() -> str:
    return DELEGATION_HEADER_STYLE[_branch()]


def get_delegation_info_style() -> str:
    return DELEGATION_INFO_STYLE[_branch()]


def get_delegation_preview_style() -> str:
    return DELEGATION_PREVIEW_STYLE[_branch()]


def get_profiles_btn_style() -> str:
    return PROFILES_BTN_STYLE[_branch()]


def get_profiles_group_style() -> str:
    return PROFILES_GROUP_STYLE[_branch()]


def get_profiles_header_style() -> str:
    return PROFILES_HEADER_STYLE[_branch()]
