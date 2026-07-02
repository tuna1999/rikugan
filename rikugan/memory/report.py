"""Report generation from the raw knowledge store.

This module has two halves:

* :func:`build_report_context` — pure data assembly. Selects the
  reportable records (verified / high-confidence / important tags),
  groups them into the section templates the plan specifies, and
  emits a Markdown-flavored "report pack" that is fed to the LLM.
  This half is unit-testable without any network calls.

* :func:`synthesize_report` — calls the configured provider with the
  ``REPORT_WRITER_PROMPT`` plus the report pack to obtain the final
  Markdown. Also writes the file under ``notes/reports/`` and
  ingests the report back into the store so it is retrievable.

The split is deliberate so ``/report`` can fail loud at the data
step (no records → friendly error) without wasting an LLM call.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from .ingest import ingest_report
from .notes import list_notes
from .paths import KnowledgePaths
from .raw_store import KnowledgeRawStore
from .schema import KnowledgeEntity, KnowledgeMemory, KnowledgeRelation

SUPPORTED_SCOPES: tuple[str, ...] = ("full", "executive", "technical", "iocs", "network")


# Important tags that always make the cut (per plan).
IMPORTANT_TAGS: frozenset[str] = frozenset(
    {
        "capability",
        "network",
        "c2",
        "persistence",
        "crypto",
        "ioc",
        "data_structure",
        "function_purpose",
    }
)


# Sections rendered for the ``full`` scope (others drop subsets).
_FULL_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "File Metadata",
    "Key Findings",
    "Capabilities",
    "Network Indicators",
    "Persistence",
    "Crypto/Encoding",
    "Key Functions",
    "Data Structures",
    "MITRE ATT&CK Mapping",
    "IOCs",
    "Open Questions",
    "Source Notes",
)


# Section labels mapped to tag subsets. Empty list → no records match.
_TAG_SECTIONS: dict[str, tuple[str, ...]] = {
    "Capabilities": ("capability",),
    "Network Indicators": ("network", "c2"),
    "Persistence": ("persistence",),
    "Crypto/Encoding": ("crypto",),
    "Key Functions": ("function_purpose",),
    "Data Structures": ("data_structure",),
}


# Each section is identified by a tag-membership filter. ``None`` means
# the section always renders (even if empty) so the LLM has the
# template. The LLM may rewrite any section freely.
@dataclass
class _ReportSection:
    title: str
    required_tags: tuple[str, ...] | None = None  # None = always render


_FULL_TEMPLATE: tuple[_ReportSection, ...] = tuple(
    _ReportSection("Executive Summary")
    if t == "Executive Summary"
    else _ReportSection("File Metadata")
    if t == "File Metadata"
    else _ReportSection("Key Findings")
    if t == "Key Findings"
    else _ReportSection(t, _TAG_SECTIONS.get(t))
    for t in _FULL_SECTIONS
)


_SCOPE_TEMPLATES: dict[str, tuple[_ReportSection, ...]] = {
    "full": _FULL_TEMPLATE,
    "executive": (
        _ReportSection("Executive Summary"),
        _ReportSection("Capabilities", _TAG_SECTIONS["Capabilities"]),
        _ReportSection("Network Indicators", _TAG_SECTIONS["Network Indicators"]),
        _ReportSection("IOCs", ("ioc",)),
    ),
    "technical": (
        _ReportSection("Technical Summary"),
        _ReportSection("Key Functions", _TAG_SECTIONS["Key Functions"]),
        _ReportSection("Data Structures", _TAG_SECTIONS["Data Structures"]),
        _ReportSection("Crypto/Encoding", _TAG_SECTIONS["Crypto/Encoding"]),
    ),
    "iocs": (
        _ReportSection("IOCs", ("ioc",)),
        _ReportSection("Network Indicators", _TAG_SECTIONS["Network Indicators"]),
    ),
    "network": (
        _ReportSection("Network Summary"),
        _ReportSection("Network Indicators", _TAG_SECTIONS["Network Indicators"]),
        _ReportSection("C2 Endpoints", ("c2",)),
    ),
}


@dataclass
class ReportContext:
    """Assembled evidence for the report-writer LLM call."""

    scope: str
    sections: dict[str, list[str]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    binary_id: str = ""
    idb_path: str = ""
    notes: list[str] = field(default_factory=list)  # raw markdown excerpts

    def to_prompt_text(self) -> str:
        """Render the context as a Markdown block for the writer prompt."""
        out: list[str] = []
        out.append(f"# Knowledge Report Pack — scope: {self.scope}")
        out.append("")
        out.append(
            f"Counts: {self.counts.get('memories', 0)} memories · "
            f"{self.counts.get('entities', 0)} entities · "
            f"{self.counts.get('relations', 0)} relations · "
            f"{self.counts.get('notes', 0)} notes"
        )
        out.append("")
        for title, items in self.sections.items():
            out.append(f"## {title}")
            if items:
                out.extend(items)
            else:
                out.append("_No records for this section._")
            out.append("")
        if self.notes:
            out.append("## Research Note Excerpts")
            out.append("")
            out.extend(self.notes[:5])
        return "\n".join(out).strip()

    def is_empty(self) -> bool:
        total = sum(len(v) for v in self.sections.values()) + len(self.notes)
        return total == 0


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------


def _record_passes_filter(memory: KnowledgeMemory) -> bool:
    """Return True for memories we want to surface in reports."""
    if memory.verified:
        return True
    if memory.confidence >= 0.65:
        return True
    if any(t.lower() in IMPORTANT_TAGS for t in (memory.tags or [])):
        return True
    return False


def _memory_matches_section(memory: KnowledgeMemory, tags: tuple[str, ...] | None) -> bool:
    if tags is None:
        return True  # section with no filter takes everything
    tags_lower = {t.lower() for t in tags}
    if any(t.lower() in tags_lower for t in (memory.tags or [])):
        return True
    # If a memory's type IS a tag (e.g. memory.type == "function_purpose"),
    # let it through — this is how ingest_exploration_finding tags records.
    if (memory.type or "").lower() in tags_lower:
        return True
    return False


def _format_memory_bullet(m: KnowledgeMemory) -> str:
    flag = " ✓" if m.verified else ""
    return f"- {m.title}{flag}: {m.content}"


def _format_entity_bullet(e: KnowledgeEntity) -> str:
    addr = f" @ {e.address}" if e.address else ""
    return f"- `{e.id}` ({e.type}){addr} — {e.name}"


def _format_relation_bullet(r: KnowledgeRelation) -> str:
    return f"- `{r.src}` → *{r.predicate}* → `{r.dst}`"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_report_context(
    store: KnowledgeRawStore,
    paths: KnowledgePaths,
    scope: str = "full",
    *,
    max_memories_per_section: int = 30,
    max_entities: int = 40,
    max_relations: int = 60,
) -> ReportContext:
    """Assemble a :class:`ReportContext` from the raw store.

    ``scope`` selects the template (see :data:`SUPPORTED_SCOPES`).
    Returns a context with an ``is_empty()`` flag so callers can
    short-circuit when the store has nothing to report.
    """
    scope_norm = (scope or "full").strip().lower()
    if scope_norm not in SUPPORTED_SCOPES:
        scope_norm = "full"
    template = _SCOPE_TEMPLATES[scope_norm]

    memories = [m for m in store.list_memories() if _record_passes_filter(m)]
    entities = store.list_entities()
    relations = store.list_relations()

    sections: dict[str, list[str]] = {}
    for sect in template:
        if sect.required_tags is None:
            # ``Executive Summary`` / ``File Metadata`` / ``Key Findings``
            # / ``Open Questions`` / ``Source Notes`` — we leave them
            # for the LLM to author. The pack still lists all reportable
            # memories in the first such section as a "facts at a glance"
            # block.
            if sect.title in ("Executive Summary", "Key Findings", "Open Questions", "Source Notes"):
                if sect.title == "Source Notes":
                    bullets = [
                        f"- `{m.id}` (type={m.type}, conf={m.confidence:.2f})"
                        for m in memories[:max_memories_per_section]
                    ]
                elif sect.title == "Key Findings":
                    bullets = [_format_memory_bullet(m) for m in memories[:max_memories_per_section]]
                else:
                    bullets = []  # writer will produce
                sections[sect.title] = bullets
            else:
                sections[sect.title] = []
            continue

        # Tag-filtered section
        items: list[str] = []
        # Memories
        mem_matches = [m for m in memories if _memory_matches_section(m, sect.required_tags)]
        for m in mem_matches[:max_memories_per_section]:
            items.append(_format_memory_bullet(m))
        # Entities (when the section implies "things of type X")
        ent_matches = [e for e in entities if e.type and e.type.lower() in {t.lower() for t in sect.required_tags}]
        for e in ent_matches[:max_entities]:
            items.append(_format_entity_bullet(e))
        sections[sect.title] = items

    # Always include a global relations + entities dump under the
    # technical sections, regardless of tag filter.
    for title in ("Technical Summary", "Network Summary", "C2 Endpoints", "Capabilities"):
        if title in sections:
            if title == "Technical Summary" or title == "Network Summary":
                sections[title] = (
                    sections.get(title, [])
                    + [f"### Entities ({len(entities)} total)"]
                    + [_format_entity_bullet(e) for e in entities[:max_entities]]
                    + [f"### Relations ({len(relations)} total)"]
                    + [_format_relation_bullet(r) for r in relations[:max_relations]]
                )

    # Note excerpts (research notes can be cited directly).
    notes: list[str] = []
    try:
        for n in list_notes(paths.notes_dir)[:5]:
            title = n.title or os.path.splitext(os.path.basename(n.path))[0]
            excerpt = (n.body or "").strip()
            if len(excerpt) > 600:
                excerpt = excerpt[:599].rstrip() + "…"
            notes.append(f"### {title}\n{excerpt}\n")
    except Exception:
        pass

    return ReportContext(
        scope=scope_norm,
        sections=sections,
        counts={
            "memories": len(memories),
            "entities": len(entities),
            "relations": len(relations),
            "notes": len(notes),
        },
        binary_id=paths.binary_id,
        idb_path=paths.idb_path,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def make_report_filename(now: datetime | None = None) -> str:
    """``report-YYYY-MM-DD-HHMM.md`` for the current local time."""
    n = now or datetime.now()
    return f"report-{n.strftime('%Y-%m-%d-%H%M')}.md"


def write_report_file(
    paths: KnowledgePaths,
    report_md: str,
    filename: str | None = None,
) -> str:
    """Persist *report_md* under ``notes/reports/`` and return the path."""
    paths.ensure()
    name = filename or make_report_filename()
    # Defense in depth: keep the file under reports/ no matter what
    # was passed in.
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", name) or make_report_filename()
    full = os.path.join(paths.reports_dir, safe_name)
    with open(full, "w", encoding="utf-8") as f:
        f.write(report_md)
    return full


def synthesize_report(
    store: KnowledgeRawStore,
    paths: KnowledgePaths,
    *,
    scope: str = "full",
    provider=None,
    config=None,
) -> tuple[ReportContext, str, str]:
    """End-to-end: assemble context, call the writer LLM, save the file.

    Returns ``(context, report_md, file_path)``. ``provider`` is the
    configured :class:`LLMProvider`; ``config`` is the live
    :class:`RikuganConfig` (used for temperature / max tokens).
    Raises when there is nothing to report or when synthesis fails.
    """
    from ..agents.report_writer import REPORT_WRITER_PROMPT

    context = build_report_context(store, paths, scope=scope)
    if context.is_empty():
        raise ValueError("no stored knowledge to report")

    if provider is None:
        raise ValueError("provider is required to synthesize the report")

    # Use the existing core.types.Message to call the provider. We
    # explicitly stay single-turn so the LLM is in plain "respond
    # with a Markdown document" mode.
    from ..core.types import Message, Role

    user_prompt = (
        f"Produce a **{scope}** scope report based on the Knowledge Report "
        f"Pack below. Follow the requested section structure. Cite specific "
        f"addresses and source IDs from the pack — do not invent details. "
        f"Distinguish between verified findings and hypotheses. Use "
        f"Markdown formatting.\n\n---\n\n{context.to_prompt_text()}"
    )

    system_prompt = REPORT_WRITER_PROMPT
    max_tokens = 4096
    temperature = 0.3
    if config is not None:
        try:
            temperature = float(getattr(config.provider, "temperature", 0.3) or 0.3)
        except (TypeError, ValueError):
            temperature = 0.3
        try:
            max_tokens = int(getattr(config.provider, "max_tokens", 4096) or 4096)
            max_tokens = max(1024, min(max_tokens, 8192))
        except (TypeError, ValueError):
            max_tokens = 4096

    response = provider.chat(
        messages=[Message(role=Role.USER, content=user_prompt)],
        temperature=temperature,
        max_tokens=max_tokens,
        system=system_prompt,
    )
    report_md = (response.content or "").strip()
    if not report_md:
        raise ValueError("LLM returned an empty report body")

    # Save and ingest
    file_path = write_report_file(paths, report_md)
    try:
        ingest_report(
            store,
            paths,
            report_path=file_path,
            slug=os.path.splitext(os.path.basename(file_path))[0],
            scope=context.scope,
            body_excerpt=report_md,
        )
    except Exception:
        # Best-effort — a write error should not undo the file.
        pass

    return context, report_md, file_path


__all__ = [
    "IMPORTANT_TAGS",
    "SUPPORTED_SCOPES",
    "ReportContext",
    "build_report_context",
    "make_report_filename",
    "synthesize_report",
    "write_report_file",
]
