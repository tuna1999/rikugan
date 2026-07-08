"""Offline IDAPython docs lookup — reads from bundled rikugan/data/idapython-docs/.

This is the runtime counterpart of scripts/build_idapython_docs.py. Once
the bundle is built and committed, this tool serves IDAPython docs to the
LLM agent with zero network dependency.

Replaces web_fetch(url=...python.docs.hex-rays.com/_sources/...) in
documentation fetches.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from ..core.errors import ToolError
from .base import tool

DOCS_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "idapython-docs"

#: Module names are [a-z0-9_]+ per spec. Reject anything else.
_MODULE_NAME_RE: re.Pattern[str] = re.compile(r"^[a-z0-9_]+$")

#: Default pagination — fits under TOOL_RESULT_TRUNCATE_LEN (~8000 chars).
DEFAULT_LIMIT: int = 7400
MAX_LIMIT: int = 7600


def _validate_module_name(module: str) -> str | None:
    """Return sanitized module name or None if invalid (path-traversal reject)."""
    if not module or not _MODULE_NAME_RE.match(module):
        return None
    return module


def _format_missing_module_error(module: str) -> str:
    """Build the user-facing error message when a module is not in the bundle."""
    available: list[str] = []
    if DOCS_DIR.is_dir():
        for p in sorted(DOCS_DIR.glob("*.rst.txt")):
            name = p.stem.removesuffix(".rst")
            if _validate_module_name(name):
                available.append(name)

    shown = ", ".join(available[:20])
    total = len(available)
    return (
        f"[Module '{module}' not found in offline bundle]\n"
        f"Available modules ({total}): {shown}"
        f"{'...' if total > 20 else ''}\n"
        f"Tip: run scripts/build_idapython_docs.py to refresh, "
        f"or fall back to web_fetch() for this module."
    )


@tool(
    name="lookup_idapython_doc",
    category="documentation",
    mutating=False,
    timeout=5.0,
)
def lookup_idapython_doc(
    module: Annotated[
        str,
        "Module name (e.g. 'ida_typeinf', 'idautils', 'ida_hexrays'). Must match `[a-z0-9_]+`.",
    ],
    offset: Annotated[int, "Character offset for pagination (0 = beginning)."] = 0,
    limit: Annotated[
        int,
        f"Max characters to return (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).",
    ] = DEFAULT_LIMIT,
) -> str:
    """Look up an IDAPython module's documentation from the bundled offline bundle.

    Reads from ``rikugan/data/idapython-docs/<module>.rst.txt`` — works
    without network access. Use this BEFORE web_fetch against
    python.docs.hex-rays.com because that site is bot-protected
    (403 Forbidden on deep-link HTML pages).

    Returns raw RST content (same format as Sphinx source files).
    Use ``offset`` to paginate through large modules.
    """
    safe = _validate_module_name(module)
    if safe is None:
        return f"[Error] invalid module name: {module!r}"

    if offset < 0:
        offset = 0
    if limit < 1:
        limit = 1
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT

    file_path = DOCS_DIR / f"{safe}.rst.txt"
    if not file_path.is_file():
        return _format_missing_module_error(safe)

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ToolError(
            f"Failed to read offline docs for {safe}: {exc}",
            tool_name="lookup_idapython_doc",
        ) from exc

    total_chars = len(content)
    if total_chars == 0:
        return f"[Offline IDAPython docs: {safe}; total chars: 0; showing offset 0-0]\n\n(empty response)"
    if offset >= total_chars:
        chunk = ""
    else:
        chunk = content[offset : offset + limit]

    header = (
        f"[Offline IDAPython docs: {safe}; total chars: {total_chars:,}; "
        f"showing offset {offset}-{min(offset + limit, total_chars)}]"
    )
    if not chunk:
        return f"{header}\n\n(reached end of content)"
    return f"{header}\n\n{chunk}"


__all__ = [
    "DEFAULT_LIMIT",
    "DOCS_DIR",
    "MAX_LIMIT",
    "lookup_idapython_doc",
]
