"""Pygments-based syntax highlighting for fenced code blocks.

Gracefully degrades when Pygments is not installed.
Output targets Qt RichText compatible HTML (inline styles only).
"""

from __future__ import annotations

import html as _html

_HAS_PYGMENTS = False
try:
    from pygments import highlight as _pygments_highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound

    _HAS_PYGMENTS = True
except ImportError:
    pass

# Cached formatters per style name (lazy singletons)
_formatter_cache: dict[str, HtmlFormatter | None] = {}


def _pygments_style_for_tokens(tokens) -> str:
    """Return the pygments style name for a given token set.

    Uses luminance check (not mode name) so that IDA_NATIVE in a light
    IDA theme also gets a light code style. The bug this fixes: pre-
    theme-system, code highlighting used monokai whenever the mode was
    'dark', but in IDA Native + Light IDA theme, monokai clashes with
    the light background.
    """
    from .theme.tokens import is_dark_tokens

    return "monokai" if is_dark_tokens(tokens) else "default"


def _get_formatter(style_name: str) -> HtmlFormatter | None:
    """Get (or create) a pygments HtmlFormatter for the given style.

    Cache is keyed by style name. Invalidate on theme change via
    ``clear_formatter_cache()``. Returns ``None`` when pygments is not
    installed so callers can degrade gracefully.
    """
    if not _HAS_PYGMENTS:
        return None
    if style_name not in _formatter_cache:
        try:
            _formatter_cache[style_name] = HtmlFormatter(
                style=style_name,
                nowrap=True,
                noclasses=True,
                nobackground=True,
            )
        except Exception:
            # Bad style name or pygments internal error — degrade to None
            # so highlight_code can fall back to plain text.
            _formatter_cache[style_name] = None
    return _formatter_cache[style_name]


def clear_formatter_cache() -> None:
    """Clear the pygments formatter cache. Call on theme change."""
    _formatter_cache.clear()


def highlight_code(code: str, language: str, is_dark: bool | None = None) -> str:
    """Highlight *code* in *language* using Pygments.

    Returns HTML with inline styles suitable for Qt RichText.
    Falls back to HTML-escaped plain text when Pygments is absent
    or the language is unknown.

    ``is_dark`` is optional — when omitted, the active theme's tokens
    drive the style choice (this is the recommended path; passing
    ``is_dark`` directly is kept for backward compatibility).
    """
    if not _HAS_PYGMENTS or not language:
        return _plain_code(code)

    if is_dark is None:
        # Defer the import to avoid a hard dependency from this module
        # on the theme manager at import time.
        from .theme.manager import ThemeManager
        from .theme.tokens import is_dark_tokens

        is_dark = is_dark_tokens(ThemeManager.instance().tokens())

    style_name = "monokai" if is_dark else "default"
    formatter = _get_formatter(style_name)
    if formatter is None:
        return _plain_code(code)

    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        # Try common aliases for RE context
        alias_map = {
            "asm": "nasm",
            "x86": "nasm",
            "arm": "asm",
            "objective-c": "objc",
            "shell": "bash",
            "conf": "ini",
        }
        mapped = alias_map.get(language.lower())
        if mapped:
            try:
                lexer = get_lexer_by_name(mapped)
            except ClassNotFound:
                return _plain_code(code)
        else:
            return _plain_code(code)

    highlighted = _pygments_highlight(code, lexer, formatter)
    return highlighted


def _plain_code(code: str) -> str:
    """Return HTML-escaped code for fallback rendering."""
    return _html.escape(code)


# === Theme change subscription ===
#
# Subscribe to ThemeManager.themeChanged at module load time. The signal
# payload is ignored — we only care that the cache is invalidated when
# the user (or IDAThemeWatcher) switches themes. Re-subscribing on each
# import is safe: highlight.py is imported at most once per process, and
# the ThemeManager singleton is reset between tests via ThemeManager.reset()
# which drops the prior manager instance. Any new instance() call returns
# a fresh QObject with no connections, so the module-level connect runs
# against whichever manager is alive at import time. If highlight.py is
# re-imported under a fresh manager (e.g. after reset() in a test
# setUp), the connect runs again against the new instance.

def _on_theme_changed(_tokens) -> None:
    clear_formatter_cache()


try:
    from .theme.manager import ThemeManager

    ThemeManager.instance().themeChanged.connect(_on_theme_changed)
except Exception:
    # Defensive: if the theme manager cannot be imported here (e.g. a
    # partial install, a missing PySide6, or a circular import in an
    # unusual embedding), the cache simply won't auto-invalidate. The
    # manual ``clear_formatter_cache()`` path still works.
    pass
