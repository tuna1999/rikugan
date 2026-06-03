"""Tests for rikugan/tools/script_guard.py."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tests.mocks.ida_mock import install_ida_mocks
install_ida_mocks()

from rikugan.tools.script_guard import _check_ast, run_guarded_script


def _empty_ns():
    return {}


class TestCheckAst(unittest.TestCase):
    def test_blocks_subprocess(self):
        assert _check_ast("import subprocess") is not None

    def test_blocks_os_system(self):
        assert _check_ast("os.system('ls')") is not None

    def test_blocks_os_popen(self):
        assert _check_ast("os.popen('ls')") is not None

    def test_blocks_import_subprocess_via_dunder(self):
        # __import__() is no longer blocked at AST level — it is now handled
        # at runtime by _guarded_import.  Verify AST allows it through.
        assert _check_ast("__import__('subprocess')") is None

    def test_blocks_os_exec(self):
        assert _check_ast("os.execv('/bin/sh', [])") is not None

    def test_blocks_os_spawn(self):
        assert _check_ast("os.spawnl(0, '/bin/sh')") is not None

    def test_blocks_exec_call(self):
        assert _check_ast("exec('code')") is not None

    def test_blocks_eval_call(self):
        assert _check_ast("eval('1+1')") is not None

    def test_blocks_from_subprocess_import(self):
        assert _check_ast("from subprocess import Popen") is not None

    def test_blocks_syntax_error(self):
        assert _check_ast("def f(:\n    pass") is not None

    def test_allows_harmless_code(self):
        assert _check_ast("x = 1 + 2") is None

    def test_allows_print(self):
        assert _check_ast("print('hello')") is None

    def test_allows_os_path(self):
        assert _check_ast("os.path.join('a', 'b')") is None

    # ── Reflective / getattr bypass coverage ─────────────────────────────────
    # These tests guard against AST-level bypasses where an attacker wraps a
    # blocked module attribute behind getattr() to evade the syntactic checks
    # for `os.system()` / `os.popen()` / `__import__()` / etc.  Each of these
    # previously passed _check_ast() — see audit report P0 finding H1.

    def test_blocks_getattr_os_system(self):
        assert _check_ast("getattr(os, 'system')('cmd')") is not None

    def test_blocks_getattr_os_popen(self):
        assert _check_ast("getattr(os, 'popen')('cmd')") is not None

    def test_blocks_getattr_os_exec(self):
        assert _check_ast("getattr(os, 'execv')('/bin/sh', [])") is not None

    def test_blocks_getattr_os_spawn(self):
        assert _check_ast("getattr(os, 'spawnl')(0, '/bin/sh')") is not None

    def test_blocks_getattr_subprocess_module(self):
        # getattr is suspicious when used on the subprocess module name itself
        assert _check_ast("getattr(subprocess, 'Popen')(['ls'])"  # noqa: F821
                          ) is not None

    def test_blocks_getattr_sys_modules(self):
        # getattr on sys reaches every loaded module including os/subprocess
        assert _check_ast("getattr(sys, 'modules')['os']"  # noqa: F821
                          ) is not None

    def test_blocks_nested_getattr(self):
        # getattr(getattr(os, 'popen'), '__call__')('cmd')
        code = "getattr(getattr(os, 'popen'), '__call__')('cmd')"  # noqa: F821
        assert _check_ast(code) is not None

    def test_allows_getattr_on_safe_objects(self):
        # getattr on a benign value (a list attribute) must NOT be blocked
        assert _check_ast("x = [1, 2, 3]; y = getattr(x, 'append')"  # noqa: F841
                          ) is None

    def test_allows_getattr_with_string_literal_arg(self):
        # getattr(obj, 'attr') where obj is a Name not in the blocklist
        assert _check_ast("getattr(some_obj, 'some_attr')"  # noqa: F821
                          ) is None


class TestRunGuardedScript(unittest.TestCase):
    def test_blocked_subprocess(self):
        result = run_guarded_script("import subprocess", _empty_ns)
        assert result.startswith("Error: Blocked")
        assert "subprocess" in result

    def test_blocked_os_system(self):
        result = run_guarded_script("os.system('ls')", _empty_ns)
        assert "Blocked" in result

    def test_stdout_captured(self):
        result = run_guarded_script("print('hello')", _empty_ns)
        assert "hello" in result
        assert "stdout" in result

    def test_stderr_on_exception(self):
        result = run_guarded_script("raise ValueError('oops')", _empty_ns)
        assert "ValueError" in result
        assert "oops" in result
        assert "stderr" in result

    def test_no_output_placeholder(self):
        result = run_guarded_script("x = 1 + 2", _empty_ns)
        assert result == "(no output)"

    def test_namespace_provided_to_exec(self):
        ns_calls = []
        def ns_factory():
            d = {"captured": ns_calls}
            ns_calls.append("called")
            return d
        result = run_guarded_script("captured.append('exec')", ns_factory)
        assert "exec" in ns_calls
        assert result == "(no output)"

    def test_stdout_and_stderr_combined(self):
        code = "print('out'); raise RuntimeError('err')"
        result = run_guarded_script(code, _empty_ns)
        assert "stdout" in result
        assert "out" in result
        assert "stderr" in result
        assert "RuntimeError" in result

    def test_syntax_error_in_code(self):
        result = run_guarded_script("def f(:\n    pass", _empty_ns)
        assert "Error" in result

    def test_namespace_factory_called_fresh_each_time(self):
        calls = []
        def factory():
            calls.append(1)
            return {}
        run_guarded_script("x = 1", factory)
        run_guarded_script("y = 2", factory)
        assert len(calls) == 2

    # ── Import inside exec() — guarded_import allows safe modules ──────────

    def test_import_os_works(self):
        """``import os`` should succeed inside the guarded exec environment."""
        result = run_guarded_script("import os; print(os.name)", _empty_ns)
        assert "Error" not in result
        assert "stdout" in result

    def test_import_from_works(self):
        """``from os.path import join`` should succeed inside guarded exec."""
        result = run_guarded_script("from os.path import join; print(join('a', 'b'))", _empty_ns)
        assert "Error" not in result
        assert "a" in result
        assert "b" in result

    def test_dunder_import_blocked_subprocess_runtime(self):
        """``__import__('subprocess')`` passes AST but is caught by _guarded_import."""
        result = run_guarded_script("__import__('subprocess')", _empty_ns)
        assert "blocked" in result.lower() or "disallowed" in result.lower()

    def test_import_subprocess_blocked_runtime(self):
        """``import subprocess`` is still caught by AST check (first layer)."""
        result = run_guarded_script("import subprocess", _empty_ns)
        assert "Error" in result
        assert "subprocess" in result

    def test_dunder_import_blocked_shlex_runtime(self):
        """``__import__('shlex')`` is caught by _guarded_import at runtime."""
        result = run_guarded_script("__import__('shlex')", _empty_ns)
        assert "blocked" in result.lower() or "disallowed" in result.lower()

    def test_dunder_import_allows_safe_module(self):
        """``__import__('os')`` should succeed — 'os' is not in _BLOCKED_MODULES."""
        result = run_guarded_script("m = __import__('os'); print(m.name)", _empty_ns)
        assert "Error" not in result
        assert "stdout" in result


if __name__ == "__main__":
    unittest.main()
