"""Unit tests for the IDA docs reviewer prompt.

Task 10 of 13 (offline docs tool).  These tests pin the reviewer
prompt so that ``lookup_idapython_doc`` is the preferred doc source
and ``web_fetch`` is demoted to a fallback only.

Task 11 of 13 (offline docs tool).  Mirrors the same preference at the
SKILL.md level so the skill body recommends the offline tool first and
demotes ``web_fetch`` to a fallback.
"""

from __future__ import annotations

import unittest
from pathlib import Path


class TestReviewerPromptPrefersTool(unittest.TestCase):
    def test_prompt_mentions_lookup_idapython_doc(self):
        from rikugan.agent.agents.ida_docs_reviewer import IDA_DOCS_REVIEWER_PROMPT

        self.assertIn("lookup_idapython_doc", IDA_DOCS_REVIEWER_PROMPT)

    def test_prompt_demotes_web_fetch_to_fallback(self):
        from rikugan.agent.agents.ida_docs_reviewer import (
            build_ida_docs_reviewer_addendum,
        )

        prompt = build_ida_docs_reviewer_addendum()
        tool_idx = prompt.find("lookup_idapython_doc")
        self.assertGreater(tool_idx, -1, "lookup_idapython_doc not in prompt")
        # The first web_fetch occurrence after the tool entry should exist
        # (tool first → fallback later).
        web_fetch_idx = prompt.find("web_fetch", tool_idx) if tool_idx >= 0 else -1
        self.assertGreater(web_fetch_idx, -1, "web_fetch not in prompt after the tool")
        # Tool appears strictly before its fallback statement
        self.assertLess(tool_idx, web_fetch_idx)

    def test_prompt_explains_fallback_reason(self):
        from rikugan.agent.agents.ida_docs_reviewer import IDA_DOCS_REVIEWER_PROMPT

        # The fallback should mention "not in bundle" or similar
        lowered = IDA_DOCS_REVIEWER_PROMPT.lower()
        self.assertTrue(
            "not in bundle" in lowered or "fall back" in lowered,
            "Prompt should explain when to fall back to web_fetch",
        )


class TestSkillPrefersTool(unittest.TestCase):
    SKILL_PATH = (
        Path(__file__).resolve().parent.parent / "rikugan" / "skills" / "builtins" / "ida-scripting" / "SKILL.md"
    )

    def setUp(self):
        self.body = self.SKILL_PATH.read_text(encoding="utf-8")

    def test_skill_recommends_lookup_idapython_doc(self):
        self.assertIn("lookup_idapython_doc", self.body)

    def test_skill_demotes_web_fetch_to_fallback(self):
        tool_idx = self.body.find("lookup_idapython_doc")
        web_fetch_idx = self.body.find("web_fetch", tool_idx) if tool_idx >= 0 else -1
        self.assertGreater(tool_idx, -1)
        self.assertGreater(web_fetch_idx, -1)
        self.assertLess(tool_idx, web_fetch_idx)

    def test_skill_frontmatter_allows_lookup_idapython_doc(self):
        # Frontmatter allowed_tools must include lookup_idapython_doc — otherwise
        # rikugan/agent/loop.py:2058-2060 filters it out and the agent can't call it
        # even though the skill body recommends it.
        import yaml

        text = self.SKILL_PATH.read_text(encoding="utf-8")
        # Parse frontmatter (between --- markers)
        parts = text.split("---", 2)
        assert len(parts) >= 3, "frontmatter not found"
        fm = yaml.safe_load(parts[1])
        self.assertIn("lookup_idapython_doc", fm.get("allowed_tools", []))


if __name__ == "__main__":
    unittest.main()
