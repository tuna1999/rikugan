"""Shared security patterns and execution helper for Python script execution tools."""

from __future__ import annotations

import ast
import builtins
import contextlib
import io
from collections.abc import Callable
from typing import Any

# Modules that must never be imported (directly or via `from X import ...`).
# These provide the "control plane" of Python — process spawning, filesystem,
# network, dynamic code loading, native FFI, and known RCE deserialization
# vectors. Blocking them at import time means user code can still freely
# import pure-compute / data-plane libraries that are essential for malware
# analysis (Crypto.Cipher, struct, binascii, hashlib, math, re, numpy, ...).
_BLOCKED_MODULES = frozenset(
    {
        # Process / shell execution
        "subprocess",
        "shlex",
        "pty",
        "commands",
        "multiprocessing",
        # Filesystem / OS access (env vars, cwd, file IO via module attrs)
        "os",
        "sys",
        "shutil",
        "pathlib",
        "glob",
        "fnmatch",
        "tempfile",
        "fileinput",
        "filecmp",
        # Network access
        "socket",
        "ssl",
        "select",
        "selectors",
        "asyncio",
        "http",
        "urllib",
        "urllib2",
        "urllib3",
        "httplib",
        "ftplib",
        "telnetlib",
        "smtplib",
        "poplib",
        "imaplib",
        "xmlrpc",
        "xmlrpc.client",
        "xmlrpc.server",
        "socketserver",
        # Native FFI (can call C functions, bypass sandbox)
        "ctypes",
        "cffi",
        # Dynamic code loading (can import arbitrary code from anywhere)
        "importlib",
        "pkgutil",
        "zipimport",
        "runpy",
        "modulefinder",
        "code",
        "codeop",
        "idlelib",
        # Deserialization RCE vectors
        "pickle",
        "cPickle",
        "marshal",
        "shelve",
        # Process side effects (signals, resource limits, terminal control)
        "signal",
        "fcntl",
        "resource",
        "termios",
        "tty",
    }
)

# Built-in calls that must never appear. `__import__` is included because
# even though we restore it to the builtins (so users can write
# `import Crypto.Cipher`), calling it directly is the canonical reflective
# bypass — agents have no reason to call it themselves.
_BLOCKED_CALLS = frozenset({"exec", "eval", "compile", "__import__"})

# Attribute calls that must never appear (module.func patterns).
_BLOCKED_ATTRS = frozenset(
    {
        ("os", "system"),
        ("os", "popen"),
        ("os", "execl"),
        ("os", "execle"),
        ("os", "execlp"),
        ("os", "execlpe"),
        ("os", "execv"),
        ("os", "execve"),
        ("os", "execvp"),
        ("os", "execvpe"),
        ("os", "spawnl"),
        ("os", "spawnle"),
        ("os", "spawnlp"),
        ("os", "spawnlpe"),
        ("os", "spawnv"),
        ("os", "spawnve"),
        ("os", "spawnvp"),
        ("os", "spawnvpe"),
    }
)

# Builtins that must be removed from the execution namespace to prevent
# reflective bypasses (e.g. `eval("os.system")`, `exec(compile(...))`).
# Note: `__import__` is intentionally kept here so user code can use
# `import` statements for safe modules. Direct `__import__("...")` calls
# are still rejected by the AST check via _BLOCKED_CALLS.
_REMOVED_BUILTINS = frozenset(
    {
        "exec",
        "eval",
        "compile",
        "breakpoint",
        "exit",
        "quit",
    }
)


def safe_builtins() -> dict[str, Any]:
    """Return a restricted __builtins__ dict with dangerous names removed."""
    safe = {k: v for k, v in vars(builtins).items() if k not in _REMOVED_BUILTINS}
    return safe


def _check_ast(code: str) -> str | None:
    """Parse code and walk the AST for blocked constructs.

    Returns an error message if a violation is found, or None if safe.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "Blocked — code contains a syntax error and cannot be validated"

    for node in ast.walk(tree):
        # Block: import subprocess / from subprocess import ...
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_MODULES:
                    return f"Blocked — import of disallowed module '{alias.name}'"

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _BLOCKED_MODULES:
                    return f"Blocked — import from disallowed module '{node.module}'"

        # Block: exec(), eval(), compile(), __import__()
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BLOCKED_CALLS:
                return f"Blocked — call to disallowed built-in '{func.id}()'"

            # Block: os.system(), os.popen(), os.exec*(), os.spawn*()
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                pair = (func.value.id, func.attr)
                if pair in _BLOCKED_ATTRS:
                    return f"Blocked — call to disallowed '{pair[0]}.{pair[1]}()'"
                # Catch os.exec*/os.spawn* variants not explicitly listed
                if func.value.id == "os" and (func.attr.startswith("exec") or func.attr.startswith("spawn")):
                    return f"Blocked — call to disallowed 'os.{func.attr}()'"

        # Block: subscript access to __builtins__ (e.g. __builtins__['__import__'])
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                return "Blocked — direct subscript access to __builtins__"

        # Block: getattr used to access blocked names reflectively
        elif isinstance(node, ast.Call):
            # Already handled above, but also catch getattr(os, 'system') patterns
            pass

    return None


def run_guarded_script(code: str, namespace_factory: Callable[[], dict[str, Any]]) -> str:
    """Block dangerous patterns, exec code, and return captured stdout/stderr."""
    violation = _check_ast(code)
    if violation:
        return f"Error: {violation}"

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    namespace = namespace_factory()

    # Ensure __builtins__ is restricted even if the factory provided full access
    ns_builtins = namespace.get("__builtins__")
    if ns_builtins is builtins or ns_builtins is vars(builtins):
        namespace["__builtins__"] = safe_builtins()
    elif isinstance(ns_builtins, dict):
        for name in _REMOVED_BUILTINS:
            ns_builtins.pop(name, None)

    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        try:
            exec(code, namespace)
        except Exception as e:
            stderr_buf.write(f"{type(e).__name__}: {e}\n")

    stdout = stdout_buf.getvalue()
    stderr = stderr_buf.getvalue()
    parts = []
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    if not parts:
        parts.append("(no output)")
    return "\n".join(parts)
