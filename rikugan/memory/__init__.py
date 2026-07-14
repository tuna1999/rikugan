"""Raw knowledge memory subsystem for Rikugan.

Stores structured analysis knowledge (memories, entities, relations,
observations) as JSONL files under ``<idb_dir>/.rikugan-kb/`` and
human-readable Markdown notes under ``<idb_dir>/notes/``.

.. deprecated::
    This folder-scoped JSONL subsystem is superseded by the central
    SQLite workspace store (``rikugan.memory.workspace_store``,
    ``rikugan.memory.repository``, ``rikugan.memory.service``).
    When ``config.memory_workspaces_enabled`` is True, all readers and
    writers should use the central service instead of this module's
    ``KnowledgeRawStore`` / ``knowledge_paths`` APIs. The legacy path
    remains active only for dark-mode backward compatibility.

This module is intentionally host-agnostic — the IDA-specific dispatch
and Qt widgets live elsewhere. Only I/O, parsing, ingestion, retrieval,
and report-context building happen here.

Storage layout
--------------
::

    <idb_dir>/
    ├── notes/
    │   ├── index.md
    │   ├── functions/
    │   ├── findings/
    │   ├── data-structures/
    │   ├── iocs.md
    │   └── reports/
    └── .rikugan-kb/
        ├── memories.jsonl
        ├── entities.jsonl
        ├── relations.jsonl
        ├── observations.jsonl
        └── meta.json
"""

from __future__ import annotations

from .paths import KnowledgePaths
from .raw_store import KnowledgeRawStore
from .schema import KnowledgeEntity, KnowledgeMemory, KnowledgeObservation, KnowledgeRelation

__all__ = [
    "KnowledgeEntity",
    "KnowledgeMemory",
    "KnowledgeObservation",
    "KnowledgePaths",
    "KnowledgeRawStore",
    "KnowledgeRelation",
]
