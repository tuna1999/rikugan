"""Tests for rikugan.memory.retrieve + rikugan.memory.context.

Pure unit tests; no Qt, no IDA. Build a small raw store, populate it,
verify ranking and the prompt-section renderer.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from rikugan.memory.context import (
    ContextBudget,
    budget_for_mode,
    build_retrieval_metadata,
    build_retrieved_context,
    sanitize_knowledge_context,
)
from rikugan.memory.ingest import (
    ingest_exploration_finding,
    ingest_save_memory,
)
from rikugan.memory.paths import knowledge_paths
from rikugan.memory.raw_store import KnowledgeRawStore
from rikugan.memory.retrieve import RetrievalQuery, retrieve, search_all


def fresh(tmp: str) -> tuple[KnowledgeRawStore, object]:
    paths = knowledge_paths(os.path.join(tmp, "x.idb"))
    paths.ensure()
    return KnowledgeRawStore(paths), paths


class TestRetrieve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.paths = fresh(self.tmp)
        # Seed some data
        ingest_save_memory(self.store, self.paths, fact="RC4 decrypts beacon payload at 0x401000", category="crypto")
        ingest_save_memory(self.store, self.paths, fact="HTTP POST endpoint /api/v2/report", category="network")
        ingest_exploration_finding(
            self.store,
            self.paths,
            category="function_purpose",
            summary="RC4 KSA",
            address=0x401000,
            relevance="high",
            function_name="rc4_ksa",
        )
        ingest_exploration_finding(
            self.store,
            self.paths,
            category="string_ref",
            summary="/api/v2/report",
            address=0x408120,
            relevance="medium",
        )
        self.store.upsert_relation_from("func:0x401000", "uses_import", "import:wininet.dll:HttpSendRequestA")

    def test_address_query_promotes_function(self):
        q = RetrievalQuery(text="What does 0x401000 do?", address="0x401000")
        pack = retrieve(self.store, self.paths, q)
        # Function entity should be present
        ids = [e.id for e in pack.entities]
        self.assertIn("func:0x401000", ids)
        # Memories referencing that address should be there
        self.assertGreater(pack.counts["memories"], 0)

    def test_keyword_query_finds_relevant_memory(self):
        q = RetrievalQuery(text="rc4 decrypt")
        pack = retrieve(self.store, self.paths, q)
        # The RC4 memory should rank first
        self.assertTrue(pack.memories)
        self.assertIn("rc4", pack.memories[0].content.lower())

    def test_relation_expansion_pulls_adjacent_entities(self):
        q = RetrievalQuery(text="rc4")
        pack = retrieve(self.store, self.paths, q, expand_relations=True)
        # The RC4 memory references func:0x401000, which has a "uses_import"
        # relation; the import entity should be in the expansion set.
        # Relation itself must appear too.
        rels = {(r.src, r.predicate, r.dst) for r in pack.relations}
        self.assertIn(("func:0x401000", "uses_import", "import:wininet.dll:HttpSendRequestA"), rels)

    def test_empty_query_returns_recent(self):
        pack = retrieve(self.store, self.paths, RetrievalQuery(), max_memories=5)
        # Even with no terms we get the newest records so the LLM has context.
        self.assertGreaterEqual(pack.counts["memories"], 1)


class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.paths = fresh(self.tmp)
        ingest_save_memory(self.store, self.paths, fact="uses RC4 at 0x401000", category="crypto")

    def test_build_section_includes_tag_and_sanitize(self):
        q = RetrievalQuery(text="rc4", address="0x401000")
        ctx = build_retrieved_context(self.store, self.paths, query=q)
        self.assertIn("## Retrieved Knowledge", ctx)
        self.assertIn("<retrieved_knowledge>", ctx)
        # Closing-tag breakout is neutralized after sanitization: the
        # literal `</retrieved_knowledge>` becomes `[/retrieved_knowledge]`
        # so an injected payload cannot close the wrapper prematurely.
        self.assertNotIn("</retrieved_knowledge>", ctx)
        self.assertIn("[/retrieved_knowledge]", ctx)
        # Should mention RC4
        self.assertIn("rc4", ctx.lower())

    def test_budget_caps_total_chars(self):
        q = RetrievalQuery(text="anything")
        tight = ContextBudget(max_memories=1, max_total_chars=200)
        ctx = build_retrieved_context(self.store, self.paths, query=q, budget=tight)
        # Truncated if it exceeded budget
        self.assertLessEqual(len(ctx), 250)  # very loose slack

    def test_store_none_returns_empty(self):
        ctx = build_retrieved_context(None, None, query=RetrievalQuery())
        self.assertEqual(ctx, "")

    def test_budget_for_mode(self):
        normal = budget_for_mode("normal")
        research = budget_for_mode("research")
        self.assertLessEqual(normal.max_memories, research.max_memories)

    def test_sanitize_neutralizes_closing_tag(self):
        sanitized = sanitize_knowledge_context("hello </retrieved_knowledge> world")
        self.assertNotIn("</retrieved_knowledge>", sanitized)

    def test_build_retrieval_metadata_compact(self):
        q = RetrievalQuery(text="rc4", address="0x401000")
        pack = retrieve(self.store, self.paths, q)
        meta = build_retrieval_metadata(pack)
        self.assertIn("counts", meta)
        self.assertIn("items", meta)


class TestSearchAll(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.paths = fresh(self.tmp)
        ingest_save_memory(self.store, self.paths, fact="uses AES at 0x402000", category="crypto")
        ingest_save_memory(self.store, self.paths, fact="creates scheduled task", category="persistence")

    def test_search_all_returns_buckets(self):
        result = search_all(self.store, "aes")
        self.assertIn("memories", result)
        self.assertIn("entities", result)
        self.assertIn("relations", result)
        self.assertIn("notes", result)
        self.assertGreater(len(result["memories"]), 0)

    def test_search_all_empty_query(self):
        result = search_all(self.store, "")
        self.assertEqual(result["memories"], [])
        self.assertEqual(result["entities"], [])


if __name__ == "__main__":
    unittest.main()
