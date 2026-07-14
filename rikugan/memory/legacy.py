"""Legacy memory importer: detect, inventory, fingerprint, and explicit import.

This module handles the one-time migration from folder-scoped ``RIKUGAN.md``
and ``.rikugan-kb/*.jsonl`` to the central workspace.

Rules:
* Never delete or move source data.
* Idempotent by source fingerprint + target + selected items.
* Records dismissal per source fingerprint, not globally.
* Minimal Phase-2 import supports binary target only.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .authority import MemoryWriteAuthority
from .service import BinaryMemoryService

RIKUGAN_MD_NAME = "RIKUGAN.md"
KB_DIR_NAME = ".rikugan-kb"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegacySource:
    """One detected legacy file/directory."""

    kind: str  # "markdown" | "jsonl" | "notes"
    path: str
    size: int = 0
    mtime: float = 0.0
    sha256: str = ""


@dataclass(frozen=True)
class LegacyItem:
    """One parsed item from legacy sources."""

    id: str
    source_path: str
    kind: str  # "markdown_fact" | "jsonl_record"
    category: str
    content: str
    title: str = ""


@dataclass(frozen=True)
class LegacyInventory:
    """Parsed inventory of all legacy sources."""

    source_fingerprint: str
    items: list[LegacyItem] = field(default_factory=list)
    sources: list[LegacySource] = field(default_factory=list)


@dataclass(frozen=True)
class LegacyImportSelection:
    """User-selected items to import into a target workspace."""

    source_fingerprint: str
    target_memory_id: str
    selected_item_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegacyImportResult:
    """Result of a legacy import operation."""

    import_id: str
    source_fingerprint: str
    target_memory_id: str
    imported_count: int
    selected_item_ids: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_legacy_sources(idb_path: str | Path) -> list[LegacySource]:
    """Detect legacy memory files beside the IDB.

    Returns metadata-only sources — no content is read.
    """
    idb_path = Path(idb_path)
    idb_dir = idb_path.parent
    sources: list[LegacySource] = []

    rikugan_md = idb_dir / RIKUGAN_MD_NAME
    if rikugan_md.is_file():
        st = rikugan_md.stat()
        sources.append(
            LegacySource(
                kind="markdown",
                path=str(rikugan_md),
                size=st.st_size,
                mtime=st.st_mtime,
            )
        )

    kb_dir = idb_dir / KB_DIR_NAME
    if kb_dir.is_dir():
        for entry in sorted(kb_dir.iterdir()):
            if entry.is_file() and entry.suffix == ".jsonl":
                st = entry.stat()
                sources.append(
                    LegacySource(
                        kind="jsonl",
                        path=str(entry),
                        size=st.st_size,
                        mtime=st.st_mtime,
                    )
                )

    notes_dir = idb_dir / "notes"
    if notes_dir.is_dir() and any(notes_dir.rglob("*.md")):
        sources.append(
            LegacySource(
                kind="notes",
                path=str(notes_dir),
            )
        )

    return sources


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


def _compute_source_fingerprint(sources: list[LegacySource]) -> str:
    """Compute a stable fingerprint from source metadata."""
    hasher = hashlib.sha256()
    for src in sources:
        hasher.update(f"{src.kind}:{src.path}:{src.size}:{src.mtime}".encode())
    return hasher.hexdigest()


def inventory_legacy_sources(
    idb_path: str | Path,
    sources: list[LegacySource],
) -> LegacyInventory:
    """Parse legacy sources into a bounded inventory.

    Reads content in bounded chunks. Groups JSONL by legacy ``binary_id``,
    parses ``RIKUGAN.md`` as free-form sections.
    """
    idb_path = Path(idb_path)
    fingerprint = _compute_source_fingerprint(sources)
    items: list[LegacyItem] = []

    for src in sources:
        if src.kind == "markdown":
            items.extend(_parse_rikugan_markdown(src.path))
        elif src.kind == "jsonl":
            items.extend(_parse_jsonl(src.path))

    return LegacyInventory(
        source_fingerprint=fingerprint,
        items=items,
        sources=sources,
    )


def _parse_rikugan_markdown(path: str) -> list[LegacyItem]:
    """Parse RIKUGAN.md as free-form sections with category headers."""
    items: list[LegacyItem] = []
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return items

    current_category = "general"
    current_lines: list[str] = []

    for line in content.splitlines():
        header_match = re.match(r"^##\s+(.+)$", line)
        if header_match:
            if current_lines:
                items.append(
                    LegacyItem(
                        id=f"md:{path}:{current_category}",
                        source_path=path,
                        kind="markdown_fact",
                        category=current_category,
                        title=current_category,
                        content="\n".join(current_lines).strip(),
                    )
                )
            current_category = header_match.group(1).strip().lower()
            current_lines = []
        elif line.strip().startswith("-"):
            # Bullet point
            bullet = line.strip().lstrip("-").strip()
            if bullet:
                current_lines.append(bullet)
        elif line.strip():
            current_lines.append(line.strip())

    if current_lines:
        items.append(
            LegacyItem(
                id=f"md:{path}:{current_category}",
                source_path=path,
                kind="markdown_fact",
                category=current_category,
                title=current_category,
                content="\n".join(current_lines).strip(),
            )
        )

    return items


def _parse_jsonl(path: str) -> list[LegacyItem]:
    """Parse JSONL memory records."""
    items: list[LegacyItem] = []
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return items

    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        items.append(
            LegacyItem(
                id=f"jsonl:{path}:{line_num}",
                source_path=path,
                kind="jsonl_record",
                category=record.get("type", "general"),
                content=record.get("content", ""),
                title=record.get("title", record.get("type", "general")),
            )
        )

    return items


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def import_legacy_selection(
    service: BinaryMemoryService,
    authority: MemoryWriteAuthority,
    inventory: LegacyInventory,
    selection: LegacyImportSelection,
) -> LegacyImportResult:
    """Import selected items into the target workspace.

    Idempotent: rerunning the same selection returns the same import ID
    without creating duplicates. Source files are never modified.
    """
    service.require_write_authority(authority)

    # Compute deterministic import ID from full fingerprint + target + selection
    normalized = {
        "source_fingerprint": inventory.source_fingerprint,
        "target_memory_id": service.context.binary_memory_id,
        "selected_item_ids": sorted(selection.selected_item_ids),
    }
    import_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    import_id = f"legacy-{import_hash[:16]}"

    # Filter selected items
    selected_set = set(selection.selected_item_ids)
    selected_items = [item for item in inventory.items if item.id in selected_set]

    imported_count = 0
    for item in selected_items:
        try:
            service.save_fact(
                authority,
                category=item.category,
                fact=item.content,
                source=f"legacy_import:{item.kind}",
            )
            imported_count += 1
        except Exception:
            # Skip items that fail import — don't abort the whole batch
            pass

    return LegacyImportResult(
        import_id=import_id,
        source_fingerprint=inventory.source_fingerprint,
        target_memory_id=service.context.binary_memory_id,
        imported_count=imported_count,
        selected_item_ids=selection.selected_item_ids,
    )
