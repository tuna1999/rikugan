"""Shared security patterns and execution helper for Python script execution tools."""

from __future__ import annotations

import ast
import builtins
import contextlib
import io
from collections.abc import Callable
from typing import Any

# Modules that must never be imported (directly or via __import__).
_BLOCKED_MODULES = frozenset({"subprocess", "shlex", "pty", "commands"})

# Preserve the real __import__ before it gets removed from builtins.
_real_import = __import__


def _guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Replacement ``__import__`` that blocks modules in ``_BLOCKED_MODULES``.

    All other imports pass through to the real ``__import__`` untouched.
    This lets ``import os``, ``from Crypto.Cipher import AES``, etc. work
    normally inside ``exec()`` while still preventing ``import subprocess``.
    """
    root = name.split(".")[0]
    if root in _BLOCKED_MODULES:
        raise ImportError(f"import of disallowed module '{name}' is blocked")
    return _real_import(name, *args, **kwargs)

# Built-in calls that must never appear.
# NOTE: ``__import__()`` is no longer blocked here — it is handled at
# runtime by ``_guarded_import`` which validates the target module.
_BLOCKED_CALLS = frozenset({"exec", "eval", "compile"})

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
# reflective bypasses (e.g. __builtins__['__import__'], eval("os.system")).
# NOTE: ``__import__`` is NOT removed here — it is replaced with
# ``_guarded_import`` in ``safe_builtins()`` so that ``import`` statements
# still work inside ``exec()`` while blocked modules are caught at runtime.
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
    """Return a restricted ``__builtins__`` dict.

    Dangerous builtins (``exec``, ``eval``, ``compile``, …) are removed.
    ``__import__`` is *replaced* with ``_guarded_import`` so that regular
    ``import`` / ``from … import`` statements work inside ``exec()`` while
    blocked modules are still caught at runtime.
    """
    safe = {k: v for k, v in vars(builtins).items() if k not in _REMOVED_BUILTINS}
    safe["__import__"] = _guarded_import
    return safe


# Modules whose presence as a getattr() first argument is suspicious enough to
# block, even before the attribute name is known.  getattr(os, anything) is
# never legitimate for user-supplied scripts inside the guarded environment.
_GETATTR_BLOCKED_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shlex",
        "pty",
        "commands",
    }
)

# Attribute names that, if retrieved from any object via getattr, would expose
# a shell-execution primitive or break out of the sandbox.  Catches the inner
# half of nested getattr chains such as getattr(getattr(os, "popen"),
# "__call__").
_GETATTR_BLOCKED_ATTRS = frozenset(
    {
        "__import__",
        "__loader__",
        "__spec__",
        "__builtins__",
        "__call__",
        "system",
        "popen",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    }
)


def _check_getattr_bypass(node: ast.Call) -> str | None:
    """Return an error message if *node* is a getattr() reflective bypass.

    Recognises three patterns:

    1. ``getattr(os, 'system')(...)`` — direct call of a blocked module.
    2. ``getattr(os, 'popen')`` — used as a value (e.g. assigned, subscripted,
       or passed as an argument) so the call site can invoke it later.
    3. ``getattr(getattr(os, 'popen'), '__call__')(...)`` — nested chains
       where the outer getattr is a Name("getattr") and the first argument
       is itself a Call to ``getattr`` on a blocked module/attr.
    """
    if not isinstance(node, ast.Call):
        return None
    if not (isinstance(node.func, ast.Name) and node.func.id == "getattr"):
        return None
    if not node.args:
        return None

    first, second = node.args[0], (node.args[1] if len(node.args) > 1 else None)

    # Pattern 1 / 2: getattr(<module>, <attr>)
    if isinstance(first, ast.Name) and first.id in _GETATTR_BLOCKED_MODULES:
        return f"Blocked — reflective getattr on '{first.id}'"

    # Pattern 3: getattr(getattr(os, '<attr>'), '<attr>') or deeper nesting
    if isinstance(first, ast.Call) and len(first.args) >= 2:
        inner_first = first.args[0]
        if isinstance(inner_first, ast.Name) and inner_first.id in _GETATTR_BLOCKED_MODULES:
            return f"Blocked — nested reflective getattr on '{inner_first.id}'"
        if isinstance(inner_first, ast.Call) and len(inner_first.args) >= 2:
            deep_first = inner_first.args[0]
            if (isinstance(deep_first, ast.Name)
                    and deep_first.id in _GETATTR_BLOCKED_MODULES):
                return f"Blocked — deep nested reflective getattr on '{deep_first.id}'"

    # getattr(<anything>, '__import__' | 'system' | '__call__' | …)
    if isinstance(second, ast.Constant) and isinstance(second.value, str):
        if second.value in _GETATTR_BLOCKED_ATTRS:
            return f"Blocked — getattr access to dangerous attribute '{second.value}'"

    return None


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

            # Block: reflective getattr() bypass — getattr(os, 'system'),
            # getattr(subprocess, 'Popen'), getattr(sys, 'modules')['os'],
            # and nested chains like getattr(getattr(os, 'popen'), '__call__').
            getattr_block = _check_getattr_bypass(node)
            if getattr_block is not None:
                return getattr_block

        # Block: subscript access to __builtins__ (e.g. __builtins__['__import__'])
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                return "Blocked — direct subscript access to __builtins__"

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
        # Also replace __import__ with guarded version in pre-existing dicts
        ns_builtins["__import__"] = _guarded_import
    else:
        # Namespace has no __builtins__ at all (e.g. factory returned {}).
        # Inject safe_builtins() so import statements and __import__() work.
        namespace["__builtins__"] = safe_builtins()

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
