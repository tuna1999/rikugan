"""String listing and searching tools.

The string tools serve results from a persistent, on-disk raw cache
(see :mod:`rikugan.tools.string_cache`) instead of re-enumerating
``idautils.Strings()`` on every call.  The first call on a given IDB
performs a one-time build (which may take a while on huge binaries);
subsequent calls are served from the cache.  Pass ``refresh=True`` or
invoke :func:`refresh_string_cache` after redefining strings in IDA.
"""

from __future__ import annotations

import importlib
from typing import Annotated

from ...constants import STRING_CACHE_BUILD_TIMEOUT
from ...core.config import RikuganConfig
from ...core.logging import log_debug, log_warning
from ...core.sanitize import strip_injection_markers
from ...tools.base import parse_addr, tool
from ...tools.pagination import format_page
from ...tools.string_cache import (
    StringCacheIndex,
    StringRecord,
    get_existing_string_cache,
    get_or_build_string_cache,
)
from ...tools.string_cache import (
    refresh_string_cache as _refresh_string_cache_helper,
)

try:
    idautils = importlib.import_module("idautils")
    idc = importlib.import_module("idc")
except ImportError as e:
    log_debug(f"IDA modules not available: {e}")


# ---------------------------------------------------------------------------
# Cache wiring
# ---------------------------------------------------------------------------


def _config_factory() -> RikuganConfig:
    """Return the active ``RikuganConfig``.

    Default returns a fresh config that auto-derives ``cache_dir`` from the
    host user config base directory.  Tests / integrations that need an
    alternative config can monkey-patch :data:`_config_factory_override`.
    """
    factory = _config_factory_override
    if factory is not None:
        return factory()
    return RikuganConfig()


# Allow tests / non-default integrations to swap in a different config.
_config_factory_override = None


def _iter_ida_strings():
    """Yield ``(ea, length, text)`` records from ``idautils.Strings()``.

    Defensive: each iteration pulls text via ``str(s)`` so we never retain
    a reference to IDA's own string object after enumeration.
    """
    for s in idautils.Strings():
        try:
            text = str(s)
        except Exception:
            text = ""
        yield (int(s.ea), int(s.length), text)


def _ensure_cache(refresh: bool = False) -> StringCacheIndex | None:
    """Return a cache index, rebuilding if *refresh* is True.

    Wraps :func:`get_or_build_string_cache` / :func:`refresh_string_cache`
    so a cache failure degrades gracefully (returns ``None``).
    """
    factory = _iter_ida_strings
    cache_dir = _config_factory().cache_dir
    try:
        if refresh:
            return _refresh_string_cache_helper(factory, cache_dir)
        return get_or_build_string_cache(factory, cache_dir, refresh=False)
    except Exception as e:
        log_warning(f"String cache unavailable: {e}")
        return None


def _format_record_line(rec: StringRecord) -> str:
    return f"  0x{rec.ea:x}  [{rec.length}] {rec.text}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


# Custom timeout for first-time cache builds on huge binaries.  The default
# registry timeout is 30s, which is too tight for a cold string cache build.
_LIST_STRINGS_TIMEOUT = STRING_CACHE_BUILD_TIMEOUT
_SEARCH_STRINGS_TIMEOUT = STRING_CACHE_BUILD_TIMEOUT
_REFRESH_STRINGS_TIMEOUT = STRING_CACHE_BUILD_TIMEOUT


@tool(category="strings", timeout=_LIST_STRINGS_TIMEOUT)
def list_strings(
    offset: Annotated[int, "Start index"] = 0,
    limit: Annotated[int, "Max results"] = 50,
    refresh: Annotated[bool, "Force rebuild of the persistent string cache"] = False,
) -> str:
    """List defined strings in the binary with pagination.

    The first call on a given IDB builds a persistent on-disk cache (which
    may take a while for very large binaries).  Subsequent calls are served
    from the cache.  Pass ``refresh=True`` or call
    :func:`refresh_string_cache` after redefining strings so the cache
    reflects the new state.
    """

    cache = _ensure_cache(refresh=refresh)
    if cache is None:
        # Persistent cache unavailable — fall back to a direct enumeration
        # (no pagination guarantee for very large binaries, but this only
        # happens when no IDB identity is available, which is uncommon).
        # Sanitize the untrusted binary strings before returning to the LLM.
        records = list(_iter_ida_strings())
        rows = [
            f"  0x{ea:x}  [{length}] {strip_injection_markers(text)}"
            for (ea, length, text) in records
        ]
        out = format_page(rows, offset=offset, limit=limit, title="Strings")
        out += "\n  (no persistent cache — direct enumeration)"
        return out

    page, total = cache.list(offset=offset, limit=limit)
    rows = [_format_record_line(r) for r in page]
    # Preserve the historical ``title="Strings"`` header for backward
    # compatibility; cache status is appended as a suffix line instead.
    out = format_page(rows, offset=offset, limit=limit, title="Strings")
    out += f"\n  (served from persistent cache: {total} total)"
    if refresh and total:
        out += f"\n  String cache rebuilt: {total} strings indexed."
    return out


@tool(category="strings", timeout=_SEARCH_STRINGS_TIMEOUT)
def search_strings(
    query: Annotated[str, "Search substring (case-insensitive)"],
    limit: Annotated[int, "Max results"] = 20,
    refresh: Annotated[bool, "Force rebuild of the persistent string cache"] = False,
) -> str:
    """Search for strings containing the given substring.

    Uses the persistent n-gram-indexed cache.  Short queries (length < 3)
    fall back to a linear scan of the cached documents.  Pass
    ``refresh=True`` after redefining strings in IDA.
    """

    cache = _ensure_cache(refresh=refresh)
    if cache is None:
        # Direct fallback.  Sanitize before returning to the LLM.
        q = (query or "").lower()
        results: list[str] = []
        for ea, length, text in _iter_ida_strings():
            if q in text.lower():
                results.append(
                    f"  0x{ea:x}  [{length}] {strip_injection_markers(text)}"
                )
                if len(results) >= limit:
                    break
        if not results:
            return f"No strings matching '{query}'"
        return (
            f"Found {len(results)} string(s) (no persistent cache):\n"
            + "\n".join(results)
        )

    results = cache.search(query, limit=limit)
    if not results:
        return f"No strings matching '{query}'"
    body = "\n".join(_format_record_line(r) for r in results)
    return f"Found {len(results)} string(s):\n{body}"


@tool(category="strings")
def get_string_at(address: Annotated[str, "Address (hex string)"]) -> str:
    """Read the string at a specific address.

    Tries IDA's ``get_strlit_contents`` first to preserve exact behavior,
    then falls back to the persistent on-disk cache for cases where IDA
    returns nothing but the cache has a string at that address.  The cache
    fallback is read-only and will not trigger a cold rebuild.
    """

    ea = parse_addr(address)
    s = idc.get_strlit_contents(ea)
    if s is not None:
        try:
            return s.decode("utf-8", errors="replace")
        except Exception:
            return repr(s)

    # Read-only cache fallback: never build the cache on a direct miss.
    # If the cache does not exist yet, just report no string.
    cache_dir = _config_factory().cache_dir
    try:
        cache = get_existing_string_cache(cache_dir)
    except Exception as e:
        log_warning(f"String cache lookup failed: {e}")
        cache = None
    if cache is not None:
        rec = cache.get_at(ea)
        if rec is not None:
            return rec.text
    return f"No string at 0x{ea:x}"


@tool(category="strings", timeout=_REFRESH_STRINGS_TIMEOUT)
def refresh_string_cache() -> str:
    """Rebuild the persistent string cache for the active database.

    Call this after manually creating or redefining strings in IDA so the
    cache reflects the latest binary state.  Returns the rebuilt count.
    The cache is a host-internal artifact: no local filesystem path is
    exposed to the LLM.
    """

    cache = _ensure_cache(refresh=True)
    if cache is None:
        return (
            "Persistent string cache unavailable: no IDB identity. "
            "Strings will be enumerated directly."
        )
    return f"String cache rebuilt: {cache.total} strings indexed."


__all__ = [
    "get_string_at",
    "list_strings",
    "refresh_string_cache",
    "search_strings",
]
