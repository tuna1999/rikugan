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
