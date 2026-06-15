"""Bulk-renamer widget style dicts + getters.

Extracted verbatim from ``rikugan/ui/styles.py`` (lines 1495-1676 +
2346-2395) to shrink that mega-module without touching any QSS byte.
Each dict carries both its ``dark`` and ``light`` branches, so the
getters select on the live theme flag read lazily from ``styles`` to
avoid an import cycle (``styles`` re-exports these getters).
"""

from __future__ import annotations


def _branch() -> str:
    """Return ``'dark'`` or ``'light'`` for the active effective theme.

    Reads the live flag lazily from :mod:`rikugan.ui.styles` so a theme
    switch at runtime is reflected without a module-level import cycle.
    """
    from ..styles import is_dark_theme  # lazy import to break the cycle

    return "dark" if is_dark_theme() else "light"


BULK_BTN_STYLE = {
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

BULK_STOP_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #c42b1c; border: 1px solid #c42b1c; "
        "border-radius: 4px; padding: 4px 10px; font-size: inherit; font-weight: bold; }"
        "QPushButton:hover { background: #3c3c3c; }"
        "QPushButton:disabled { color: #555; border-color: #555; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #c0392b; border: 1px solid #c0392b; "
        "border-radius: 4px; padding: 4px 10px; font-size: inherit; font-weight: bold; }"
        "QPushButton:hover { background: #e8e0d8; }"
        "QPushButton:disabled { color: #92898a; border-color: #92898a; }"
    ),
}

BULK_START_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #d4d4d4; "
        "border-radius: 4px; padding: 4px 14px; font-size: inherit; font-weight: bold; }"
        "QPushButton:hover { background: #3c3c3c; }"
        "QPushButton:disabled { color: #555; border-color: #555; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #72696d; "
        "border-radius: 4px; padding: 4px 14px; font-size: inherit; font-weight: bold; }"
        "QPushButton:hover { background: #e8e0d8; }"
        "QPushButton:disabled { color: #92898a; border-color: #92898a; }"
    ),
}

BULK_TABLE_STYLE = {
    "dark": """
        QTableWidget {
            background: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            gridline-color: #3c3c3c;
            font-size: inherit;
            alternate-background-color: #252525;
        }
        QTableWidget::item {
            padding: 2px 4px;
        }
        QTableWidget::item:selected {
            background: #2d2d2d;
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
        QTableWidget {
            background: #f8efe7;
            color: #2c232e;
            border: 1px solid #d2c9c4;
            gridline-color: #d2c9c4;
            font-size: inherit;
            alternate-background-color: #f0e8e0;
        }
        QTableWidget::item {
            padding: 2px 4px;
        }
        QTableWidget::item:selected {
            background: #d7ba7d;
            color: #2c232e;
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

BULK_FILTER_STYLE = {
    "dark": (
        "QLineEdit { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 3px; padding: 3px 6px; font-size: inherit; }"
        "QLineEdit:focus { border-color: #4ec9b0; }"
    ),
    "light": (
        "QLineEdit { background: #f8efe7; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 3px; padding: 3px 6px; font-size: inherit; }"
        "QLineEdit:focus { border-color: #218871; }"
    ),
}

BULK_COMBO_STYLE = {
    "dark": (
        "QComboBox { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 3px; padding: 3px 6px; font-size: inherit; }"
    ),
    "light": (
        "QComboBox { background: #f8efe7; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 3px; padding: 3px 6px; font-size: inherit; }"
    ),
}

BULK_NUM_INPUT_STYLE = {
    "dark": (
        "QLineEdit { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 3px; padding: 2px 4px; font-size: inherit; }"
    ),
    "light": (
        "QLineEdit { background: #f8efe7; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 3px; padding: 2px 4px; font-size: inherit; }"
    ),
}

BULK_PROGRESS_STYLE = {
    "dark": (
        "QProgressBar { background: #2d2d2d; border: 1px solid #3c3c3c; "
        "border-radius: 3px; text-align: center; color: #d4d4d4; font-size: inherit; }"
        "QProgressBar::chunk { background: #808080; border-radius: 2px; }"
    ),
    "light": (
        "QProgressBar { background: #e8e0d8; border: 1px solid #d2c9c4; "
        "border-radius: 3px; text-align: center; color: #2c232e; font-size: inherit; }"
        "QProgressBar::chunk { background: #218871; border-radius: 2px; }"
    ),
}

BULK_RADIO_STYLE = {
    "dark": "QRadioButton { color: #d4d4d4; font-size: inherit; spacing: 4px; }",
    "light": "QRadioButton { color: #2c232e; font-size: inherit; spacing: 4px; }",
}

BULK_CHECK_STYLE = {
    "dark": "QCheckBox { spacing: 0px; } QCheckBox::indicator { width: 14px; height: 14px; }",
    "light": "QCheckBox { spacing: 0px; } QCheckBox::indicator { width: 14px; height: 14px; }",
}

BULK_SELECTION_LABEL_STYLE = {
    "dark": "color: #808080; font-size: inherit;",
    "light": "color: #92898a; font-size: inherit;",
}

BULK_MODE_LABEL_STYLE = {
    "dark": "color: #d4d4d4; font-size: inherit;",
    "light": "color: #2c232e; font-size: inherit;",
}

# Bulk renamer status colors
BULK_STATUS_COLORS = {
    "dark": {
        "queued": "#808080",
        "analyzing": "#dcdcaa",
        "renamed": "#4ec9b0",
        "reverted": "#569cd6",
        "skipped": "#d7ba7d",
        "error": "#f44747",
    },
    "light": {
        "queued": "#92898a",
        "analyzing": "#b16803",
        "renamed": "#218871",
        "reverted": "#2473b6",
        "skipped": "#d7ba7d",
        "error": "#ce4770",
    },
}


def get_bulk_btn_style() -> str:
    return BULK_BTN_STYLE[_branch()]


def get_bulk_stop_btn_style() -> str:
    return BULK_STOP_BTN_STYLE[_branch()]


def get_bulk_start_btn_style() -> str:
    return BULK_START_BTN_STYLE[_branch()]


def get_bulk_table_style() -> str:
    return BULK_TABLE_STYLE[_branch()]


def get_bulk_filter_style() -> str:
    return BULK_FILTER_STYLE[_branch()]


def get_bulk_combo_style() -> str:
    return BULK_COMBO_STYLE[_branch()]


def get_bulk_num_input_style() -> str:
    return BULK_NUM_INPUT_STYLE[_branch()]


def get_bulk_progress_style() -> str:
    return BULK_PROGRESS_STYLE[_branch()]


def get_bulk_radio_style() -> str:
    return BULK_RADIO_STYLE[_branch()]


def get_bulk_check_style() -> str:
    return BULK_CHECK_STYLE[_branch()]


def get_bulk_selection_label_style() -> str:
    return BULK_SELECTION_LABEL_STYLE[_branch()]


def get_bulk_mode_label_style() -> str:
    return BULK_MODE_LABEL_STYLE[_branch()]


def get_bulk_status_colors() -> dict[str, str]:
    return BULK_STATUS_COLORS[_branch()]
