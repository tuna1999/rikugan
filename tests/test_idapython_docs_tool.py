"""Unit tests for rikugan/tools/idapython_docs.py"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestLookupIdapythonDoc(unittest.TestCase):
    def setUp(self):
        # Create temp DOCS_DIR with 2 modules
        self.tmpdir = tempfile.mkdtemp()
        (Path(self.tmpdir) / "ida_typeinf.rst.txt").write_text(
            "ida_typeinf module docs\n\nFunctions:\n- apply_cdecl\n",
            encoding="utf-8",
        )
        (Path(self.tmpdir) / "idautils.rst.txt").write_text(
            "idautils module docs\n\nFunctions:\n- Functions\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _patch_docs_dir(self):
        return patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir))

    def test_reads_existing_module_returns_content(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with self._patch_docs_dir():
            result = lookup_idapython_doc("ida_typeinf")
        self.assertIn("apply_cdecl", result)
        self.assertIn("[Offline IDAPython docs: ida_typeinf", result)

    def test_path_traversal_rejected_dotdot(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with self._patch_docs_dir():
            result = lookup_idapython_doc("../../../etc/passwd")
        self.assertIn("invalid module name", result)

    def test_path_traversal_rejected_slash(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with self._patch_docs_dir():
            result = lookup_idapython_doc("foo/bar")
        self.assertIn("invalid module name", result)

    def test_path_traversal_rejected_uppercase(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with self._patch_docs_dir():
            result = lookup_idapython_doc("IDA_TYPEINF")
        self.assertIn("invalid module name", result)

    def test_path_traversal_rejected_dot(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with self._patch_docs_dir():
            result = lookup_idapython_doc(".")
        self.assertIn("invalid module name", result)

    def test_tool_does_not_read_outside_docs_dir(self):
        # Create a file outside the patched DOCS_DIR that the tool must NOT access
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        outside = Path(self.tmpdir).parent / "sensitive_outside.txt"
        outside.write_text("SENSITIVE")
        try:
            with self._patch_docs_dir():
                # Try every traversal pattern to reach sensitive_outside.txt
                result = lookup_idapython_doc("../sensitive_outside")
                # Must NOT contain SENSITIVE
                self.assertNotIn("SENSITIVE", result)
                self.assertIn("invalid module name", result)
        finally:
            outside.unlink()


class TestPaginationAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create one BIG module (~10000 chars) + one EMPTY module
        big = ("X" * 50 + "\n") * 200  # ~10000 chars
        (Path(self.tmpdir) / "big.rst.txt").write_text(big, encoding="utf-8")
        (Path(self.tmpdir) / "empty.rst.txt").write_text("", encoding="utf-8")
        # One with manifest missing
        # (No MANIFEST.json file written)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_pagination_first_chunk(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("big", offset=0, limit=200)
        self.assertIn("showing offset 0-200", result)

    def test_pagination_middle_chunk(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("big", offset=4000, limit=100)
        self.assertIn("showing offset 4000-4100", result)

    def test_pagination_past_end_returns_marker(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("big", offset=20000, limit=100)
        self.assertIn("reached end of content", result)

    def test_empty_file_returns_empty_marker(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("empty")
        self.assertIn("[Offline IDAPython docs: empty", result)
        self.assertIn("(empty response)", result)

    def test_limit_clamped_to_max(self):
        from rikugan.tools.idapython_docs import MAX_LIMIT, lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            # Request way over the max — must clamp to MAX_LIMIT
            result = lookup_idapython_doc("big", offset=0, limit=99999)
        # Header shows total file size ~10K so we see clamped chunk end
        self.assertIn(f"showing offset 0-{MAX_LIMIT}", result)

    def test_limit_below_one_clamped_to_one(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("big", offset=0, limit=0)
        # limit=0 -> clamp to 1 -> shows offset 0-1
        self.assertIn("showing offset 0-1", result)

    def test_offset_negative_clamped_to_zero(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("big", offset=-5, limit=100)
        self.assertIn("showing offset 0-100", result)

    def test_manifest_missing_does_not_break_tool(self):
        # No MANIFEST.json — tool should still work (manifest is informational)
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("big")
        self.assertIn("apply_cdecl" if "apply_cdecl" in result else "XXX", result)  # any content

    def test_zero_byte_file_does_not_crash(self):
        from rikugan.tools.idapython_docs import lookup_idapython_doc

        with patch("rikugan.tools.idapython_docs.DOCS_DIR", Path(self.tmpdir)):
            result = lookup_idapython_doc("empty")
        # Must not raise; must include "(empty response)" or similar
        self.assertIsInstance(result, str)
