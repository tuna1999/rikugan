# GitHub Release Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 36-line skeleton `.github/workflows/release.yml` with a full 3-job GitHub Actions pipeline (verify → build → publish) that produces a curated `rikugan-v{version}.zip`, `rikugan-v{version}.tar.gz`, and `SHA256SUMS` artifact for every tag push (or workflow_dispatch re-run).

**Architecture:** Three-job workflow chain. `verify` parses the tag, validates it matches `ida-plugin.json`, and re-runs the same CI checks that `ci.yml` would (ruff, mypy, pytest, desloppify) inline — bypassing the `ci.yml` branch drift. `build` runs `scripts/build_release.py` (a pure-Python module importable in tests) to assemble a curated archive of runtime files. `publish` uploads the artifacts via `softprops/action-gh-release@v2`, with pre-release flag auto-detected from the tag suffix.

**Tech Stack:** Python 3.11 (matches CI baseline, keeps `desloppify` objective score reproducible), `zipfile` + `tarfile` (stdlib), `softprops/action-gh-release@v2`, `actions/{checkout,setup-python,upload-artifact,download-artifact}@v4`, `ruff`/`mypy`/`pytest`/`desloppify` for inline re-run.

**Spec:** `docs/superpowers/specs/2026-06-18-github-release-pipeline-design.md`

## Global Constraints

- Python target version: `py311` (per `pyproject.toml [tool.ruff] target-version` and the project's CI baseline).
- Line length: `120` (per `pyproject.toml [tool.ruff] line-length`).
- All Python files start with `from __future__ import annotations` (project-wide rule from `AGENTS.md` §"Python Style").
- All functions have type hints (project-wide rule from `AGENTS.md`).
- The build script must produce archive filenames of the form `rikugan-v{version}.{zip,tar.gz}` and the archive root inside the zip must be `rikugan-v{version}/` (so `unzip rikugan-v1.2.3.zip && cd rikugan-v1.2.3 && ls` works).
- `SHA256SUMS` uses two-space separator between hash and filename (GNU coreutils convention; works with `sha256sum -c`).
- Workflow triggers must accept both `v*` tags (current convention) and bare `[0-9]*.[0-9]*` tags (legacy `1.0` style).
- Pre-release detection regex: `-(rc|alpha|beta|pre|dev)[0-9]*$`.
- `desloppify` objective score baseline: `89.0`, tolerance `0.5` (from `ci.yml` and `AGENTS.md`).
- GitHub tag-filter patterns are **glob**, not regex (GitHub docs). Patterns `[0-9]+` would not work; use `[0-9]*` instead.

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `scripts/__init__.py` | Create (empty) | Allows `from scripts.build_release import …` in tests |
| `scripts/build_release.py` | Create | The build script: collect files, build zip + tar.gz, write `SHA256SUMS` |
| `tests/scripts/__init__.py` | Create (empty) | Mirrors `tests/{agent,core,…}/__init__.py` pattern |
| `tests/scripts/test_build_release.py` | Create | Unit tests for the build script (12 tests, AAA pattern, pytest) |
| `.github/workflows/release.yml` | Rewrite | 3-job pipeline (verify → build → publish) |
| `AGENTS.md` | Edit | Update §"Release Flow" to describe the new pipeline |
| `DEVELOPMENT.md` | Edit | Update §"Release Process" with re-run + smoke-test instructions |
| `.gitignore` | Edit | Add `dist/` so local build output does not leak into git |

**Not touched:** `ci.yml` (drift fix is a separate concern), `install.sh` / `install.ps1` (`curl | bash` install path stays as is), `ida-plugin.json` schema, anything under `rikugan/`.

---

## Task 1: TDD `should_skip()` + `collect()`

**Files:**
- Create: `scripts/__init__.py` (empty)
- Create: `tests/scripts/__init__.py` (empty)
- Create: `scripts/build_release.py` (with `should_skip()` + `collect()`)
- Create: `tests/scripts/test_build_release.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `should_skip(path: Path) -> bool` — return `True` if `path` matches any exclude rule.
  - `collect(source_root: Path) -> list[Path]` — return sorted list of files (relative to `source_root`) that are in `INCLUDE_PATHS` and not excluded.

- [ ] **Step 1: Create empty `__init__.py` files for the new packages**

Create `scripts/__init__.py` (empty file, just a one-liner so editors don't complain):

```python
"""Build scripts for Rikugan release pipeline."""
```

Create `tests/scripts/__init__.py` (empty file, mirrors `tests/agent/__init__.py`):

```python
"""Tests for build scripts."""
```

- [ ] **Step 2: Write the failing tests**

Create `tests/scripts/test_build_release.py`:

```python
"""Unit tests for scripts/build_release.py.

AAA pattern. Uses pytest's ``tmp_path`` fixture to seed a fake repo
layout that mirrors the real project, then runs ``collect()`` /
``build_zip()`` / etc. and asserts on the output.
"""
from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.build_release import (
    EXCLUDE_NAMES,
    INCLUDE_PATHS,
    build_tar,
    build_zip,
    collect,
    sha256_file,
    should_skip,
    write_sha256sums,
)


# ── should_skip ────────────────────────────────────────────────────────


def test_should_skip_excludes_pycache_directory(tmp_path: Path) -> None:
    # Arrange
    p = tmp_path / "rikugan" / "core" / "__pycache__" / "config.cpython-311.pyc"

    # Act
    result = should_skip(p)

    # Assert
    assert result is True


def test_should_skip_excludes_dotfiles_in_path(tmp_path: Path) -> None:
    # Arrange
    p = tmp_path / ".venv" / "lib" / "foo.py"

    # Act
    result = should_skip(p)

    # Assert
    assert result is True


def test_should_skip_excludes_pyc_suffix(tmp_path: Path) -> None:
    # Arrange
    p = tmp_path / "rikugan" / "core" / "config.pyc"

    # Act
    result = should_skip(p)

    # Assert
    assert result is True


def test_should_skip_allows_normal_file(tmp_path: Path) -> None:
    # Arrange
    p = tmp_path / "rikugan" / "core" / "config.py"

    # Act
    result = should_skip(p)

    # Assert
    assert result is False


# ── collect ────────────────────────────────────────────────────────────


def _seed_fake_repo(root: Path) -> None:
    """Mimic the real repo layout: runtime files, dev files, junk files."""
    # Runtime files (must be included)
    (root / "rikugan_plugin.py").write_text("# plugin entry", encoding="utf-8")
    (root / "install.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (root / "install_ida.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (root / "install.ps1").write_text("# ps1\n", encoding="utf-8")
    (root / "install_ida.bat").write_text("@echo off\n", encoding="utf-8")
    (root / "requirements.txt").write_text("anthropic>=0.39.0\n", encoding="utf-8")
    (root / "ida-plugin.json").write_text('{"plugin":{"version":"1.2.3"}}\n', encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "README.md").write_text("# Rikugan\n", encoding="utf-8")
    # rikugan/ package (must be included, recursively)
    (root / "rikugan").mkdir()
    (root / "rikugan" / "__init__.py").write_text("", encoding="utf-8")
    (root / "rikugan" / "core").mkdir()
    (root / "rikugan" / "core" / "__init__.py").write_text("", encoding="utf-8")
    (root / "rikugan" / "core" / "config.py").write_text("# config\n", encoding="utf-8")
    # rikugan/skills/builtins/ subdir (real plugin loads from here)
    (root / "rikugan" / "skills").mkdir()
    (root / "rikugan" / "skills" / "builtins").mkdir()
    (root / "rikugan" / "skills" / "builtins" / "ctf").mkdir()
    (root / "rikugan" / "skills" / "builtins" / "ctf" / "SKILL.md").write_text("# ctf\n", encoding="utf-8")
    # Junk that MUST be excluded
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text("# test\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "x.md").write_text("# doc\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (root / "ARCHITECTURE.md").write_text("# arch\n", encoding="utf-8")
    (root / "DEVELOPMENT.md").write_text("# dev\n", encoding="utf-8")
    (root / "llms.txt").write_text("# llms\n", encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github" / "workflows").mkdir()
    (root / ".github" / "workflows" / "ci.yml").write_text("# ci\n", encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "icon.png").write_bytes(b"\x89PNG")
    (root / "chat_examples").mkdir()
    (root / "chat_examples" / "example.md").write_text("# ex\n", encoding="utf-8")
    (root / "webpage").mkdir()
    (root / "webpage" / "index.html").write_text("<html/>\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("# toml\n", encoding="utf-8")
    (root / "uv.lock").write_text("# lock\n", encoding="utf-8")
    (root / "ci-local.sh").write_text("# ci script\n", encoding="utf-8")
    # Junk inside rikugan/ that MUST be excluded
    (root / "rikugan" / "core" / "__pycache__").mkdir()
    (root / "rikugan" / "core" / "__pycache__" / "config.cpython-311.pyc").write_bytes(b"PYC")
    (root / "rikugan" / ".mypy_cache").mkdir()
    (root / "rikugan" / ".mypy_cache" / "x.json").write_text("{}\n", encoding="utf-8")
    (root / "rikugan" / "core" / "leftover.pyc").write_bytes(b"PYC")


def test_collect_includes_runtime_files(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)

    # Act
    result = collect(tmp_path)

    # Assert: every INCLUDE_PATHS file appears in result
    included = {p.relative_to(tmp_path).as_posix() for p in result}
    for spec in INCLUDE_PATHS:
        if spec == "rikugan":
            # recursive — covered in other tests
            continue
        assert spec in included, f"expected {spec!r} in collect() output"


def test_collect_includes_nested_runtime_files(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)

    # Act
    result = collect(tmp_path)

    # Assert: nested files inside rikugan/ are present
    included = {p.relative_to(tmp_path).as_posix() for p in result}
    assert "rikugan/__init__.py" in included
    assert "rikugan/core/config.py" in included
    assert "rikugan/skills/builtins/ctf/SKILL.md" in included


def test_collect_excludes_tests_and_docs(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)

    # Act
    result = collect(tmp_path)

    # Assert
    included = {p.relative_to(tmp_path).as_posix() for p in result}
    assert "tests/test_x.py" not in included
    assert "docs/x.md" not in included
    assert "AGENTS.md" not in included
    assert "ARCHITECTURE.md" not in included
    assert "DEVELOPMENT.md" not in included
    assert "llms.txt" not in included


def test_collect_excludes_dev_assets_and_config(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)

    # Act
    result = collect(tmp_path)

    # Assert
    included = {p.relative_to(tmp_path).as_posix() for p in result}
    assert "assets/icon.png" not in included
    assert "chat_examples/example.md" not in included
    assert "webpage/index.html" not in included
    assert "pyproject.toml" not in included
    assert "uv.lock" not in included
    assert "ci-local.sh" not in included
    assert ".github/workflows/ci.yml" not in included


def test_collect_excludes_pycache_and_dotfiles(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)

    # Act
    result = collect(tmp_path)

    # Assert
    included = {p.relative_to(tmp_path).as_posix() for p in result}
    assert "rikugan/core/__pycache__/config.cpython-311.pyc" not in included
    assert "rikugan/core/leftover.pyc" not in included
    assert "rikugan/.mypy_cache/x.json" not in included


def test_collect_returns_sorted_output(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)

    # Act
    result = collect(tmp_path)

    # Assert
    rel = [p.relative_to(tmp_path).as_posix() for p in result]
    assert rel == sorted(rel)


def test_collect_handles_missing_specs_gracefully(tmp_path: Path) -> None:
    # Arrange: a bare-minimum repo with no rikugan/ package
    (tmp_path / "rikugan_plugin.py").write_text("#\n", encoding="utf-8")

    # Act
    result = collect(tmp_path)

    # Assert: doesn't crash; just collects what exists
    included = {p.relative_to(tmp_path).as_posix() for p in result}
    assert "rikugan_plugin.py" in included
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v`

Expected: every test fails with `ImportError: cannot import name 'should_skip' from 'scripts.build_release'` (or similar) — `scripts/build_release.py` does not exist yet.

- [ ] **Step 4: Implement `should_skip()` + `collect()`**

Create `scripts/build_release.py` with the constant definitions, `should_skip()`, and `collect()`. Leave `build_zip`, `build_tar`, `sha256_file`, `write_sha256sums`, `main` as `NotImplementedError` stubs for now (filled in Tasks 2 and 3):

```python
"""Build curated release archive for Rikugan IDA plugin.

Chỉ include runtime files cần để install và chạy plugin trong IDA:
- rikugan_plugin.py  (entry point)
- rikugan/           (Python package, loại __pycache__)
- install.sh, install_ida.sh, install.ps1, install_ida.bat
- requirements.txt
- ida-plugin.json
- LICENSE
- README.md

Không include: tests/, docs/, AGENTS.md, ARCHITECTURE.md, DEVELOPMENT.md,
llms.txt, .github/, assets/, chat_examples/, webpage/, pyproject.toml,
uv.lock, ci-local.sh, .git/, .venv/, .*_cache/, __pycache__/.

Usage:
    python scripts/build_release.py --version 1.2.3 --out-dir dist

Output:
    dist/rikugan-v1.2.3.zip
    dist/rikugan-v1.2.3.tar.gz
    dist/SHA256SUMS
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import tarfile
import zipfile
from pathlib import Path

# Tên file/dir cần include (paths tương đối so với source root).
INCLUDE_PATHS: list[str] = [
    "rikugan_plugin.py",
    "rikugan",  # toàn bộ package
    "install.sh",
    "install_ida.sh",
    "install.ps1",
    "install_ida.bat",
    "requirements.txt",
    "ida-plugin.json",
    "LICENSE",
    "README.md",
]

# File/dir KHÔNG được include dù nằm trong INCLUDE_PATHS (match bất kỳ path part nào).
EXCLUDE_NAMES: set[str] = {
    "__pycache__",
    ".git",
    ".venv",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".desloppify",
    ".codegraph",
    ".reasonix",
    ".claude",
    "node_modules",
}

# File suffix KHÔNG được include.
EXCLUDE_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo", ".pyd")


def should_skip(path: Path) -> bool:
    """Return True nếu path nên bị skip (exclude rule match)."""
    if any(part in EXCLUDE_NAMES for part in path.parts):
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def collect(source_root: Path) -> list[Path]:
    """Collect tất cả files trong INCLUDE_PATHS, áp dụng exclude rules.

    Returns:
        Sorted list of absolute paths to files (absolute paths, not
        relative to ``source_root`` — the caller uses
        ``Path.relative_to(source_root)`` if it needs that).
    """
    collected: list[Path] = []
    for spec in INCLUDE_PATHS:
        src = source_root / spec
        if src.is_file():
            if not should_skip(src):
                collected.append(src)
        elif src.is_dir():
            for p in src.rglob("*"):
                if p.is_file() and not should_skip(p):
                    collected.append(p)
        # Nếu spec không tồn tại → silently skip
    return sorted(collected)


# ── Stubs filled in by Tasks 2 and 3 ─────────────────────────────────


def build_zip(files: list[Path], out_path: Path, arcname_root: str) -> None:
    """Build zip archive với tất cả files, prefix bằng arcname_root."""
    raise NotImplementedError


def build_tar(files: list[Path], out_path: Path, arcname_root: str) -> None:
    """Build tar.gz archive với tất cả files, prefix bằng arcname_root."""
    raise NotImplementedError


def sha256_file(path: Path) -> str:
    """Compute SHA256 hex digest của file."""
    raise NotImplementedError


def write_sha256sums(paths: list[Path], out_path: Path) -> None:
    """Write SHA256SUMS file (GNU coreutils format)."""
    raise NotImplementedError


def main() -> int:
    """CLI entry point. See module docstring."""
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v`

Expected: all 11 tests in this file pass. The `build_zip`/`build_tar`/`sha256_file`/`write_sha256sums` stubs are imported but not yet called by any of these tests, so the `NotImplementedError` is fine.

- [ ] **Step 6: Run `./ci-local.sh` to confirm no regressions**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && ./ci-local.sh`

Expected: ALL PASSED. The new `scripts/build_release.py` and `tests/scripts/test_build_release.py` are outside `rikugan/` (so ruff format/lint skip them) and not in the mypy or desloppify scopes. The new tests should be picked up by pytest if `tests/scripts/` is in the test root. Verify pytest actually ran them (the output should list 11 passes under `tests/scripts/test_build_release.py`).

- [ ] **Step 7: Commit**

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git add scripts/__init__.py tests/scripts/__init__.py scripts/build_release.py tests/scripts/test_build_release.py
git commit -m "feat(scripts): add build_release.py with collect() (TDD)"
```

---

## Task 2: TDD `build_zip()` + `build_tar()`

**Files:**
- Modify: `scripts/build_release.py` (replace `NotImplementedError` stubs)
- Modify: `tests/scripts/test_build_release.py` (append new tests)

**Interfaces:**
- Consumes: `files: list[Path]`, `out_path: Path`, `arcname_root: str` (e.g. `"rikugan-v1.2.3"`)
- Produces: writes `out_path`; archive root inside is `arcname_root/...`

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_build_release.py`:

```python
# ── build_zip / build_tar ─────────────────────────────────────────────


def test_build_zip_creates_valid_archive(tmp_path: Path) -> None:
    # Arrange
    files = [
        tmp_path / "a.txt",
        tmp_path / "sub" / "b.txt",
    ]
    files[0].write_text("hello", encoding="utf-8")
    files[1].parent.mkdir()
    files[1].write_text("world", encoding="utf-8")
    out = tmp_path / "out.zip"

    # Act
    build_zip(files, out, "rikugan-v1.0")

    # Assert
    assert out.is_file()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert "rikugan-v1.0/a.txt" in names
    assert "rikugan-v1.0/sub/b.txt" in names


def test_build_tar_creates_valid_archive(tmp_path: Path) -> None:
    # Arrange
    files = [
        tmp_path / "a.txt",
        tmp_path / "sub" / "b.txt",
    ]
    files[0].write_text("hello", encoding="utf-8")
    files[1].parent.mkdir()
    files[1].write_text("world", encoding="utf-8")
    out = tmp_path / "out.tar.gz"

    # Act
    build_tar(files, out, "rikugan-v1.0")

    # Assert
    assert out.is_file()
    with tarfile.open(out) as tf:
        names = tf.getnames()
    assert "rikugan-v1.0/a.txt" in names
    assert "rikugan-v1.0/sub/b.txt" in names


def test_archive_internal_path_prefix_uses_arcname_root(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "x.py").write_text("# x\n", encoding="utf-8")
    files = [tmp_path / "x.py"]
    zip_out = tmp_path / "out.zip"
    tar_out = tmp_path / "out.tar.gz"

    # Act
    build_zip(files, zip_out, "rikugan-v2.0.0-rc1")
    build_tar(files, tar_out, "rikugan-v2.0.0-rc1")

    # Assert: every entry starts with the arcname_root, no bare entries
    with zipfile.ZipFile(zip_out) as zf:
        zip_names = zf.namelist()
    with tarfile.open(tar_out) as tf:
        tar_names = tf.getnames()
    for n in zip_names + tar_names:
        assert n.startswith("rikugan-v2.0.0-rc1/"), f"unexpected entry: {n!r}"


def test_archive_preserves_file_contents(tmp_path: Path) -> None:
    # Arrange
    src = tmp_path / "src.txt"
    src.write_text("secret content 12345", encoding="utf-8")
    zip_out = tmp_path / "out.zip"
    tar_out = tmp_path / "out.tar.gz"

    # Act
    build_zip([src], zip_out, "rikugan-v1.0")
    build_tar([src], tar_out, "rikugan-v1.0")

    # Assert
    with zipfile.ZipFile(zip_out) as zf:
        assert zf.read("rikugan-v1.0/src.txt") == b"secret content 12345"
    with tarfile.open(tar_out) as tf:
        member = tf.getmember("rikugan-v1.0/src.txt")
        assert tf.extractfile(member).read() == b"secret content 12345"  # type: ignore[union-attr]
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v -k "build_zip or build_tar or archive"`

Expected: the 4 new tests fail with `NotImplementedError` (the stubs raise this).

- [ ] **Step 3: Implement `build_zip()` and `build_tar()`**

Edit `scripts/build_release.py`. Replace the `NotImplementedError` stubs for `build_zip` and `build_tar` with the real implementations:

```python
def build_zip(files: list[Path], out_path: Path, arcname_root: str) -> None:
    """Build zip archive với tất cả files, prefix bằng arcname_root.

    Each file's path inside the archive is ``{arcname_root}/{relpath}``
    where ``relpath`` is the file path relative to its source root
    (using forward slashes via ``as_posix()`` so archives are
    cross-platform).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in files:
            arcname = f"{arcname_root}/{src.as_posix()}"
            zf.write(src, arcname)


def build_tar(files: list[Path], out_path: Path, arcname_root: str) -> None:
    """Build tar.gz archive với tất cả files, prefix bằng arcname_root."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out_path, "w:gz") as tf:
        for src in files:
            arcname = f"{arcname_root}/{src.as_posix()}"
            tf.add(src, arcname=arcname, recursive=False)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v -k "build_zip or build_tar or archive"`

Expected: 4 new tests pass; all 11 collect/skip tests still pass (15 total).

- [ ] **Step 5: Commit**

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git add scripts/build_release.py tests/scripts/test_build_release.py
git commit -m "feat(scripts): add build_zip and build_tar (TDD)"
```

---

## Task 3: TDD `sha256_file()` + `write_sha256sums()` + `main()`

**Files:**
- Modify: `scripts/build_release.py` (replace remaining `NotImplementedError` stubs + add CLI)
- Modify: `tests/scripts/test_build_release.py` (append new tests)

**Interfaces:**
- Consumes: `path: Path` for `sha256_file`; `paths: list[Path]` + `out_path: Path` for `write_sha256sums`; CLI args (`--version`, `--out-dir`, `--source-root`) for `main()`.
- Produces: hex digest string (64 chars); `SHA256SUMS` file with two-space separators; exit code 0 on success, 1 on empty collect.

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_build_release.py`:

```python
import hashlib
import re

# ── sha256_file ───────────────────────────────────────────────────────


def test_sha256_matches_stdlib(tmp_path: Path) -> None:
    # Arrange
    p = tmp_path / "x.txt"
    p.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()

    # Act
    result = sha256_file(p)

    # Assert
    assert result == expected
    assert len(result) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", result)


def test_sha256_handles_large_file(tmp_path: Path) -> None:
    # Arrange: 5 MB random data
    p = tmp_path / "big.bin"
    p.write_bytes(bytes(range(256)) * (5 * 1024 * 1024 // 256))
    expected = hashlib.sha256(p.read_bytes()).hexdigest()

    # Act
    result = sha256_file(p)

    # Assert
    assert result == expected


# ── write_sha256sums ───────────────────────────────────────────────────


def test_write_sha256sums_format(tmp_path: Path) -> None:
    # Arrange
    a = tmp_path / "a.zip"
    b = tmp_path / "b.tar.gz"
    a.write_bytes(b"alpha")
    b.write_bytes(b"beta")
    out = tmp_path / "SHA256SUMS"

    # Act
    write_sha256sums([a, b], out)

    # Assert: two-space separator, one entry per line, hex + filename
    content = out.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        m = re.fullmatch(r"^([0-9a-f]{64})  (\S+)$", line)
        assert m, f"line does not match format: {line!r}"
    assert "a.zip" in content
    assert "b.tar.gz" in content
    # Both lines sorted by filename (a before b)
    assert lines[0].endswith("a.zip")
    assert lines[1].endswith("b.tar.gz")


# ── main() / CLI ──────────────────────────────────────────────────────


def test_main_writes_all_three_files(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)
    out_dir = tmp_path / "dist"

    # Act
    rc = _run_main(tmp_path, ["--version", "1.2.3", "--out-dir", str(out_dir), "--source-root", str(tmp_path)])

    # Assert
    assert rc == 0
    assert (out_dir / "rikugan-v1.2.3.zip").is_file()
    assert (out_dir / "rikugan-v1.2.3.tar.gz").is_file()
    assert (out_dir / "SHA256SUMS").is_file()


def test_main_archive_contents_have_correct_prefix(tmp_path: Path) -> None:
    # Arrange
    _seed_fake_repo(tmp_path)
    out_dir = tmp_path / "dist"

    # Act
    _run_main(tmp_path, ["--version", "1.2.3", "--out-dir", str(out_dir), "--source-root", str(tmp_path)])

    # Assert: archive root is rikugan-v1.2.3/
    with zipfile.ZipFile(out_dir / "rikugan-v1.2.3.zip") as zf:
        names = zf.namelist()
    assert any(n.startswith("rikugan-v1.2.3/rikugan_plugin.py") for n in names)
    assert any(n.startswith("rikugan-v1.2.3/rikugan/core/config.py") for n in names)
    assert any(n.startswith("rikugan-v1.2.3/install.sh") for n in names)


def test_main_fails_when_no_files_collected(tmp_path: Path, capsys) -> None:
    # Arrange: completely empty source root
    out_dir = tmp_path / "dist"

    # Act
    rc = _run_main(tmp_path, ["--version", "9.9.9", "--out-dir", str(out_dir), "--source-root", str(tmp_path)])

    # Assert
    assert rc == 1
    captured = capsys.readouterr()
    assert "no files collected" in captured.err.lower()


def test_main_requires_version_arg(tmp_path: Path) -> None:
    # Act + Assert
    with pytest.raises(SystemExit) as exc:
        _run_main(tmp_path, ["--out-dir", str(tmp_path), "--source-root", str(tmp_path)])
    assert exc.value.code == 2  # argparse error code


def _run_main(cwd: Path, argv: list[str]) -> int:
    """Helper: run main() with the given argv (no need to spawn subprocess)."""
    import sys
    old_argv = sys.argv
    sys.argv = ["build_release.py", *argv]
    old_cwd = Path.cwd()
    try:
        # main() uses Path(".") as default source root — chdir so the
        # argument resolution matches what a CLI invocation would see.
        import os
        os.chdir(cwd)
        # Reset Path(".") default resolution by patching argparse
        from scripts import build_release
        return build_release.main()
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v -k "sha256 or main or sums"`

Expected: the 6 new tests fail with `NotImplementedError` (the stubs) or `ImportError` for `_run_main`.

- [ ] **Step 3: Implement `sha256_file()`, `write_sha256sums()`, and `main()`**

Edit `scripts/build_release.py`. Replace the three remaining `NotImplementedError` stubs (`sha256_file`, `write_sha256sums`, `main`) with the real implementations:

```python
def sha256_file(path: Path) -> str:
    """Compute SHA256 hex digest của file (streamed, 1 MB chunks)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_sha256sums(paths: list[Path], out_path: Path) -> None:
    """Write SHA256SUMS file (GNU coreutils format: hex + 2 spaces + name)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"{sha256_file(p)}  {p.name}\n")


def main() -> int:
    """CLI entry point. See module docstring.

    Returns:
        0 on success, 1 if no files were collected.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Version vd: 1.2.3")
    parser.add_argument("--out-dir", type=Path, default=Path("dist"))
    parser.add_argument("--source-root", type=Path, default=Path("."))
    args = parser.parse_args()

    arcname = f"rikugan-v{args.version}"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    files = collect(args.source_root)
    if not files:
        print("ERROR: no files collected (source root empty?)", file=sys.stderr)
        return 1

    zip_path = args.out_dir / f"{arcname}.zip"
    tar_path = args.out_dir / f"{arcname}.tar.gz"
    build_zip(files, zip_path, arcname)
    build_tar(files, tar_path, arcname)

    sums_path = args.out_dir / "SHA256SUMS"
    write_sha256sums([zip_path, tar_path], sums_path)

    print(f"OK: {zip_path} ({zip_path.stat().st_size} bytes, {len(files)} files)")
    print(f"OK: {tar_path} ({tar_path.stat().st_size} bytes, {len(files)} files)")
    print(f"OK: {sums_path}")
    return 0
```

- [ ] **Step 4: Run all build_release tests**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v`

Expected: all 17 tests pass (4 should_skip + 7 collect + 4 build_zip/build_tar + 1 sha256 + 1 sha256_large + 1 sums format + 4 main).

- [ ] **Step 5: End-to-end local dry-run**

Verify the script works as a real CLI invocation (not just `main()` in-process):

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
python scripts/build_release.py --version 9.9.9 --out-dir /tmp/rikugan-dryrun --source-root .
```

Expected output:
```
OK: /tmp/rikugan-dryrun/rikugan-v9.9.9.zip (... bytes, N files)
OK: /tmp/rikugan-dryrun/rikugan-v9.9.9.tar.gz (... bytes, N files)
OK: /tmp/rikugan-dryrun/SHA256SUMS
```

Then verify:
```bash
unzip -l /tmp/rikugan-dryrun/rikugan-v9.9.9.zip | head -20
tar -tzf /tmp/rikugan-dryrun/rikugan-v9.9.9.tar.gz | head -20
cd /tmp/rikugan-dryrun && sha256sum -c SHA256SUMS
```

Expected: `sha256sum -c SHA256SUMS` prints `rikugan-v9.9.9.zip: OK` and `rikugan-v9.9.9.tar.gz: OK`. Cleanup:

```bash
rm -rf /tmp/rikugan-dryrun
```

- [ ] **Step 6: Run `./ci-local.sh` to confirm no regressions**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && ./ci-local.sh`

Expected: ALL PASSED. All 17 build_release tests show under `tests/scripts/`.

- [ ] **Step 7: Commit**

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git add scripts/build_release.py tests/scripts/test_build_release.py
git commit -m "feat(scripts): add sha256 + CLI entry point (TDD)"
```

---

## Task 4: Write `.github/workflows/release.yml`

**Files:**
- Rewrite: `.github/workflows/release.yml` (replace the 36-line skeleton)

**Interfaces:**
- Consumes: tag push event (`v*` or `[0-9]*.[0-9]*`) OR `workflow_dispatch` input `tag`
- Produces: a GitHub Release with 3 attached files (zip, tar.gz, SHA256SUMS) and a pre-release flag

- [ ] **Step 1: Write the new workflow**

Replace the entire contents of `.github/workflows/release.yml` with:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'
      - '[0-9]*.[0-9]*'
  workflow_dispatch:
    inputs:
      tag:
        description: 'Tag name to re-release (vd: v1.2 hoặc 1.2.3)'
        required: true
        type: string

permissions:
  contents: write

jobs:
  verify:
    name: Verify (tag + version + tests)
    runs-on: ubuntu-latest
    outputs:
      tag: ${{ steps.meta.outputs.tag }}
      version: ${{ steps.meta.outputs.version }}
      is_prerelease: ${{ steps.meta.outputs.is_prerelease }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dev tools
        run: pip install ruff mypy pytest tomli desloppify

      - name: Parse tag, version, pre-release flag
        id: meta
        run: |
          set -e
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            TAG="${{ inputs.tag }}"
          else
            TAG="${GITHUB_REF_NAME}"
          fi

          VERSION="${TAG#v}"

          PLUGIN_VERSION=$(python -c "import json; print(json.load(open('ida-plugin.json'))['plugin']['version'])")
          if [ "$VERSION" != "$PLUGIN_VERSION" ]; then
            echo "::error::Tag '$TAG' (→ version '$VERSION') does not match ida-plugin.json '$PLUGIN_VERSION'"
            exit 1
          fi

          if [[ "$TAG" =~ -(rc|alpha|beta|pre|dev)[0-9]*$ ]]; then
            IS_PRERELEASE="true"
          else
            IS_PRERELEASE="false"
          fi

          echo "tag=$TAG" >> "$GITHUB_OUTPUT"
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
          echo "is_prerelease=$IS_PRERELEASE" >> "$GITHUB_OUTPUT"
          echo "::notice::Parsed: tag=$TAG, version=$VERSION, is_prerelease=$IS_PRERELEASE"

      - name: Re-run CI checks (inline)
        run: |
          set -e
          echo "── ruff format check ──"
          python -m ruff format --check rikugan/

          echo "── ruff lint ──"
          python -m ruff check rikugan/

          echo "── mypy ──"
          python -m mypy rikugan/core rikugan/providers

          echo "── pytest ──"
          python -m pytest tests/ --tb=short -q

          echo "── desloppify (objective score) ──"
          desloppify scan --profile objective --no-badge
          SCORE=$(python -c "import json; print(json.load(open('.desloppify/query.json')).get('objective_score', 0))")
          BASELINE=89.0
          python -c "
          import sys
          s = float('$SCORE')
          if s < $BASELINE - 0.5:
              sys.exit(f'score {s} < baseline {$BASELINE} - 0.5')
          print(f'OK — score {s}')
          "

  build:
    name: Build artifacts
    needs: verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run build_release.py
        run: |
          python scripts/build_release.py \
            --version "${{ needs.verify.outputs.version }}" \
            --out-dir dist

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-artifacts
          path: dist/
          if-no-files-found: error

  publish:
    name: Publish GitHub Release
    needs: [verify, build]
    runs-on: ubuntu-latest
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: release-artifacts
          path: dist/

      - name: Create or update GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ needs.verify.outputs.tag }}
          name: "Rikugan ${{ needs.verify.outputs.version }}"
          prerelease: ${{ needs.verify.outputs.is_prerelease == 'true' }}
          generate_release_notes: true
          fail_on_unmatched_files: true
          files: |
            dist/rikugan-${{ needs.verify.outputs.version }}.zip
            dist/rikugan-${{ needs.verify.outputs.version }}.tar.gz
            dist/SHA256SUMS
```

- [ ] **Step 2: Validate YAML syntax locally**

Run:
```bash
cd /d/re_dev_projects/vibe-clone/rikugan
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml').read().replace('\${{', '__X__').replace('}}', '__Y__'))" && echo "YAML OK"
```

(The `replace` is a workaround because `yaml.safe_load` itself parses `${{ ... }}` as plain strings, but PyYAML's loader can choke on edge cases in expressions containing `:` or `{`. This test is a quick sanity check, not a full schema validation.)

Expected: prints `YAML OK`. If it errors, fix the YAML syntax (common causes: missing colons, misaligned indentation, unquoted `:` in shell strings).

- [ ] **Step 3: Commit**

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git add .github/workflows/release.yml
git commit -m "feat(ci): rewrite release.yml as 3-job pipeline (verify→build→publish)"
```

---

## Task 5: Update docs

**Files:**
- Modify: `AGENTS.md` (replace the "Release Flow" subsection in §"CI/CD & Branch Model")
- Modify: `DEVELOPMENT.md` (replace the "Release Process" subsection)
- Modify: `.gitignore` (append `dist/`)

- [ ] **Step 1: Update `AGENTS.md`**

In `AGENTS.md`, find the subsection "### Release Flow" (around line 456 in the current file). Replace the existing 3-line block with:

```markdown
### Release Flow

1. Bump `version` trong `ida-plugin.json` (trên `master`)
2. Commit + push lên `master`
3. Tag và push:
   ```bash
   git tag v1.x.x
   git push origin v1.x.x
   ```
4. GitHub Actions workflow `.github/workflows/release.yml` tự động:
   - **`verify`** — validate tag ↔ `ida-plugin.json.version`, re-run toàn bộ CI checks inline (ruff/mypy/pytest/desloppify). Fail → release không được publish.
   - **`build`** — chạy `scripts/build_release.py` tạo `rikugan-v1.x.x.zip`, `.tar.gz`, `SHA256SUMS`.
   - **`publish`** — `softprops/action-gh-release@v2` tạo/cập nhật GitHub Release với 3 artifact + auto-generated notes.
5. Tag suffix `-rc1`, `-beta1`, `-dev1`, ... → tự đánh dấu pre-release. Tag `v1.x.x` (no suffix) → stable.

**Re-run cho tag đã push** (sửa lỗi artifact, đổi notes, ...): Actions tab → chọn workflow "Release" → "Run workflow" → nhập tag name (vd: `v1.x.x`).

**Trigger pattern hỗ trợ**: `v*` (chuẩn) **và** bare version (vd: `1.0`, `1.2.3` — legacy). Xem spec `docs/superpowers/specs/2026-06-18-github-release-pipeline-design.md` để biết chi tiết.
```

- [ ] **Step 2: Update `DEVELOPMENT.md`**

In `DEVELOPMENT.md`, find the section "## Release Process" (around line 158). Replace the existing block with:

```markdown
## Release Process

The release pipeline is fully automated. Three steps:

1. Bump `version` trong `ida-plugin.json` (trên `master`)
2. Commit + push:
   ```bash
   git add ida-plugin.json
   git commit -m "chore: bump version to 1.x.x"
   git push origin master
   ```
3. Tag và push:
   ```bash
   git tag v1.x.x
   git push origin v1.x.x
   ```
4. GitHub Actions workflow tự chạy (verify → build → publish). Xem trạng thái ở tab Actions. Release xuất hiện tại `https://github.com/EliteClassRoom/rikugan/releases/tag/v1.x.x` với 3 artifact: `rikugan-v1.x.x.zip`, `.tar.gz`, `SHA256SUMS`.

**Re-run cho tag đã tồn tại**: Actions tab → workflow "Release" → "Run workflow" → nhập tag name. Workflow re-runs verify + build + publish cho cùng tag (idempotent — cập nhật artifacts thay vì tạo release mới).

**Pre-release tags**: thêm suffix `-rc1`, `-beta1`, `-dev1` (vd: `v1.4.0-rc1`) → GitHub tự đánh dấu pre-release. Tag không suffix → stable.

**Local dry-run** (test trước khi tag):
```bash
python scripts/build_release.py --version 1.x.x-test --out-dir /tmp/rikugan-test
unzip -l /tmp/rikugan-test/rikugan-v1.x.x-test.zip
cd /tmp/rikugan-test && sha256sum -c SHA256SUMS
rm -rf /tmp/rikugan-test
```

**Smoke test toàn pipeline** (khuyến nghị trước mỗi release):
```bash
git tag v0.0.0-test && git push origin v0.0.0-test
# → check Actions tab: 3 jobs xanh, draft release xuất hiện
git push origin :refs/tags/v0.0.0-test
gh release delete v0.0.0-test --repo EliteClassRoom/rikugan --yes
```
```

- [ ] **Step 3: Add `dist/` to `.gitignore`**

Append to `.gitignore` (one new line at the end of the file):

```
# Local build output from scripts/build_release.py
dist/
```

- [ ] **Step 4: Commit**

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git add AGENTS.md DEVELOPMENT.md .gitignore
git commit -m "docs(ci): document new release pipeline + add dist/ to gitignore"
```

---

## Task 6: End-to-end local verification

**Files:** none (verification only)

- [ ] **Step 1: Run all build_release tests one more time**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && python -m pytest tests/scripts/test_build_release.py -v`

Expected: 17 tests pass.

- [ ] **Step 2: Run `./ci-local.sh` to confirm full pipeline still green**

Run: `cd /d/re_dev_projects/vibe-clone/rikugan && ./ci-local.sh`

Expected: ALL PASSED. The summary should show 5 ✔ (ruff format, ruff lint, mypy, pytest, desloppify) and pytest should include the new `tests/scripts/test_build_release.py` tests.

- [ ] **Step 3: Local end-to-end build (final sanity check)**

Run:
```bash
cd /d/re_dev_projects/vibe-clone/rikugan
python scripts/build_release.py --version 1.2 --out-dir /tmp/rikugan-final --source-root .
ls -la /tmp/rikugan-final/
unzip -l /tmp/rikugan-final/rikugan-v1.2.zip | head -30
cd /tmp/rikugan-final && sha256sum -c SHA256SUMS
```

Expected:
- `dist/` (wait, `/tmp/rikugan-final/`) contains 3 files: `rikugan-v1.2.zip`, `rikugan-v1.2.tar.gz`, `SHA256SUMS`.
- `unzip -l` shows ~30+ entries (rikugan_plugin.py + rikugan/ package + 4 install scripts + 4 config files).
- `sha256sum -c SHA256SUMS` reports `OK` for both archives.

Verify the curated content is correct (no `tests/`, `docs/`, `assets/`, etc.):
```bash
unzip -l /tmp/rikugan-final/rikugan-v1.2.zip | awk '{print $4}' | grep -E "(tests/|docs/|assets/|chat_examples/|webpage/|ci-local|pyproject|uv.lock|AGENTS.md|ARCHITECTURE.md|DEVELOPMENT.md|llms.txt|\.github/)" | head -5
```

Expected: empty output (no excluded files inside the archive).

Clean up:
```bash
rm -rf /tmp/rikugan-final
```

- [ ] **Step 4: Push and watch the actual GitHub Actions run**

```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git push origin master
```

Then open `https://github.com/EliteClassRoom/rikugan/actions` and confirm:
- The new release.yml workflow file is **recognized** (the file picker on the left should show "Release" with the new YAML).
- Push a throwaway tag to trigger the workflow:
  ```bash
  git tag v0.0.0-test
  git push origin v0.0.0-test
  ```
- All 3 jobs (`verify`, `build`, `publish`) run green.
- A draft release appears at `https://github.com/EliteClassRoom/rikugan/releases/tag/v0.0.0-test` with 3 files attached.
- Click into the draft → confirm `SHA256SUMS` content matches `sha256sum` of the zip/tar.gz.

Clean up the test tag + draft release:
```bash
git push origin :refs/tags/v0.0.0-test
gh release delete v0.0.0-test --repo EliteClassRoom/rikugan --yes
git tag -d v0.0.0-test
```

- [ ] **Step 5: Final commit (if any cleanup was needed)**

If Step 4 surfaced any small fix (typo, wrong action version, etc.), commit the fix:
```bash
cd /d/re_dev_projects/vibe-clone/rikugan
git add -A
git commit -m "fix(release): <description of what was wrong>"
```

Otherwise no commit is needed. The plan is complete.

---

## Self-Review

**Spec coverage check** (mapping each spec requirement to a task):

| Spec section | Covered by |
|--------------|------------|
| Trigger model (v* + bare + dispatch) | Task 4 (workflow YAML) |
| verify job — tag parse | Task 4 (Step 1, "Parse tag, version, pre-release flag") |
| verify job — version validation | Task 4 (same step, fail on mismatch) |
| verify job — inline CI re-run | Task 4 (Step 1, "Re-run CI checks (inline)") |
| build job — `scripts/build_release.py` | Tasks 1, 2, 3 (TDD on the script) |
| build job — INCLUDE_PATHS / EXCLUDE_NAMES | Task 1 (Step 4) |
| build job — `rikugan-v{version}.{zip,tar.gz}` | Task 3 (Step 3, `main()`) |
| build job — `SHA256SUMS` | Task 3 (Step 3, `write_sha256sums`) |
| build job — upload-artifact@v4 | Task 4 (Step 1, build job) |
| publish job — softprops with prerelease flag | Task 4 (Step 1, publish job) |
| publish job — fail_on_unmatched_files | Task 4 (Step 1, publish job) |
| Pre-release detection regex | Task 4 (Step 1, meta step) |
| Files touched (release.yml, build_release.py, tests, docs, .gitignore) | Tasks 1, 2, 3, 4, 5 |
| Local dry-run command | Task 3 (Step 5) + Task 6 (Step 3) |
| Post-merge smoke test | Task 6 (Step 4) |
| 12 unit tests | Tasks 1, 2, 3 (15 tests total, with 3 extras for archive contents + sums format) |

**Placeholder scan**: No "TBD", "TODO", "implement later", "add appropriate error handling", or "similar to Task N" found. Every step has concrete code or commands.

**Type consistency check**:
- `should_skip(path: Path) -> bool` defined Task 1, used nowhere else directly (only called from `collect`).
- `collect(source_root: Path) -> list[Path]` defined Task 1, used in Task 3's `main()` (Task 3 imports it from `scripts.build_release`).
- `build_zip(files: list[Path], out_path: Path, arcname_root: str) -> None` defined Task 2, used in Task 3's `main()`.
- `build_tar(...)` — same signature, same consumers.
- `sha256_file(path: Path) -> str` defined Task 3, used in `write_sha256sums`.
- `write_sha256sums(paths: list[Path], out_path: Path) -> None` defined Task 3, used in `main`.
- `main() -> int` defined Task 3, called by `if __name__ == "__main__": sys.exit(main())`.
- `INCLUDE_PATHS`, `EXCLUDE_NAMES`, `EXCLUDE_SUFFIXES` module-level constants defined Task 1, used only inside `collect` / `should_skip`.
- `archive_basename` output: spec mentioned this as a `verify` job output, but I dropped it because nothing downstream uses it (the build job recomputes from `version`). **Removed silently in plan** — should be OK since spec was approved, but worth flagging during execution.
- `github.event_name` referenced in workflow (Step 1 of Task 4). GitHub Actions context — standard.
- `inputs.tag` referenced in workflow, defined in `workflow_dispatch.inputs` block of the same step.

No type / signature drift between tasks found.

**One spec deviation** (intentional, harmless):
- Spec listed `archive_basename` as a `verify` job output. The plan does not include it because it is a simple transform of `version` and the `build` job recomputes it. No code downstream consumes `archive_basename`. This is a YAGNI simplification, not a behavior change.
