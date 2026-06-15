"""Light and Dark theme stylesheets for Rikugan UI.

Light theme based on Monokai Pro Light (Filter Sun) color palette.
Dark theme based on VS Code Dark+.
"""

from __future__ import annotations

_current_theme: str = "light"
# ``_effective_theme`` is the helper palette ('dark' or 'light') that
# inline-styled widgets should look up. For 'ida' the effective theme is
# supplied by the caller (panel core / IDA wrapper) based on the host's
# detected color brightness.
_effective_theme: str = "light"


def set_current_theme(theme: str, effective_theme: str | None = None) -> None:
    """Set the current theme for theme-aware style getters.

    Args:
        theme: The user-configured theme name (``"light"``, ``"dark"``,
            ``"ida"``). ``"ida"`` is treated as "inherit the host".
        effective_theme: Optional helper palette to use when *theme* is
            ``"ida"`` (or any non-``"dark"``/``"light"`` value). Must be
            ``"dark"`` or ``"light"``. When omitted, the previous
            effective theme is preserved (defaulting to ``"light"`` for
            the very first call).
    """
    global _current_theme, _effective_theme
    _current_theme = theme
    if effective_theme in ("dark", "light"):
        _effective_theme = effective_theme
    elif theme in ("dark", "light"):
        _effective_theme = theme
    # If theme is 'ida' and no effective theme was supplied, leave the
    # previous effective theme alone (defaults to "light").


def is_dark_theme() -> bool:
    """Check whether inline-styled widgets should use the dark palette."""
    return _effective_theme == "dark"


def get_current_theme() -> str:
    """Return the user-configured theme name (``"light"``/``"dark"``/``"ida"``).

    ``"ida"`` means "inherit the host's Qt theme".  Use :func:`is_host_theme`
    for a boolean check.
    """
    return _current_theme


def is_host_theme() -> bool:
    """True when the configured theme is ``"ida"`` (inherit the host palette).

    In host-theme mode, Rikugan does not apply its own LIGHT_THEME / DARK_THEME
    global stylesheet.  Inline-styled widgets that have a per-widget
    stylesheet (e.g. the paginated history nav strip) should clear that
    inline stylesheet so the host's Qt stylesheet — or the host-aware
    minimal stylesheet added by the IDA panel wrapper — can take over.

    ``"auto"`` is treated as host-theme for the purposes of the legacy
    helper: the effective palette is decided by the live QApplication,
    and the legacy selectors do not have a separate "auto" branch.
    """
    return _current_theme in ("ida", "auto")


# =============================================================================
# LIGHT THEME - Monokai Pro Light (Filter Sun) inspired
# =============================================================================
LIGHT_THEME = """
QWidget#rikugan_panel {
    background-color: #f8efe7;
    color: #2c232e;
}

QScrollArea#chat_scroll {
    background-color: #f8efe7;
    border: none;
}

QWidget#chat_container {
    background-color: #f8efe7;
}

QFrame#message_user {
    background-color: #f0e8e0;
    border-radius: 8px;
    padding: 8px;
    margin: 4px 8px 4px 8px;
}

QFrame#message_assistant {
    background-color: #f8efe7;
    border-radius: 8px;
    padding: 8px;
    margin: 4px 8px 4px 8px;
}

QFrame#message_tool {
    background-color: #e8e0d8;
    border: 1px solid #d2c9c4;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#message_thinking {
    background-color: #f8efe7;
    border-radius: 6px;
    padding: 4px 8px;
    margin: 2px 8px;
}




QLabel#msg_role_label {
    color: #218871;
    font-weight: bold;
    font-size: inherit;
}

QLabel#tool_header {
    color: #2473b6;
    font-weight: bold;
    font-size: inherit;
}

QLabel#tool_content {
    color: #6851a2;
    font-size: inherit;
}

QLabel#collapse_button {
    border: none;
    color: #92898a;
    font-size: inherit;
}










QLabel#cat_label {
    font-weight: bold;
    font-size: inherit;
}



QLabel#note_title {
    font-weight: bold;
    font-size: inherit;
}

QLabel#note_genre {
    color: #92898a;
    font-size: inherit;
    font-style: italic;
}



QLabel#subagent_icon {
    font-size: inherit;
}

QLabel#subagent_label {
    font-weight: bold;
    font-size: inherit;
}




QLabel#msg_content {
    color: inherit;
}

QLabel#relevance_star {
    color: #d7ba7d;
    font-size: inherit;
}

QFrame#finding_tool {
    border: 1px solid;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#note_tool {
    border: 1px solid;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#subagent_tool {
    border: 1px solid;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#skill_popup {
    background: #f0e8e0;
    border: 1px solid #d2c9c4;
    border-radius: 4px;
    padding: 2px;
}

QFrame#skill_popup QLabel {
    color: #2c232e;
    padding: 3px 8px;
}

QFrame#skill_popup QLabel[selected="true"] {
    background: rgba(177, 104, 3, 0.20);
    border-radius: 3px;
}

QPushButton#option_btn {
    background: #2473b6;
    color: white;
    border: 1px solid #1a5a93;
    border-radius: 4px;
    padding: 4px 14px;
    font-size: inherit;
}

QPushButton#option_btn:hover {
    background: #3d8cd9;
}

QPushButton#option_btn:pressed {
    background: #1a5a93;
}

QPushButton#option_btn:disabled {
    color: #a59c9c;
    background: #e8e0d8;
    border-color: #d2c9c4;
}

QPlainTextEdit#input_area {
    background-color: #f8efe7;
    color: #2c232e;
    border: 1px solid #d2c9c4;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #b16803;
}

QPlainTextEdit#input_area:focus {
    border-color: #2473b6;
}

QPushButton#send_button {
    background-color: #2473b6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}

QPushButton#send_button:hover {
    background-color: #3d8cd9;
}

QPushButton#send_button:pressed {
    background-color: #1a5a93;
}

QPushButton#send_button:disabled {
    background-color: #e8e0d8;
    color: #92898a;
}

QPushButton#cancel_button {
    background-color: #c0392b;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}

QFrame#context_bar {
    background-color: #e8e0d8;
    border-top: 1px solid #d2c9c4;
    padding: 4px 8px;
}

QLabel#context_label {
    color: #92898a;
    font-size: inherit;
}

QLabel#context_value {
    color: #2c232e;
    font-size: inherit;
}

QFrame#plan_step {
    background-color: #f0e8e0;
    border: 1px solid #d2c9c4;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}

QFrame#plan_step_active {
    background-color: #f0e8e0;
    border: 1px solid #2473b6;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}

QFrame#plan_step_done {
    background-color: #f0e8e0;
    border: 1px solid #218871;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}

QToolButton#collapse_button {
    border: none;
    color: #92898a;
    font-size: inherit;
}

QToolButton#collapse_button:hover {
    color: #2c232e;
}

QFrame#tools_panel {
    background-color: #f8efe7;
    border-left: 1px solid #d2c9c4;
}

QFrame#tools_panel QTabWidget::pane {
    border: none;
}

QFrame#tools_panel QTabBar {
    background: #f8efe7;
    border: none;
}

QFrame#tools_panel QTabBar::tab {
    background: #f0e8e0;
    color: #72696d;
    padding: 4px 12px;
    border: none;
    border-right: 1px solid #d2c9c4;
    font-size: inherit;
}

QFrame#tools_panel QTabBar::tab:selected {
    background: #f8efe7;
    color: #2c232e;
    border-bottom: 2px solid #218871;
}

QFrame#tools_panel QTabBar::tab:hover {
    background: #e8e0d8;
}

QTreeWidget {
    background-color: #f8efe7;
    color: #2c232e;
    border: none;
    font-size: inherit;
}

QTreeWidget::item {
    padding: 2px 4px;
}

QTreeWidget::item:selected {
    background-color: #d7ba7d;
    color: #2c232e;
}

QTreeWidget::item:hover {
    background-color: #f0e8e0;
}

QHeaderView::section {
    background-color: #e8e0d8;
    color: #2c232e;
    border: none;
    border-right: 1px solid #d2c9c4;
    padding: 3px 6px;
    font-size: inherit;
}

QTableWidget {
    background-color: #f8efe7;
    color: #2c232e;
    border: none;
    gridline-color: #d2c9c4;
    font-size: inherit;
}

QTableWidget::item {
    padding: 2px 4px;
}

QTableWidget::item:selected {
    background-color: #d7ba7d;
    color: #2c232e;
}

QProgressBar {
    background-color: #e8e0d8;
    border: 1px solid #d2c9c4;
    border-radius: 3px;
    text-align: center;
    color: #2c232e;
    font-size: inherit;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #218871;
    border-radius: 2px;
}

QRadioButton {
    color: #2c232e;
    font-size: inherit;
    spacing: 4px;
}

QTextEdit {
    background-color: #f8efe7;
    color: #2c232e;
    border: 1px solid #d2c9c4;
    border-radius: 4px;
    font-size: inherit;
}

QFrame#thinking_block {
    background: #f0e8e0;
    border: 1px solid #d2c9c4;
    border-radius: 6px;
}

QFrame#message_queued {
    border: 1px dashed #2473b6;
    border-radius: 6px;
    background: #f8efe7;
}

QFrame#message_question {
    border: 1px solid #b16803;
    border-radius: 6px;
    background: #f0e8e0;
}

QLabel#error_header {
    color: #ce4770;
    font-weight: bold;
    font-size: inherit;
}

QLabel#error_content {
    color: #2c232e;
    font-size: inherit;
}

QLabel#thinking_header {
    color: #92898a;
    font-size: inherit;
    font-style: italic;
}

QLabel#thinking_content {
    color: #72696d;
    font-size: inherit;
}

QLabel#star_label {
    color: #b16803;
    font-size: inherit;
}

QLabel#phrase_label {
    color: #92898a;
    font-style: italic;
    font-size: inherit;
}

QLabel#queued_badge {
    color: #92898a;
    font-size: inherit;
    font-style: italic;
}

QLabel#question_header {
    color: #b16803;
    font-weight: bold;
    font-size: inherit;
}

QLabel#question_content {
    color: #2c232e;
    font-size: inherit;
}

QLabel#phase_label {
    color: #b16803;
    font-weight: bold;
    font-size: inherit;
}

QLabel#reason_label {
    color: #a59c9c;
    font-size: inherit;
}

QLabel#note_path {
    color: #72696d;
    font-size: inherit;
}

QLabel#note_preview {
    color: #a59c9c;
    font-size: inherit;
}

QLabel#subagent_detail {
    color: #72696d;
    font-size: inherit;
}

QLabel#finding_summary {
    color: #2c232e;
    font-size: inherit;
}

QLabel#addr_label {
    color: #92898a;
    font-size: inherit;
}

QFrame#delegation_approval {
    border: 1px solid #218871;
    border-radius: 6px;
    background: #f0f5f3;
}

QFrame#mutation_entry {
    background: transparent;
}

QLabel#mutation_indicator {
    color: #218871;
    font-size: inherit;
}

QLabel#mutation_desc {
    color: #2c232e;
    font-size: inherit;
}

QLabel#mutation_badge {
    color: #92898a;
    font-size: inherit;
    padding: 1px 4px;
    background: #e8e0d8;
    border-radius: 3px;
}

QPushButton#undo_mutation_btn {
    color: #218871;
    background: #f8efe7;
    border: 1px solid #218871;
    border-radius: 3px;
    padding: 3px 10px;
    font-size: inherit;
}

QPushButton#undo_mutation_btn:hover {
    background: #e8e0d8;
}

QPushButton#undo_mutation_btn:disabled {
    color: #92898a;
    border-color: #92898a;
}

QFrame#bulk_renamer_widget {
    background-color: #f8efe7;
}

QFrame#agent_tree_widget {
    background-color: #f8efe7;
}

QFrame#orchestra_panel {
    background-color: #f8efe7;
}

QLabel#orchestra_header {
    font-size: inherit;
    font-weight: bold;
    color: #218871;
}

QFrame#delegation_dialog {
    background: #1e1e1e;
}

/* History navigation strip (paginated restore) — object-name-scoped
   so generic QPushButton/QLabel styles above do not affect it. */
QFrame#history_nav {
    background: #e8e0d8;
    border: 1px solid #d2c9c4;
    border-radius: 4px;
    padding: 2px 4px;
}

QLabel#history_nav_label {
    color: #72696d;
    font-size: inherit;
    padding: 0 6px;
}

QPushButton#history_nav_btn {
    background: #f0e8e0;
    color: #2c232e;
    border: 1px solid #d2c9c4;
    border-radius: 3px;
    padding: 2px 10px;
    font-size: inherit;
}
QPushButton#history_nav_btn:hover {
    background: #e8e0d8;
}
QPushButton#history_nav_btn:pressed {
    background: #d2c9c4;
}
QPushButton#history_nav_btn:disabled {
    color: #92898a;
    background: #e8e0d8;
    border-color: #d2c9c4;
}
"""

# Dark Theme - VS Code Dark+ inspired
DARK_THEME = """
QWidget#rikugan_panel {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

QScrollArea#chat_scroll {
    background-color: #1e1e1e;
    border: none;
}

QWidget#chat_container {
    background-color: #1e1e1e;
}

QFrame#message_user {
    background-color: #2d2d2d;
    border-radius: 8px;
    padding: 8px;
    margin: 4px 8px 4px 8px;
}

QFrame#message_assistant {
    background-color: #1e1e1e;
    border-radius: 8px;
    padding: 8px;
    margin: 4px 8px 4px 8px;
}

QFrame#message_tool {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#message_thinking {
    background-color: #1e1e1e;
    border-radius: 6px;
    padding: 4px 8px;
    margin: 2px 8px;
}



QPlainTextEdit#input_area {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #264f78;
}

QPlainTextEdit#input_area:focus {
    border-color: #007acc;
}

QPushButton#send_button {
    background-color: #007acc;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}

QPushButton#send_button:hover {
    background-color: #1a8ad4;
}

QPushButton#send_button:pressed {
    background-color: #005a9e;
}

QPushButton#send_button:disabled {
    background-color: #3c3c3c;
    color: #6c6c6c;
}

QPushButton#cancel_button {
    background-color: #c72e2e;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}

QFrame#context_bar {
    background-color: #252526;
    border-top: 1px solid #3c3c3c;
    padding: 4px 8px;
}

QLabel#context_label {
    color: #808080;
    font-size: inherit;
}

QLabel#context_value {
    color: #cccccc;
    font-size: inherit;
}

QFrame#plan_step {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}

QFrame#plan_step_active {
    background-color: #252526;
    border: 1px solid #007acc;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}

QFrame#plan_step_done {
    background-color: #252526;
    border: 1px solid #4ec9b0;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}

QToolButton#collapse_button {
    border: none;
    color: #808080;
    font-size: inherit;
}

QToolButton#collapse_button:hover {
    color: #d4d4d4;
}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 4px;
}

QGroupBox {
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QFrame#tools_panel {
    background-color: #1e1e1e;
    border-left: 1px solid #3c3c3c;
}

QFrame#tools_panel QTabWidget::pane {
    border: none;
}

QFrame#tools_panel QTabBar {
    background: #1e1e1e;
    border: none;
}

QFrame#tools_panel QTabBar::tab {
    background: #252526;
    color: #cccccc;
    padding: 4px 12px;
    border: none;
    border-right: 1px solid #3c3c3c;
    font-size: inherit;
}

QFrame#tools_panel QTabBar::tab:selected {
    background: #1e1e1e;
    color: #ffffff;
}

QFrame#tools_panel QTabBar::tab:hover {
    background: #2d2d2d;
}

QTreeWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: none;
    font-size: inherit;
}

QTreeWidget::item {
    padding: 2px 4px;
}

QTreeWidget::item:selected {
    background-color: #264f78;
}

QTreeWidget::item:hover {
    background-color: #2d2d2d;
}

QHeaderView::section {
    background-color: #252526;
    color: #cccccc;
    border: none;
    border-right: 1px solid #3c3c3c;
    padding: 3px 6px;
    font-size: inherit;
}

QTableWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: none;
    gridline-color: #3c3c3c;
    font-size: inherit;
}

QTableWidget::item {
    padding: 2px 4px;
}

QTableWidget::item:selected {
    background-color: #264f78;
}

QProgressBar {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    text-align: center;
    color: #d4d4d4;
    font-size: inherit;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #4ec9b0;
    border-radius: 2px;
}

QRadioButton {
    color: #d4d4d4;
    font-size: inherit;
    spacing: 4px;
}

QTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    font-size: inherit;
}

QFrame#thinking_block {
    background: #1a1a2e;
    border: 1px solid #2a2a3e;
    border-radius: 6px;
}

QFrame#message_queued {
    border: 1px dashed #007acc;
    border-radius: 6px;
    background: #1e1e2e;
}

QFrame#message_question {
    border: 1px solid #dcdcaa;
    border-radius: 6px;
    background: #2d2d1e;
}

QLabel#msg_role_label {
    color: #4ec9b0;
    font-weight: bold;
    font-size: inherit;
}

QLabel#tool_header {
    color: #569cd6;
    font-weight: bold;
    font-size: inherit;
}

QLabel#tool_content {
    color: #9cdcfe;
    font-size: inherit;
}

QLabel#collapse_button {
    border: none;
    color: #808080;
    font-size: inherit;
}

QLabel#thinking_header {
    color: #707090;
    font-size: inherit;
    font-style: italic;
}

QLabel#thinking_content {
    color: #606078;
    font-size: inherit;
}

QLabel#star_label {
    color: #dcdcaa;
    font-size: inherit;
}

QLabel#phrase_label {
    color: #808080;
    font-style: italic;
    font-size: inherit;
}

QLabel#queued_badge {
    color: #808080;
    font-size: inherit;
    font-style: italic;
}

QLabel#question_header {
    color: #dcdcaa;
    font-weight: bold;
    font-size: inherit;
}

QLabel#question_content {
    color: #d4d4d4;
    font-size: inherit;
}

QLabel#phase_label {
    color: #d7ba7d;
    font-weight: bold;
    font-size: inherit;
}

QLabel#reason_label {
    color: #b0a070;
    font-size: inherit;
}

QLabel#cat_label {
    font-weight: bold;
    font-size: inherit;
}

QLabel#addr_label {
    color: #808080;
    font-size: inherit;
}

QLabel#finding_summary {
    color: #d4d4d4;
    font-size: inherit;
}

QLabel#note_title {
    font-weight: bold;
    font-size: inherit;
}

QLabel#note_genre {
    color: #808080;
    font-size: inherit;
    font-style: italic;
}

QLabel#note_path {
    color: #606060;
    font-size: inherit;
}

QLabel#note_preview {
    color: #a0a0a0;
    font-size: inherit;
}

QLabel#subagent_icon {
    font-size: inherit;
}

QLabel#subagent_label {
    font-weight: bold;
    font-size: inherit;
}

QLabel#subagent_detail {
    color: #b0b0b0;
    font-size: inherit;
}

QLabel#error_header {
    color: #f44747;
    font-weight: bold;
    font-size: inherit;
}

QLabel#error_content {
    color: #d4d4d4;
    font-size: inherit;
}

QLabel#msg_content {
    color: inherit;
}

QLabel#relevance_star {
    color: #d7ba7d;
    font-size: inherit;
}

QFrame#finding_tool {
    border: 1px solid;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#note_tool {
    border: 1px solid;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#subagent_tool {
    border: 1px solid;
    border-radius: 4px;
    padding: 3px 6px;
    margin: 1px 12px 1px 12px;
}

QFrame#skill_popup {
    border: 1px solid;
    border-radius: 4px;
    padding: 2px;
}

QFrame#skill_popup QLabel {
    padding: 3px 8px;
}

QFrame#skill_popup QLabel[selected="true"] {
    border-radius: 3px;
}

QPushButton#option_btn {
    background: #2d4a6e;
    color: #9cdcfe;
    border: 1px solid #4a7ab5;
    border-radius: 4px;
    padding: 4px 14px;
    font-size: inherit;
}

QPushButton#option_btn:hover {
    background: #3a5a8a;
}

QPushButton#option_btn:pressed {
    background: #1a3a5e;
}

QPushButton#option_btn:disabled {
    color: #808080;
    background: #1e2a3a;
    border-color: #444;
}

QFrame#delegation_approval {
    border: 1px solid #4ec9b0;
    border-radius: 6px;
    background: #1e2e2e;
}

QFrame#mutation_entry {
    background: transparent;
}

QLabel#mutation_indicator {
    color: #4ec9b0;
    font-size: inherit;
}

QLabel#mutation_desc {
    color: #d4d4d4;
    font-size: inherit;
}

QLabel#mutation_badge {
    color: #808080;
    font-size: inherit;
    padding: 1px 4px;
    background: #2d2d2d;
    border-radius: 3px;
}

QPushButton#undo_mutation_btn {
    color: #4ec9b0;
    background: #2d2d2d;
    border: 1px solid #4ec9b0;
    border-radius: 3px;
    padding: 3px 10px;
    font-size: inherit;
}

QPushButton#undo_mutation_btn:hover {
    background: #3d3d3d;
}

QPushButton#undo_mutation_btn:disabled {
    color: #555;
    border-color: #555;
}

QFrame#bulk_renamer_widget {
    background-color: #1e1e1e;
}

QFrame#agent_tree_widget {
    background-color: #1e1e1e;
}

QFrame#orchestra_panel {
    background-color: #1e1e1e;
}

QLabel#orchestra_header {
    font-size: inherit;
    font-weight: bold;
    color: #4ec9b0;
}

QFrame#delegation_dialog {
    background: #1e1e1e;
}

/* History navigation strip (paginated restore) — object-name-scoped
   so generic QPushButton/QLabel styles above do not affect it. */
QFrame#history_nav {
    background: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 2px 4px;
}

QLabel#history_nav_label {
    color: #808080;
    font-size: inherit;
    padding: 0 6px;
}

QPushButton#history_nav_btn {
    background: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 2px 10px;
    font-size: inherit;
}
QPushButton#history_nav_btn:hover {
    background: #3c3c3c;
}
QPushButton#history_nav_btn:pressed {
    background: #1e1e1e;
}
QPushButton#history_nav_btn:disabled {
    color: #555;
    background: #252526;
    border-color: #3c3c3c;
}
"""


# =============================================================================
# Theme-aware style constants for inline widget styling
# These are used by widgets that need to apply styles dynamically
# =============================================================================

# Tool call widget colors
TOOL_COLORS = {
    "dark": {
        "bullet": "#dcdcaa",
        "status_spinner": "#dcdcaa",
        "status_error": "#f44747",
        "status_success": "#4ec9b0",
        "preview": "#808080",
        "result_header": "#808080",
    },
    "light": {
        "bullet": "#b16803",
        "status_spinner": "#b16803",
        "status_error": "#ce4770",
        "status_success": "#218871",
        "preview": "#92898a",
        "result_header": "#92898a",
    },
}

# Small button style (Send, New, Export, Settings, Tools)
SMALL_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 6px; padding: 4px; font-size: inherit; }"
        "QPushButton:hover { background: #3c3c3c; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 6px; padding: 4px; font-size: inherit; }"
        "QPushButton:hover { background: #e8e0d8; }"
    ),
}

# Cancel button style
CANCEL_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #c42b1c; border: 1px solid #3c3c3c; "
        "border-radius: 6px; padding: 4px; font-size: inherit; }"
        "QPushButton:hover { background: #3c3c3c; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #c0392b; border: 1px solid #d2c9c4; "
        "border-radius: 6px; padding: 4px; font-size: inherit; }"
        "QPushButton:hover { background: #e8e0d8; }"
    ),
}

# Mode bar style (Chat | Tools tabs)
MODE_BAR_STYLE = {
    "dark": (
        "QTabBar { background: #2d2d2d; border: none; border-bottom: 1px solid #3c3c3c; }"
        "QTabBar::tab { background: #2d2d2d; color: #808080; padding: 4px 16px; "
        "border: none; border-bottom: 2px solid transparent; font-size: inherit; }"
        "QTabBar::tab:selected { color: #d4d4d4; border-bottom: 2px solid #4ec9b0; }"
        "QTabBar::tab:hover:!selected { color: #d4d4d4; }"
    ),
    "light": (
        "QTabBar { background: #e8e0d8; border: none; border-bottom: 1px solid #d2c9c4; }"
        "QTabBar::tab { background: #e8e0d8; color: #92898a; padding: 4px 16px; "
        "border: none; border-bottom: 2px solid transparent; font-size: inherit; }"
        "QTabBar::tab:selected { color: #2c232e; border-bottom: 2px solid #218871; }"
        "QTabBar::tab:hover:!selected { color: #2c232e; }"
    ),
}

# Tab widget style for chat tabs
TAB_WIDGET_STYLE = {
    "dark": (
        "QTabWidget::pane { border: none; }"
        "QTabBar { background: #1e1e1e; border: none; }"
        "QTabBar::tab { background: #252526; color: #cccccc; padding: 2px 8px; "
        "border: none; border-right: 1px solid #3c3c3c; "
        "font-size: inherit; max-width: 140px; }"
        "QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; }"
        "QTabBar::tab:hover { background: #2d2d2d; }"
        "QTabBar::close-button { image: none; border: none; padding: 1px; }"
        "QTabBar::close-button:hover { background: #c42b1c; border-radius: 2px; }"
    ),
    "light": (
        "QTabWidget::pane { border: none; }"
        "QTabBar { background: #f8efe7; border: none; }"
        "QTabBar::tab { background: #f0e8e0; color: #72696d; padding: 2px 8px; "
        "border: none; border-right: 1px solid #d2c9c4; "
        "font-size: inherit; max-width: 140px; }"
        "QTabBar::tab:selected { background: #f8efe7; color: #2c232e; }"
        "QTabBar::tab:hover { background: #e8e0d8; }"
        "QTabBar::close-button { image: none; border: none; padding: 1px; }"
        "QTabBar::close-button:hover { background: #c0392b; border-radius: 2px; }"
    ),
}

# Tools panel header style
TOOLS_PANEL_HEADER_STYLE = {
    "dark": "color: #d4d4d4; font-weight: bold; font-size: inherit;",
    "light": "color: #2c232e; font-weight: bold; font-size: inherit;",
}

# Placeholder label style (for "Not loaded" labels in tools panel)
PLACEHOLDER_STYLE = {
    "dark": "color: #808080; padding: 20px;",
    "light": "color: #92898a; padding: 20px;",
}

# Tools panel button style
TOOLS_PANEL_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 4px; padding: 2px 8px; font-size: inherit; }"
        "QPushButton:hover { background: #3c3c3c; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 4px; padding: 2px 8px; font-size: inherit; }"
        "QPushButton:hover { background: #e8e0d8; }"
    ),
}

# Tools panel stylesheet
TOOLS_PANEL_STYLE = {
    "dark": """
        QWidget#tools_panel {
            background: #1e1e1e;
        }
        QTabWidget::pane {
            border: none;
            background: #1e1e1e;
        }
        QTabBar::tab {
            background: #2d2d2d;
            color: #808080;
            border: 1px solid #3c3c3c;
            border-bottom: none;
            padding: 5px 14px;
            font-size: inherit;
            min-width: 60px;
        }
        QTabBar::tab:selected {
            background: #1e1e1e;
            color: #d4d4d4;
            border-bottom: 2px solid #4ec9b0;
        }
        QTabBar::tab:hover:!selected {
            background: #353535;
            color: #d4d4d4;
        }
    """,
    "light": """
        QWidget#tools_panel {
            background: #f8efe7;
        }
        QTabWidget::pane {
            border: none;
            background: #f8efe7;
        }
        QTabBar::tab {
            background: #f0e8e0;
            color: #72696d;
            border: 1px solid #d2c9c4;
            border-bottom: none;
            padding: 5px 14px;
            font-size: inherit;
            min-width: 60px;
        }
        QTabBar::tab:selected {
            background: #f8efe7;
            color: #2c232e;
            border-bottom: 2px solid #218871;
        }
        QTabBar::tab:hover:!selected {
            background: #e8e0d8;
            color: #2c232e;
        }
    """,
}

# Add button style for tab bar
ADD_TAB_BTN_STYLE = {
    "dark": (
        "QToolButton { color: #d4d4d4; font-size: inherit; font-weight: bold; "
        "border: none; background: transparent; }"
        "QToolButton:hover { background: #3c3c3c; border-radius: 3px; }"
    ),
    "light": (
        "QToolButton { color: #2c232e; font-size: inherit; font-weight: bold; "
        "border: none; background: transparent; }"
        "QToolButton:hover { background: #e8e0d8; border-radius: 3px; }"
    ),
}

# Splitter handle style
SPLITTER_HANDLE_STYLE = {
    "dark": "QSplitter::handle { background: #3c3c3c; }",
    "light": "QSplitter::handle { background: #d2c9c4; }",
}

# Message dialog style for new chat confirmation
MESSAGE_DIALOG_STYLE = {
    "dark": (
        "QMessageBox { background: #1e1e1e; color: #d4d4d4; }"
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 4px; padding: 6px 16px; font-size: inherit; min-width: 80px; }"
        "QPushButton:hover { background: #3c3c3c; }"
    ),
    "light": (
        "QMessageBox { background: #f8efe7; color: #2c232e; }"
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 4px; padding: 6px 16px; font-size: inherit; min-width: 80px; }"
        "QPushButton:hover { background: #e8e0d8; }"
    ),
}

# Error label style
ERROR_LABEL_STYLE = {
    "dark": "color: #f44747;",
    "light": "color: #ce4770;",
}

# Status label styles
OK_STATUS_STYLE = {
    "dark": "color: #4ec9b0; font-weight: bold;",
    "light": "color: #218871; font-weight: bold;",
}

HINT_STATUS_STYLE = {
    "dark": "color: #808080;",
    "light": "color: #92898a;",
}

ERR_STATUS_STYLE = {
    "dark": "color: #f44747;",
    "light": "color: #ce4770;",
}

# Bulk renamer styles moved to ui/theme/widgets_bulk.py
# Agent-tree styles moved to ui/theme/widgets_agent.py
# Orchestra panel styles
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

# Mutation log styles
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

# History navigation strip styles (used by paginated restore in chat_view)
HISTORY_NAV_FRAME_STYLE = {
    "dark": (
        "QFrame#history_nav { background: #252526; border: 1px solid #3c3c3c; "
        "border-radius: 4px; padding: 2px 4px; }"
    ),
    "light": (
        "QFrame#history_nav { background: #e8e0d8; border: 1px solid #d2c9c4; "
        "border-radius: 4px; padding: 2px 4px; }"
    ),
}

HISTORY_NAV_BTN_STYLE = {
    "dark": (
        "QPushButton#history_nav_btn { background: #2d2d2d; color: #d4d4d4; "
        "border: 1px solid #3c3c3c; border-radius: 3px; padding: 2px 10px; "
        "font-size: inherit; }"
        "QPushButton#history_nav_btn:hover { background: #3c3c3c; }"
        "QPushButton#history_nav_btn:pressed { background: #1e1e1e; }"
        "QPushButton#history_nav_btn:disabled { color: #555; "
        "background: #252526; border-color: #3c3c3c; }"
    ),
    "light": (
        "QPushButton#history_nav_btn { background: #f0e8e0; color: #2c232e; "
        "border: 1px solid #d2c9c4; border-radius: 3px; padding: 2px 10px; "
        "font-size: inherit; }"
        "QPushButton#history_nav_btn:hover { background: #e8e0d8; }"
        "QPushButton#history_nav_btn:pressed { background: #d2c9c4; }"
        "QPushButton#history_nav_btn:disabled { color: #92898a; "
        "background: #e8e0d8; border-color: #d2c9c4; }"
    ),
}

HISTORY_NAV_LABEL_STYLE = {
    "dark": "color: #808080; font-size: inherit; padding: 0 6px;",
    "light": "color: #72696d; font-size: inherit; padding: 0 6px;",
}

# Settings dialog styles
SETTINGS_BTN_STYLE = {
    "dark": (
        "QPushButton { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; "
        "border-radius: 4px; font-weight: bold; }"
        "QPushButton:hover { background: #3c3c3c; }"
    ),
    "light": (
        "QPushButton { background: #f0e8e0; color: #2c232e; border: 1px solid #d2c9c4; "
        "border-radius: 4px; font-weight: bold; }"
        "QPushButton:hover { background: #e8e0d8; }"
    ),
}

# Helper functions to get themed styles


def _theme_get(name: str) -> str | dict[str, str]:
    """Look up a theme-aware dict by name for the active theme."""
    d = globals()[name]
    return d["dark" if is_dark_theme() else "light"]


def get_small_btn_style() -> str:
    return _theme_get("SMALL_BTN_STYLE")


def get_cancel_btn_style() -> str:
    return _theme_get("CANCEL_BTN_STYLE")


def get_mode_bar_style() -> str:
    return _theme_get("MODE_BAR_STYLE")


def get_tab_widget_style() -> str:
    return _theme_get("TAB_WIDGET_STYLE")


def get_tools_panel_header_style() -> str:
    return _theme_get("TOOLS_PANEL_HEADER_STYLE")


def get_placeholder_style() -> str:
    return _theme_get("PLACEHOLDER_STYLE")


def get_tools_panel_btn_style() -> str:
    return _theme_get("TOOLS_PANEL_BTN_STYLE")


def get_tools_panel_style() -> str:
    return _theme_get("TOOLS_PANEL_STYLE")


def get_add_tab_btn_style() -> str:
    return _theme_get("ADD_TAB_BTN_STYLE")


def get_splitter_handle_style() -> str:
    return _theme_get("SPLITTER_HANDLE_STYLE")


def get_message_dialog_style() -> str:
    return _theme_get("MESSAGE_DIALOG_STYLE")


def get_error_label_style() -> str:
    return _theme_get("ERROR_LABEL_STYLE")


def get_ok_status_style() -> str:
    return _theme_get("OK_STATUS_STYLE")


def get_hint_status_style() -> str:
    return _theme_get("HINT_STATUS_STYLE")


def get_err_status_style() -> str:
    return _theme_get("ERR_STATUS_STYLE")
# Bulk-renamer style getters moved to ui/theme/widgets_bulk.py;
# re-exported here so existing ``from .styles import get_bulk_*`` callers
# keep working unchanged.
# Agent-tree style getters moved to ui/theme/widgets_agent.py;
# re-exported here so existing 'from .styles import get_agent_*' callers
# keep working unchanged.
from .theme.widgets_agent import (  # noqa: E402,F401 — re-export
    AGENT_BTN_STYLE,
    AGENT_COMBO_STYLE,
    AGENT_PREVIEW_STYLE,
    AGENT_STATUS_COLORS,
    AGENT_STATUS_LABEL_STYLE,
    AGENT_TREE_STYLE,
    get_agent_btn_style,
    get_agent_combo_style,
    get_agent_preview_style,
    get_agent_status_colors,
    get_agent_status_label_style,
    get_agent_tree_style,
)
from .theme.widgets_bulk import (  # noqa: E402,F401 — re-export
    BULK_BTN_STYLE,
    BULK_CHECK_STYLE,
    BULK_COMBO_STYLE,
    BULK_FILTER_STYLE,
    BULK_MODE_LABEL_STYLE,
    BULK_NUM_INPUT_STYLE,
    BULK_PROGRESS_STYLE,
    BULK_RADIO_STYLE,
    BULK_SELECTION_LABEL_STYLE,
    BULK_START_BTN_STYLE,
    BULK_STATUS_COLORS,
    BULK_STOP_BTN_STYLE,
    BULK_TABLE_STYLE,
    get_bulk_btn_style,
    get_bulk_check_style,
    get_bulk_combo_style,
    get_bulk_filter_style,
    get_bulk_mode_label_style,
    get_bulk_num_input_style,
    get_bulk_progress_style,
    get_bulk_radio_style,
    get_bulk_selection_label_style,
    get_bulk_start_btn_style,
    get_bulk_status_colors,
    get_bulk_stop_btn_style,
    get_bulk_table_style,
)


def get_orchestra_panel_style() -> str:
    return _theme_get("ORCHESTRA_PANEL_STYLE")


def get_orchestra_stats_style() -> str:
    return _theme_get("ORCHESTRA_STATS_STYLE")


def get_delegation_dialog_style() -> str:
    return _theme_get("DELEGATION_DIALOG_STYLE")


def get_delegation_approval_widget_style() -> str:
    return _theme_get("DELEGATION_APPROVAL_WIDGET_STYLE")


def get_delegation_header_style() -> str:
    return _theme_get("DELEGATION_HEADER_STYLE")


def get_delegation_info_style() -> str:
    return _theme_get("DELEGATION_INFO_STYLE")


def get_delegation_preview_style() -> str:
    return _theme_get("DELEGATION_PREVIEW_STYLE")


def get_profiles_btn_style() -> str:
    return _theme_get("PROFILES_BTN_STYLE")


def get_profiles_group_style() -> str:
    return _theme_get("PROFILES_GROUP_STYLE")


def get_profiles_header_style() -> str:
    return _theme_get("PROFILES_HEADER_STYLE")


def get_mutation_indicator_style(reversible: bool) -> str:
    """Get the mutation indicator style for the current theme."""
    theme = "dark" if is_dark_theme() else "light"
    key = "reversible" if reversible else "irreversible"
    return MUTATION_INDICATOR_STYLE[theme][key]


def get_mutation_desc_style() -> str:
    return _theme_get("MUTATION_DESC_STYLE")


def get_mutation_badge_style() -> str:
    return _theme_get("MUTATION_BADGE_STYLE")


def get_mutation_undo_btn_style() -> str:
    return _theme_get("MUTATION_UNDO_BTN_STYLE")


def get_mutation_title_style() -> str:
    return _theme_get("MUTATION_TITLE_STYLE")


def get_mutation_count_style() -> str:
    return _theme_get("MUTATION_COUNT_STYLE")


def get_tool_approval_frame_style() -> str:
    return _theme_get("TOOL_APPROVAL_FRAME_STYLE")


def get_tool_approval_header_style() -> str:
    return _theme_get("TOOL_APPROVAL_HEADER_STYLE")


def get_tool_approval_code_editor_style() -> str:
    return _theme_get("TOOL_APPROVAL_CODE_EDITOR_STYLE")


def get_tool_approval_allow_btn_style() -> str:
    return _theme_get("TOOL_APPROVAL_ALLOW_BTN_STYLE")


def get_tool_approval_always_btn_style() -> str:
    return _theme_get("TOOL_APPROVAL_ALWAYS_BTN_STYLE")


def get_tool_approval_deny_btn_style() -> str:
    return _theme_get("TOOL_APPROVAL_DENY_BTN_STYLE")


def get_tool_approval_disabled_btn_style() -> str:
    return _theme_get("TOOL_APPROVAL_DISABLED_BTN_STYLE")


def get_settings_btn_style() -> str:
    return _theme_get("SETTINGS_BTN_STYLE")


def get_history_nav_frame_style() -> str:
    return _theme_get("HISTORY_NAV_FRAME_STYLE")


def get_history_nav_button_style() -> str:
    return _theme_get("HISTORY_NAV_BTN_STYLE")


def get_history_nav_label_style() -> str:
    return _theme_get("HISTORY_NAV_LABEL_STYLE")


def get_tool_colors() -> dict[str, str]:
    return _theme_get("TOOL_COLORS")


# =============================================================================
# Theme-aware style shims (added for theme.manager integration)
# =============================================================================
#
# The production code (panel_core, message_widgets, settings_dialog, etc.)
# imports these helpers from .styles. They previously lived alongside the
# now-removed theme subsystem. The shims below preserve the call sites
# while delegating to either the new ThemeManager or a safe default.
#
# They are deliberately simple — for any visual refinement the manager
# and the styles constants in this module are the source of truth.


def use_native_host_theme() -> bool:
    """Return True when the current theme should inherit the host palette.

    Equivalent to ``is_host_theme()``; provided as a backwards-compatible
    name for callers migrated from the old theme subsystem.
    """
    return is_host_theme()


def host_stylesheet(css: str, fallback: str = "") -> str:
    """Return ``css`` unchanged if the host theme is active, else ``""``.

    When the user selected the "ida" theme we do NOT apply Rikugan's
    inline styles — the host's Qt theme is the source of truth and
    Rikugan's colors would clash with it. For all other themes the
    caller-supplied ``css`` is returned verbatim.

    Callers that want a host-friendly default pass a second argument;
    it is only used in the host-theme branch.
    """
    if is_host_theme():
        return fallback
    return css


def maybe_host_stylesheet(css: str, fallback: str = "") -> str:
    """Alias for :func:`host_stylesheet` (older name)."""
    return host_stylesheet(css, fallback)


def build_theme_stylesheet(widget: object) -> str:
    """Build a minimal theme stylesheet for ``widget``.

    Production path: panel_core already calls individual style getters
    on each child widget. The top-level stylesheet is a no-op here so
    that global QWidget selectors do not bleed into the host (IDA) UI.
    """
    return ""


def build_small_button_stylesheet(widget: object, danger: bool = False) -> str:
    """Build a small-button stylesheet; delegates to the constants above.

    When ``danger=True`` the cancel/remove color palette is used so destructive
    actions (e.g. "Undo All") are visually distinct from regular buttons.
    """
    if danger:
        return _theme_get("CANCEL_BTN_STYLE")
    return get_small_btn_style()


# =============================================================================
# Explicit ThemeTokens-based stylesheet builders
# =============================================================================
#
# The functions below build a small QSS string from a ``ThemeTokens``
# instance.  They are used by ``SettingsDialog`` and ``InputArea`` so
# the user-selected Rikugan Light / Dark theme always paints the
# dialog body and the chat input with the chosen palette, even when
# the host's default Qt palette would otherwise leak through as a
# black background in light mode.
#
# The returned QSS uses a ``#rikugan_settings`` / ``#input_area``
# object-name selector so the styles do not bleed into the rest of
# the host application (e.g. IDA's main window).


def build_settings_dialog_stylesheet(tokens: object) -> str:
    """Build a ThemeTokens-driven QSS for ``SettingsDialog``.

    The returned stylesheet targets only widgets under
    ``#rikugan_settings`` (the dialog's object name) and the standard
    editor controls (``QLineEdit``, ``QComboBox``, ``QSpinBox``,
    ``QDoubleSpinBox``, ``QPlainTextEdit``, ``QCheckBox``, ``QLabel``,
    ``QGroupBox``, ``QTabWidget``) so we do not affect any other
    host UI.  In the host/IDA-native mode, returns an empty string
    so the host's palette remains the source of truth.
    """
    if is_host_theme():
        return ""
    base = getattr(tokens, "base", "#ffffff")
    alt_base = getattr(tokens, "alt_base", "#f3f3f3")
    text = getattr(tokens, "text", "#1e1e1e")
    button = getattr(tokens, "button", "#f0f0f0")
    button_text = getattr(tokens, "button_text", "#1e1e1e")
    highlight = getattr(tokens, "highlight", "#0066cc")
    highlight_text = getattr(tokens, "highlight_text", "#ffffff")
    mid = getattr(tokens, "mid", "#cccccc")
    window = getattr(tokens, "window", base)
    return (
        f"#rikugan_settings {{ background-color: {window}; color: {text}; }}"
        f"#rikugan_settings QWidget {{ background-color: {base}; color: {text}; }}"
        f"#rikugan_settings QLabel {{ background: transparent; color: {text}; }}"
        f"#rikugan_settings QGroupBox {{"
        f" background-color: {alt_base}; color: {text};"
        f" border: 1px solid {mid}; border-radius: 4px;"
        f" margin-top: 8px; padding-top: 12px;"
        f"}}"
        f"#rikugan_settings QGroupBox::title {{"
        f" subcontrol-origin: margin; left: 8px; padding: 0 4px;"
        f" color: {text};"
        f"}}"
        f"#rikugan_settings QTabWidget::pane {{"
        f" border: 1px solid {mid}; background: {base};"
        f"}}"
        f"#rikugan_settings QTabBar::tab {{"
        f" background: {alt_base}; color: {text}; padding: 4px 12px;"
        f" border: 1px solid {mid}; border-bottom: none;"
        f" border-top-left-radius: 4px; border-top-right-radius: 4px;"
        f"}}"
        f"#rikugan_settings QTabBar::tab:selected {{"
        f" background: {base}; color: {text};"
        f" border-bottom: 1px solid {base};"
        f"}}"
        f"#rikugan_settings QLineEdit, "
        f"#rikugan_settings QComboBox, "
        f"#rikugan_settings QSpinBox, "
        f"#rikugan_settings QDoubleSpinBox, "
        f"#rikugan_settings QPlainTextEdit {{"
        f" background-color: {base}; color: {text};"
        f" border: 1px solid {mid}; border-radius: 4px;"
        f" padding: 3px 6px; selection-background-color: {highlight};"
        f" selection-color: {highlight_text};"
        f"}}"
        f"#rikugan_settings QLineEdit:focus, "
        f"#rikugan_settings QComboBox:focus, "
        f"#rikugan_settings QSpinBox:focus, "
        f"#rikugan_settings QDoubleSpinBox:focus, "
        f"#rikugan_settings QPlainTextEdit:focus {{"
        f" border-color: {highlight};"
        f"}}"
        f"#rikugan_settings QComboBox QAbstractItemView {{"
        f" background-color: {base}; color: {text};"
        f" border: 1px solid {mid}; selection-background-color: {highlight};"
        f" selection-color: {highlight_text};"
        f"}}"
        f"#rikugan_settings QCheckBox {{ color: {text}; }}"
        f"#rikugan_settings QRadioButton {{ color: {text}; }}"
        f"#rikugan_settings QPushButton {{"
        f" background-color: {button}; color: {button_text};"
        f" border: 1px solid {mid}; border-radius: 4px; padding: 4px 12px;"
        f"}}"
        f"#rikugan_settings QPushButton:hover {{"
        f" background-color: {alt_base};"
        f"}}"
        f"#rikugan_settings QPushButton:pressed {{"
        f" background-color: {mid}; color: {text};"
        f"}}"
        f"#rikugan_settings QDialogButtonBox {{ background: transparent; }}"
    )


def build_input_area_stylesheet(tokens: object) -> str:
    """Build a ThemeTokens-driven QSS for the chat ``InputArea``.

    Targets the ``QPlainTextEdit#input_area`` object name only, so
    the styles do not bleed into other plain text editors in the
    host.  Returns an empty string in host/IDA-native mode.
    """
    if is_host_theme():
        return ""
    base = getattr(tokens, "base", "#ffffff")
    text = getattr(tokens, "text", "#1e1e1e")
    mid = getattr(tokens, "mid", "#cccccc")
    highlight = getattr(tokens, "highlight", "#0066cc")
    highlight_text = getattr(tokens, "highlight_text", "#ffffff")
    return (
        f"QPlainTextEdit#input_area {{"
        f" background-color: {base}; color: {text};"
        f" border: 1px solid {mid}; border-radius: 6px;"
        f" padding: 6px; selection-background-color: {highlight};"
        f" selection-color: {highlight_text};"
        f"}}"
        f"QPlainTextEdit#input_area:focus {{"
        f" border-color: {highlight};"
        f"}}"
    )


def build_skill_popup_stylesheet(tokens: object) -> str:
    """Build a ThemeTokens-driven QSS for the ``_SkillPopup``.

    The popup is a small floating widget, so the QSS targets its
    object name (``#skill_popup``) and child ``QLabel`` children.
    Returns an empty string in host/IDA-native mode.
    """
    if is_host_theme():
        return ""
    alt_base = getattr(tokens, "alt_base", "#f3f3f3")
    text = getattr(tokens, "text", "#1e1e1e")
    mid = getattr(tokens, "mid", "#cccccc")
    highlight = getattr(tokens, "highlight", "#0066cc")
    highlight_text = getattr(tokens, "highlight_text", "#ffffff")
    return (
        f"QFrame#skill_popup {{"
        f" background-color: {alt_base}; color: {text};"
        f" border: 1px solid {mid}; border-radius: 4px; padding: 2px;"
        f"}}"
        f"QFrame#skill_popup QLabel {{"
        f" background: transparent; color: {text}; padding: 3px 8px;"
        f"}}"
        f"QFrame#skill_popup QLabel[selected=\"true\"] {{"
        f" background-color: {highlight}; color: {highlight_text};"
        f" border-radius: 3px;"
        f"}}"
        f"QFrame#skill_popup QLabel[selected=\"false\"] {{"
        f" background-color: {alt_base}; color: {text};"
        f"}}"
    )
