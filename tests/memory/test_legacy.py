"""Tests for legacy memory import: detection, inventory, fingerprint, import."""

from __future__ import annotations

import json
from pathlib import Path

from rikugan.memory.authority import MemoryAuthorityIssuer
from rikugan.memory.legacy import (
    LegacyImportSelection,
    detect_legacy_sources,
    import_legacy_selection,
    inventory_legacy_sources,
)
from rikugan.memory.markdown import MemoryProjector
from rikugan.memory.repository import SQLiteKnowledgeRepository
from rikugan.memory.service import BinaryMemoryService
from rikugan.memory.workspace import MemoryLocator, MemoryRunContext, new_memory_id
from rikugan.memory.workspace_store import WorkspaceStore


def _seed_legacy_sources(tmp_path: Path) -> Path:
    """Create a fake IDB directory with legacy RIKUGAN.md and .rikugan-kb/."""
    idb_dir = tmp_path / "sample"
    idb_dir.mkdir()
    idb_path = idb_dir / "sample.i64"
    idb_path.write_bytes(b"fake")

    # Legacy RIKUGAN.md
    rikugan_md = idb_dir / "RIKUGAN.md"
    rikugan_md.write_text(
        "# Rikugan Memory\n\n## algorithm\n\n- Uses RC4 for C2 traffic.\n\n## protocol\n\n- Sends data over HTTP.\n",
        encoding="utf-8",
    )

    # Legacy JSONL
    kb_dir = idb_dir / ".rikugan-kb"
    kb_dir.mkdir()
    (kb_dir / "memories.jsonl").write_text(
        json.dumps(
            {
                "id": "mem:algorithm:rc4:abc123",
                "binary_id": "sample",
                "type": "algorithm",
                "title": "RC4",
                "content": "Uses RC4 for C2",
                "confidence": 0.8,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return idb_path


class TestDetectLegacySources:
    def test_detect_finds_rikugan_md_and_kb(self, tmp_path: Path) -> None:
        idb_path = _seed_legacy_sources(tmp_path)
        sources = detect_legacy_sources(idb_path)
        assert len(sources) == 2

    def test_detect_returns_empty_for_clean_dir(self, tmp_path: Path) -> None:
        idb_path = tmp_path / "clean.i64"
        idb_path.write_bytes(b"fake")
        sources = detect_legacy_sources(idb_path)
        assert sources == []


class TestInventoryLegacySources:
    def test_inventory_parses_rikugan_md_and_jsonl(self, tmp_path: Path) -> None:
        idb_path = _seed_legacy_sources(tmp_path)
        sources = detect_legacy_sources(idb_path)
        inventory = inventory_legacy_sources(idb_path, sources)
        assert len(inventory.items) > 0

    def test_inventory_fingerprint_is_stable(self, tmp_path: Path) -> None:
        idb_path = _seed_legacy_sources(tmp_path)
        sources = detect_legacy_sources(idb_path)
        inv1 = inventory_legacy_sources(idb_path, sources)
        inv2 = inventory_legacy_sources(idb_path, sources)
        assert inv1.source_fingerprint == inv2.source_fingerprint


class TestImportLegacySelection:
    def test_import_creates_facts_and_is_idempotent(self, tmp_path: Path) -> None:
        idb_path = _seed_legacy_sources(tmp_path)
        sources = detect_legacy_sources(idb_path)
        inventory = inventory_legacy_sources(idb_path, sources)

        # Create a target workspace
        memory_id = new_memory_id()
        context = MemoryRunContext(memory_id, "", 1, 0)
        paths = MemoryLocator(tmp_path / "memory").binary(memory_id)
        store = WorkspaceStore.create(paths, owner_memory_id=memory_id)
        repo = SQLiteKnowledgeRepository(store, owner_memory_id=memory_id)
        issuer = MemoryAuthorityIssuer()
        service = BinaryMemoryService(
            context=context,
            paths=paths,
            repository=repo,
            store=store,
            projector=MemoryProjector(),
            authority_issuer=issuer,
        )

        selection = LegacyImportSelection(
            source_fingerprint=inventory.source_fingerprint,
            target_memory_id=memory_id,
            selected_item_ids=tuple(item.id for item in inventory.items),
        )

        authority = issuer.issue(context)
        result1 = import_legacy_selection(service, authority, inventory, selection)
        assert result1.imported_count > 0

        # Rerun same selection → idempotent
        result2 = import_legacy_selection(service, authority, inventory, selection)
        assert result2.imported_count == result1.imported_count
        assert result2.import_id == result1.import_id

    def test_source_untouched_after_import(self, tmp_path: Path) -> None:
        idb_path = _seed_legacy_sources(tmp_path)
        before = (idb_path.parent / "RIKUGAN.md").read_text(encoding="utf-8")

        sources = detect_legacy_sources(idb_path)
        inventory = inventory_legacy_sources(idb_path, sources)

        memory_id = new_memory_id()
        context = MemoryRunContext(memory_id, "", 1, 0)
        paths = MemoryLocator(tmp_path / "memory").binary(memory_id)
        store = WorkspaceStore.create(paths, owner_memory_id=memory_id)
        repo = SQLiteKnowledgeRepository(store, owner_memory_id=memory_id)
        issuer = MemoryAuthorityIssuer()
        service = BinaryMemoryService(
            context=context,
            paths=paths,
            repository=repo,
            store=store,
            projector=MemoryProjector(),
            authority_issuer=issuer,
        )

        selection = LegacyImportSelection(
            source_fingerprint=inventory.source_fingerprint,
            target_memory_id=memory_id,
            selected_item_ids=tuple(item.id for item in inventory.items),
        )
        import_legacy_selection(service, issuer.issue(context), inventory, selection)

        after = (idb_path.parent / "RIKUGAN.md").read_text(encoding="utf-8")
        assert before == after
