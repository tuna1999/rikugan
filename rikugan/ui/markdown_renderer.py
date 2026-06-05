"""Custom markdown-it renderer that produces Qt RichText-compatible HTML.

All styling uses inline ``style=`` attributes because QLabel's RichText
engine does not support CSS classes.  The renderer receives a theme
style dict from ``markdown._theme_markdown_styles()`` and produces
self-contained HTML fragments.
"""

from __future__ import annotations

import re as _re
from collections.abc import Sequence
from typing import Any, ClassVar

from markdown_it.common.utils import escapeHtml
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

from .highlight import highlight_code

# ---------------------------------------------------------------------------
# Theme style generation
# ---------------------------------------------------------------------------


def _build_theme_styles(source: Any = None) -> dict[str, str]:
    """Build a complete style dict for the renderer.

    Uses ThemeManager.tokens() for all 17 colors. No more use_native_host_theme()
    branching — the manager already accounts for AUTO/IDA_NATIVE mode.

    The ``source`` parameter is kept for backward compat but unused
    (tokens come from the manager).
    """
    from .theme.manager import ThemeManager, _blend_hex
    from .theme.tokens import is_dark_tokens

    tokens = ThemeManager.instance().tokens()

    base = tokens.base
    window = tokens.window
    text = tokens.text
    highlight = tokens.highlight
    mid = tokens.mid
    code_bg = tokens.code_bg
    code_text = tokens.code_text

    # Recessed border for code blocks: blend mid toward window at 35%
    border = _blend_hex(mid, window, 0.35)
    # Heading color: blend highlight toward text at 15%
    heading_color = _blend_hex(highlight, text, 0.15)
    # Inline code: blend code_bg toward base at 50% for a soft tint
    inline_code_bg = _blend_hex(code_bg, base, 0.5)
    inline_fg = text
    # Muted text: blend text toward mid at 50%
    muted = _blend_hex(text, mid, 0.5)
    # Accent border: use highlight
    accent_border = highlight

    return {
        "is_dark": is_dark_tokens(tokens),
        "inline_code": (
            f"background-color:{inline_code_bg}; color:{inline_fg}; "
            "padding:1px 4px; border-radius:3px; font-family:monospace; font-size:12px;"
        ),
        "code_block": (
            f"background-color:{code_bg}; color:{code_text}; "
            f"border-left:3px solid {accent_border}; border-radius:6px; "
            "padding:8px; font-family:monospace; font-size:12px; "
            "white-space:pre-wrap; word-break:break-all;"
        ),
        "lang_tag": f"color:{muted}; font-size:10px;",
        "link": f"color:{highlight};",
        "heading": f"color:{heading_color}; font-weight:bold;",
        "heading_border": f"border-bottom:1px solid {border};",
        "hr": f"border:1px solid {border};",
        "paragraph": "margin:0 0 4px 0;",
        "blockquote": (
            f"border-left:3px solid {accent_border}; "
            f"color:{muted}; font-style:italic; "
            "padding:4px 12px; margin:4px 0;"
        ),
        "table": "border-collapse:collapse; width:100%;",
        "table_cell": (
            f"border:1px solid {border}; padding:4px 8px; "
            "vertical-align:top; word-wrap:break-word;"
        ),
        "table_header": (
            f"border:1px solid {border}; padding:4px 8px; "
            f"font-weight:bold; background-color:{_blend_hex(base, window, 0.1)};"
        ),
        "table_row_even": f"background-color:{_blend_hex(base, window, 0.05)};",
        "list_item": "margin:1px 0;",
        "task_unchecked": "☐",
        "task_checked": "☑",
    }


# ---------------------------------------------------------------------------
# Task list detection
# ---------------------------------------------------------------------------

_TASK_CHECKED_RE = _re.compile(r"^\[x\]\s?", _re.IGNORECASE)
_TASK_UNCHECKED_RE = _re.compile(r"^\[\s?\]\s?")


def _process_task_list_item(content_html: str, styles: dict[str, str]) -> str:
    """Replace [x] / [ ] at the start of list item content with Unicode checkboxes."""
    if _TASK_CHECKED_RE.search(content_html):
        icon = styles["task_checked"]
        return _TASK_CHECKED_RE.sub(icon + " ", content_html, count=1)
    if _TASK_UNCHECKED_RE.search(content_html):
        icon = styles["task_unchecked"]
        return _TASK_UNCHECKED_RE.sub(icon + " ", content_html, count=1)
    return content_html


# ---------------------------------------------------------------------------
# Heading sizes
# ---------------------------------------------------------------------------

_HEADING_SIZES = {1: 20, 2: 17, 3: 15, 4: 13}


# ---------------------------------------------------------------------------
# QtRenderer
# ---------------------------------------------------------------------------


class QtRenderer(RendererHTML):
    """markdown-it renderer that produces Qt QLabel-compatible HTML.

    Every method receives ``(tokens, idx, options, env)`` per the
    markdown-it renderer protocol.  ``self._styles`` is set per render
    call via ``render_with_styles()``.
    """

    _styles: ClassVar[dict[str, str]] = {}
    _in_list_item: ClassVar[bool] = False

    def render_with_styles(
        self, tokens: Sequence[Token], options: OptionsDict, env: EnvType, styles: dict[str, str]
    ) -> str:
        """Entry point — render tokens using *styles*."""
        self._styles = styles
        return self.render(tokens, options, env)

    # ---- Block-level --------------------------------------------------

    def heading_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return ""

    def heading_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return ""

    def paragraph_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        token = tokens[idx]
        if token.hidden:
            return ""
        s = self._styles
        para_style = s.get("paragraph", "")
        if para_style:
            return f'<div style="{para_style}">'
        return "<div>"

    def paragraph_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        token = tokens[idx]
        if token.hidden:
            return ""
        return "</div>"

    def render(self, tokens: Sequence[Token], options: OptionsDict, env: EnvType) -> str:
        """Override render to track heading context and list item content."""
        result = ""

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "heading_open":
                level = int(token.tag[1]) if token.tag and token.tag[0] == "h" else 3
                # Collect heading_open + inline + heading_close
                content = ""
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    content = self.renderInline(tokens[i + 1].children or [], options, env)
                    i += 2  # skip inline + heading_close
                else:
                    i += 1
                if i < len(tokens) and tokens[i].type == "heading_close":
                    i += 1
                result += self._render_heading(content, level)
                continue

            elif token.type == "inline":
                if token.children:
                    inline_html = self.renderInline(token.children, options, env)
                    result += inline_html
                i += 1
                continue

            elif token.type in self.rules:
                result += self.rules[token.type](tokens, i, options, env)
                i += 1
                continue

            else:
                result += self.renderToken(tokens, i, options, env)
                i += 1
                continue

        return result

    def _render_heading(self, content: str, level: int) -> str:
        s = self._styles
        size = _HEADING_SIZES.get(level, 13)
        parts = [s.get("heading", ""), f"font-size:{size}px;", "margin:8px 0 4px 0;"]
        if level <= 2 and s.get("heading_border"):
            parts.append(s["heading_border"])
        style_str = " ".join(parts)
        return f'<div style="{style_str}">{content}</div>'

    # ---- Fenced code blocks -------------------------------------------

    def fence(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        token = tokens[idx]
        lang = (token.info or "").strip().split()[0] if token.info.strip() else ""
        code = token.content

        is_dark = s.get("is_dark", True)

        if lang:
            highlighted = highlight_code(code, lang, is_dark=is_dark)
        else:
            highlighted = escapeHtml(code)

        block_style = s.get("code_block", "")
        # Use a single-cell table so Qt renders background-color reliably.
        # Qt QLabel supports <td> background but often ignores <div> background.
        table_style = "border-collapse:collapse; width:100%; margin:4px 0;"
        cell_style = block_style
        return (
            f'<table style="{table_style}">'
            f'<tr><td style="{cell_style}">{highlighted}</td></tr>'
            f'</table>'
        )

    def code_block(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        """Indented code block (less common from LLMs)."""
        s = self._styles
        token = tokens[idx]
        code = escapeHtml(token.content)
        block_style = s.get("code_block", "")
        table_style = "border-collapse:collapse; width:100%; margin:4px 0;"
        return (
            f'<table style="{table_style}">'
            f'<tr><td style="{block_style}">{code}</td></tr>'
            f'</table>'
        )

    # ---- Inline code --------------------------------------------------

    def code_inline(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        code = escapeHtml(tokens[idx].content)
        style = s.get("inline_code", "")
        return f'<span style="{style}">{code}</span>'

    # ---- Lists --------------------------------------------------------

    def bullet_list_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return '<ul style="margin:2px 0 2px 20px; padding-left:0; list-style-type:disc;">'

    def bullet_list_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</ul>"

    def ordered_list_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        start_attr = ""
        token = tokens[idx]
        start = token.attrGet("start")
        if start and int(start) != 1:
            start_attr = f' start="{int(start)}"'
        return f'<ol style="margin:2px 0 2px 20px; padding-left:0;"{start_attr}>'

    def ordered_list_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</ol>"

    def list_item_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        self._in_list_item = True
        return "<li>"

    def list_item_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        self._in_list_item = False
        return "</li>"

    # ---- Blockquotes --------------------------------------------------

    def blockquote_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        style = s.get("blockquote", "")
        return f'<div style="{style}">'

    def blockquote_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</div>"

    # ---- Tables -------------------------------------------------------

    def table_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        style = s.get("table", "")
        return f'<table style="{style}">'

    def table_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</table>"

    def thead_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<thead>"

    def thead_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</thead>"

    def tbody_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<tbody>"

    def tbody_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</tbody>"

    def tr_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<tr>"

    def tr_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</tr>"

    def th_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        style = s.get("table_header", "")
        return f'<th style="{style}">'

    def th_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</th>"

    def td_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        style = s.get("table_cell", "")
        return f'<td style="{style}">'

    def td_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</td>"

    # ---- Horizontal rule -----------------------------------------------

    def hr(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        style = s.get("hr", "")
        if style:
            return f'<hr style="{style}">'
        return "<hr>"

    # ---- Inline formatting --------------------------------------------

    def strong_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<b>"

    def strong_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</b>"

    def em_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<i>"

    def em_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</i>"

    def s_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<s>"

    def s_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</s>"

    def link_open(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        s = self._styles
        style = s.get("link", "")
        href = tokens[idx].attrGet("href") or ""
        href_escaped = escapeHtml(str(href))
        return f'<a style="{style}" href="{href_escaped}">'

    def link_close(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "</a>"

    def text(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        content = escapeHtml(tokens[idx].content)
        # Replace task list markers with Unicode checkboxes when inside a list item
        if self._in_list_item:
            content = _process_task_list_item(content, self._styles)
        return content

    def softbreak(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<br>"

    def hardbreak(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<br>"

    def image(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        """Images are not supported in QLabel RichText — render alt text."""
        token = tokens[idx]
        alt = ""
        if token.children:
            alt = self.renderInlineAsText(token.children, options, env)
        return escapeHtml(alt)
