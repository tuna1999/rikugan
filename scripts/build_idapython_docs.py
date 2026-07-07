"""Build the offline IDAPython docs bundle from Hex-Rays upstream.

Runs at dev/CI time (NOT inside IDA). Produces raw RST files + MANIFEST.json
under rikugan/data/idapython-docs/. See:
docs/superpowers/specs/2026-07-07-idapython-offline-docs-design.md
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants (no magic numbers; values from spec section Components)
#
# NOTE: This module is built up incrementally across tasks 1-6.  Only the
# constants and imports needed for the current task are present; later
# tasks (fetch/manifest/build/verify) will add urllib, hashlib, json, etc.
# ---------------------------------------------------------------------------

BASE_URL: str = "https://python.docs.hex-rays.com"
UPSTREAM_INDEX_URL: str = f"{BASE_URL}/"
SOURCES_URL_TEMPLATE: str = f"{BASE_URL}/_sources/{{module}}/index.rst.txt"

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
OUTPUT_DIR: Path = REPO_ROOT / "rikugan" / "data" / "idapython-docs"
MANIFEST_PATH: Path = OUTPUT_DIR / "MANIFEST.json"

MANIFEST_SCHEMA_VERSION: int = 1

HTTP_TIMEOUT_SECONDS: float = 30.0
MAX_RETRIES: int = 3
INITIAL_BACKOFF_SECONDS: float = 1.0
BACKOFF_MULTIPLIER: float = 2.0

# Module names are [a-z0-9_]+ per spec; we accept that here, and a Sphinx
# index page contains <a href="ida_typeinf/"> style entries.
_MODULE_LINK_RE: re.Pattern[str] = re.compile(r'<a\s+href="(?P<module>[a-z0-9_]+)/?"')


# ---------------------------------------------------------------------------
# HTML index parser — Task 1 deliverable
# ---------------------------------------------------------------------------


def discover_modules_from_index(html_content: str) -> list[str]:
    """Parse the Hex-Rays index page and return module names.

    Args:
        html_content: Raw HTML of https://python.docs.hex-rays.com/

    Returns:
        Sorted list of unique module names matching the Sphinx index
        pattern (e.g. ``["ida_name", "ida_typeinf", "idautils"]``).
        External URLs, fragments, and non-module hrefs are skipped.
    """
    modules = set(_MODULE_LINK_RE.findall(html_content))
    return sorted(modules)


__all__ = [
    "BACKOFF_MULTIPLIER",
    "BASE_URL",
    "HTTP_TIMEOUT_SECONDS",
    "INITIAL_BACKOFF_SECONDS",
    "MANIFEST_PATH",
    "MANIFEST_SCHEMA_VERSION",
    "MAX_RETRIES",
    "OUTPUT_DIR",
    "SOURCES_URL_TEMPLATE",
    "UPSTREAM_INDEX_URL",
    "discover_modules_from_index",
]
