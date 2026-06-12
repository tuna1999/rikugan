"""markdown-it-py renderer that emits Qt-RichText-compatible HTML.

This module pairs with :mod:`rikugan.ui.markdown`. The renderer
walks the CommonMark token tree produced by ``markdown-it-py`` and
emits HTML with *inline* styles only — ``<span style="...">`` /
``<div style="...">``. Qt's rich-text engine is a strict subset
of HTML 4 / CSS 1, so we avoid classes (no ``<style>`` block, no
external CSS) and skip ``<thead>``/``<tbody>`` because Qt drops
them silently.

Public surface used by :mod:`rikugan.ui.markdown`:

* :func:`_build_theme_styles` — returns a dict of inline-style
  fragments keyed by element.  ``source`` is an optional IDA source
  object (kept for parity with the legacy path; unused here).
* :class:`QtRenderer` — instantiable renderer with a single
  method, :meth:`QtRenderer.render_with_styles`.  The signature is
  ``render_with_styles(tokens, options, env, styles)`` so the
  caller can pass in a precomputed style map; the upstream
  default ``render(tokens, options, env)`` is provided too for
  parity with markdown-it conventions.
"""

from __future__ import annotations

import html as _html
from typing import Any


def _highlight(code: str, language: str) -> str:
    """Highlight *code* with *language* via the Pygments bridge.

    Imported lazily so this module does not require Pygments at
    import time.  Returns inline-styled HTML, or plain escaped
    text when Pygments / the language lexer is unavailable.
    """
    from .highlight import highlight_code

    if not language:
        return _html.escape(code)
    return highlight_code(code, language)


# ---------------------------------------------------------------------------
# Theme style builder
# ---------------------------------------------------------------------------


def _build_theme_styles(source: Any = None) -> dict[str, str]:
    """Return a dict of inline-style fragments for the active theme.

    The keys are stable identifiers used by :class:`QtRenderer` to
    pick the right CSS for each token.  ``source`` is accepted for
    API parity with the legacy converter but is otherwise ignored —
    the active palette is owned by :class:`ThemeManager`.
    """
    del source  # unused; kept for API parity
    from .styles import is_host_theme
    from .theme.manager import ThemeManager, _blend_hex

    if is_host_theme():
        # Minimal host-friendly defaults — Qt picks up the host's
        # QPalette for body text in most cases, so we just need
        # enough CSS for code spans and links.
        return {
            "inline_code_style": "font-family:monospace;",
            "block_code_style": (
                "font-family:monospace; white-space:pre-wrap; "
                "padding:6px; border-radius:3px;"
            ),
            "link_style": "text-decoration: underline;",
            "hr_style": "",
            "heading_style": "font-weight:bold;",
            "lang_tag_style": "font-size:10px;",
            "blockquote_style": (
                "border-left:3px solid #888; padding-left:8px; "
                "margin:4px 0; color:#666;"
            ),
            "table_style": "border-collapse:collapse;",
            "th_style": (
                "border:1px solid #888; padding:4px 6px; "
                "font-weight:bold; text-align:left;"
            ),
            "td_style": "border:1px solid #888; padding:4px 6px;",
            "strikethrough_style": "text-decoration:line-through;",
        }

    tokens = ThemeManager.instance().tokens()
    code_bg = _blend_hex(tokens.base, tokens.window, 0.15)
    inline_fg = _blend_hex(tokens.highlight, tokens.text, 0.3)
    border = _blend_hex(tokens.mid, tokens.window, 0.35)
    heading = _blend_hex(tokens.highlight, tokens.text, 0.15)
    muted_text = _blend_hex(tokens.text, tokens.window, 0.45)

    return {
        "inline_code_style": (
            f"background-color:{code_bg}; color:{inline_fg}; "
            "padding:1px 4px; border-radius:3px; "
            "font-family:monospace; font-size:12px;"
        ),
        "block_code_style": (
            f"background-color:{tokens.base}; color:{tokens.text}; "
            f"border:1px solid {border}; border-radius:4px; "
            "padding:8px; font-family:monospace; font-size:12px; "
            "white-space:pre-wrap; word-break:break-all;"
        ),
        "link_style": f"color:{tokens.highlight};",
        "hr_style": f"border:1px solid {border};",
        "heading_style": f"color:{heading}; font-weight:bold;",
        "lang_tag_style": f"color:{muted_text};font-size:10px;",
        "blockquote_style": (
            f"border-left:3px solid {border}; padding-left:8px; "
            f"margin:4px 0; color:{muted_text};"
        ),
        "table_style": "border-collapse:collapse;",
        "th_style": (
            f"border:1px solid {border}; padding:4px 6px; "
            f"font-weight:bold; text-align:left; color:{heading};"
        ),
        "td_style": f"border:1px solid {border}; padding:4px 6px;",
        "strikethrough_style": "text-decoration:line-through;",
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _attr(tok: Any, name: str, default: str = "") -> str:
    """Read ``tok.attrs[name]`` with a safe default.

    markdown-it exposes ``attrs`` as either a list of pairs
    (``[["href", "..."], ...]``) or, in newer versions, a dict.
    This helper accepts both shapes.
    """
    attrs = getattr(tok, "attrs", None)
    if attrs is None:
        return default
    if isinstance(attrs, dict):
        return attrs.get(name, default) or default
    # list-of-pairs
    for k, v in attrs:
        if k == name:
            return v or default
    return default


class QtRenderer:
    """Render a markdown-it token list to Qt-compatible HTML.

    ``md`` is the :class:`markdown_it.MarkdownIt` instance.  We do
    not use ``md.renderer`` — the upstream default is HTML with
    external CSS, which Qt cannot consume.  The instance is kept
    around so future hooks (e.g. custom token rules) can introspect
    it.
    """

    def __init__(self, md: Any) -> None:
        self.md = md
        # Active style map (set by ``render_with_styles`` so the
        # recursive helpers can reach it without threading the
        # argument through every call).
        self._styles: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        tokens: list[Any],
        options: Any,
        env: Any,
    ) -> str:
        """Default markdown-it entry point — falls back to
        computing styles on the fly from the active theme.
        """
        styles = _build_theme_styles()
        return self.render_with_styles(tokens, options, env, styles)

    def render_with_styles(
        self,
        tokens: list[Any],
        options: Any,
        env: Any,
        styles: dict[str, str],
    ) -> str:
        """Render *tokens* to HTML using *styles* for inline CSS."""
        del options, env  # unused — we drive off the token list
        self._styles = styles
        out: list[str] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            ttype = tok.type
            if ttype == "heading_open":
                level = int(tok.tag[1])  # tag is "h1" .. "h6"
                # Spec: heading_open, inline, heading_close
                inline_tok = tokens[i + 1]
                close_tok = tokens[i + 2]
                inner = self._render_inline(inline_tok.children or [])
                size = {1: 18, 2: 16, 3: 14, 4: 13, 5: 12, 6: 11}.get(level, 13)
                heading_style = (
                    f'{styles["heading_style"]}font-size:{size}px;'
                    "margin:6px 0 2px 0;"
                )
                out.append(
                    f'<div style="{_html.escape(heading_style, quote=True)}">'
                    f"{inner}</div>"
                )
                del close_tok  # structural; verified by parser
                i += 3
                continue
            if ttype == "paragraph_open":
                inline_tok = tokens[i + 1]
                inner = self._render_inline(inline_tok.children or [])
                # Trailing ``<br>`` preserves the legacy
                # behaviour where a blank line in the source
                # became a visible break between paragraphs
                # (the css ``margin:2px 0`` does the visual
                # gap; the ``<br>`` is the inline marker the
                # rest of the suite and older code keys on).
                out.append(f'<div style="margin:2px 0;">{inner}<br></div>')
                i += 3  # paragraph_open, inline, paragraph_close
                continue
            if ttype == "bullet_list_open":
                end = self._find_close(
                    tokens, i, "bullet_list_open", "bullet_list_close"
                )
                inner = self._render_list_items(tokens[i + 1 : end])
                out.append(
                    f"<ul style='margin:2px 0 2px 16px;'>{inner}</ul>"
                )
                i = end + 1
                continue
            if ttype == "ordered_list_open":
                end = self._find_close(
                    tokens, i, "ordered_list_open", "ordered_list_close"
                )
                inner = self._render_list_items(tokens[i + 1 : end])
                out.append(
                    f"<ol style='margin:2px 0 2px 16px;'>{inner}</ol>"
                )
                i = end + 1
                continue
            if ttype == "blockquote_open":
                end = self._find_close(
                    tokens, i, "blockquote_open", "blockquote_close"
                )
                inner = self._render_blocks(tokens[i + 1 : end])
                out.append(
                    f'<div style="{_html.escape(styles["blockquote_style"], quote=True)}">'
                    f"{inner}</div>"
                )
                i = end + 1
                continue
            if ttype == "fence":
                lang = ""
                info = (tok.info or "").strip()
                if info:
                    lang = info.split()[0]
                code = tok.content
                if lang:
                    body = _highlight(code, lang)
                    lang_tag = (
                        f'<div style="{_html.escape(styles["lang_tag_style"], quote=True)}">'
                        f"{_html.escape(lang)}</div>"
                    )
                else:
                    body = _html.escape(code)
                    lang_tag = ""
                out.append(
                    f'<div style="{_html.escape(styles["block_code_style"], quote=True)}">'
                    f"{lang_tag}{body}</div>"
                )
                i += 1
                continue
            if ttype == "code_block":
                # Indented code block. Render as a fenced block
                # with no language.
                out.append(
                    f'<div style="{_html.escape(styles["block_code_style"], quote=True)}">'
                    f"{_html.escape(tok.content)}</div>"
                )
                i += 1
                continue
            if ttype == "hr":
                hr_style = styles.get("hr_style", "")
                style_attr = (
                    f' style="{_html.escape(hr_style, quote=True)}"'
                    if hr_style
                    else ""
                )
                out.append(f"<hr{style_attr}>")
                i += 1
                continue
            if ttype == "html_block":
                # ``markdown-it`` already filtered any unsafe HTML
                # when configured with ``html: false``; emit it
                # verbatim so the user sees their raw markup.
                out.append(tok.content)
                i += 1
                continue
            if ttype == "table_open":
                end = self._find_close(tokens, i, "table_open", "table_close")
                inner = self._render_table(tokens[i + 1 : end])
                out.append(
                    f'<table style="{_html.escape(styles["table_style"], quote=True)}" '
                    f'border="0" cellpadding="0" cellspacing="0">{inner}</table>'
                )
                i = end + 1
                continue
            # Defensive fallback: skip unknown block tokens but
            # render any inline payload they carry.
            if getattr(tok, "children", None):
                out.append(self._render_inline(tok.children))
            i += 1
        return "".join(out)

    # ------------------------------------------------------------------
    # Block-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_close(
        tokens: list[Any],
        start: int,
        open_type: str,
        close_type: str,
    ) -> int:
        depth = 0
        for j in range(start, len(tokens)):
            if tokens[j].type == open_type:
                depth += 1
            elif tokens[j].type == close_type:
                depth -= 1
                if depth == 0:
                    return j
        # Unbalanced; return the last index so the caller does
        # not loop forever.
        return len(tokens) - 1

    def _render_blocks(self, tokens: list[Any]) -> str:
        """Render a sub-slice of block-level tokens.

        Used for blockquote bodies and similar nested contexts.
        """
        # Reuse the public entry point with the current styles.
        return self.render_with_styles(tokens, None, {}, self._styles)

    def _render_list_items(self, tokens: list[Any]) -> str:
        out: list[str] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok.type == "list_item_open":
                end = self._find_close(
                    tokens, i, "list_item_open", "list_item_close"
                )
                inner = self._render_list_item_body(tokens[i + 1 : end])
                out.append(f"<li>{inner}</li>")
                i = end + 1
                continue
            if getattr(tok, "children", None):
                out.append(self._render_inline(tok.children))
            i += 1
        return "".join(out)

    def _render_list_item_body(self, tokens: list[Any]) -> str:
        """Render the body of a ``<li>`` (may contain paragraphs,
        nested lists, code blocks, etc.)."""
        out: list[str] = []
        i = 0
        n = len(tokens)
        styles = self._styles
        while i < n:
            tok = tokens[i]
            ttype = tok.type
            if ttype == "paragraph_open":
                inline_tok = tokens[i + 1]
                inner = self._render_inline(inline_tok.children or [])
                out.append(inner)
                i += 3  # paragraph_open, inline, paragraph_close
                continue
            if ttype == "bullet_list_open":
                end = self._find_close(
                    tokens, i, "bullet_list_open", "bullet_list_close"
                )
                inner = self._render_list_items(tokens[i + 1 : end])
                out.append(
                    f"<ul style='margin:2px 0 2px 16px;'>{inner}</ul>"
                )
                i = end + 1
                continue
            if ttype == "ordered_list_open":
                end = self._find_close(
                    tokens, i, "ordered_list_open", "ordered_list_close"
                )
                inner = self._render_list_items(tokens[i + 1 : end])
                out.append(
                    f"<ol style='margin:2px 0 2px 16px;'>{inner}</ol>"
                )
                i = end + 1
                continue
            if ttype == "fence":
                lang = (tok.info or "").strip().split()[0]
                code = tok.content
                if lang:
                    body = _highlight(code, lang)
                    lang_tag = (
                        f'<div style="{_html.escape(styles["lang_tag_style"], quote=True)}">'
                        f"{_html.escape(lang)}</div>"
                    )
                else:
                    body = _html.escape(code)
                    lang_tag = ""
                out.append(
                    f'<div style="{_html.escape(styles["block_code_style"], quote=True)}">'
                    f"{lang_tag}{body}</div>"
                )
                i += 1
                continue
            if getattr(tok, "children", None):
                out.append(self._render_inline(tok.children))
            i += 1
        return "".join(out)

    def _render_table(self, tokens: list[Any]) -> str:
        """Render the inner tokens of a table block.

        Qt's rich text engine is happy with ``<tr>`` / ``<th>`` /
        ``<td>`` but does not honour ``<thead>`` / ``<tbody>``.
        We collapse both into a single row stream.
        """
        styles = self._styles
        out: list[str] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            ttype = tok.type
            if ttype == "tr_open":
                out.append("<tr>")
                i += 1
                continue
            if ttype == "tr_close":
                out.append("</tr>")
                i += 1
                continue
            if ttype == "th_open":
                inline_tok = tokens[i + 1]
                inner = self._render_inline(inline_tok.children or [])
                out.append(
                    f'<th style="{_html.escape(styles["th_style"], quote=True)}">{inner}</th>'
                )
                i += 3  # th_open, inline, th_close
                continue
            if ttype == "td_open":
                inline_tok = tokens[i + 1]
                inner = self._render_inline(inline_tok.children or [])
                out.append(
                    f'<td style="{_html.escape(styles["td_style"], quote=True)}">{inner}</td>'
                )
                i += 3  # td_open, inline, td_close
                continue
            # thead_open / tbody_open / etc — Qt drops these, skip.
            i += 1
        return "".join(out)

    # ------------------------------------------------------------------
    # Inline rendering — state-machine over ``inline`` children
    # ------------------------------------------------------------------

    _EM_OPEN = "em_open"
    _EM_CLOSE = "em_close"
    _STRONG_OPEN = "strong_open"
    _STRONG_CLOSE = "strong_close"
    _S_OPEN = "s_open"
    _S_CLOSE = "s_close"
    _LINK_OPEN = "link_open"
    _LINK_CLOSE = "link_close"
    _IMAGE = "image"
    _TEXT = "text"
    _CODE_INLINE = "code_inline"
    _SOFTBREAK = "softbreak"
    _HARDBREAK = "hardbreak"
    _HTML_INLINE = "html_inline"

    def _render_inline(self, children: list[Any]) -> str:
        """Render an ``inline`` token's children to HTML.

        ``markdown-it`` emits paired ``_open`` / ``_close`` tokens
        for emphasis, strong, strikethrough and links.  We walk
        the children linearly and track an *open-tag stack* so the
        matching closer does not re-emit the inner content.
        """
        styles = self._styles
        out: list[str] = []
        i = 0
        n = len(children)
        # Each entry is the *raw opener tag* (e.g. ``<i>``,
        # ``<b>``, ``<a ...>``).  The matching close token causes
        # us to pop the entry and emit the corresponding closing
        # tag.
        stack: list[str] = []
        while i < n:
            tok = children[i]
            ttype = tok.type
            if ttype == self._TEXT:
                out.append(_html.escape(tok.content))
            elif ttype == self._CODE_INLINE:
                out.append(
                    f'<span style="{_html.escape(styles["inline_code_style"], quote=True)}">'
                    f"{_html.escape(tok.content)}</span>"
                )
            elif ttype == self._SOFTBREAK:
                out.append(" ")
            elif ttype == self._HARDBREAK:
                out.append("<br>")
            elif ttype == self._EM_OPEN:
                out.append("<i>")
                stack.append("</i>")
            elif ttype == self._EM_CLOSE:
                if stack and stack[-1] == "</i>":
                    out.append(stack.pop())
            elif ttype == self._STRONG_OPEN:
                out.append("<b>")
                stack.append("</b>")
            elif ttype == self._STRONG_CLOSE:
                if stack and stack[-1] == "</b>":
                    out.append(stack.pop())
            elif ttype == self._S_OPEN:
                # Qt does not render ``<s>`` reliably; use a
                # styled span.
                out.append(
                    f'<span style="{_html.escape(styles["strikethrough_style"], quote=True)}">'
                )
                stack.append("</span>")
            elif ttype == self._S_CLOSE:
                if stack and stack[-1] == "</span>":
                    out.append(stack.pop())
            elif ttype == self._LINK_OPEN:
                href = _attr(tok, "href")
                title = _attr(tok, "title")
                title_attr = (
                    f' title="{_html.escape(title)}"' if title else ""
                )
                opener = (
                    f'<a style="{_html.escape(styles["link_style"], quote=True)}" '
                    f'href="{_html.escape(href, quote=True)}"{title_attr}>'
                )
                out.append(opener)
                stack.append("</a>")
            elif ttype == self._LINK_CLOSE:
                if stack and stack[-1] == "</a>":
                    out.append(stack.pop())
            elif ttype == self._IMAGE:
                # Images are not supported by Qt rich text — fall
                # back to a textual alt string so the user still
                # sees the intent.
                src = _attr(tok, "src")
                alt = tok.content
                out.append(
                    f"[image: {_html.escape(alt or src)}]"
                )
            elif ttype == self._HTML_INLINE:
                out.append(tok.content)
            else:
                # Unknown inline token — render its content as
                # text so we never drop information.
                if tok.content:
                    out.append(_html.escape(tok.content))
            i += 1
        # If the stack is non-empty (malformed input), close
        # everything cleanly so the produced HTML stays balanced.
        for close_tag in reversed(stack):
            out.append(close_tag)
        return "".join(out)
