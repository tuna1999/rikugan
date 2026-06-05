# Remove Binary Ninja Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop Binary Ninja (BN) host support from Rikugan entirely, leaving an IDA-only plugin. Delete all BN code, entry points, installers, and skills; strip BN detection from core abstractions; deduplicate IDA tool helpers; rewrite documentation.

**Architecture:** Pure refactor with zero new features. The codebase goes from dual-host (IDA Pro + Binary Ninja) to single-host (IDA Pro only). Work is organized in 7 phases, each producing exactly one git commit. Every phase must leave `ruff check` + `mypy rikugan/core rikugan/providers` + `pytest tests/` green.

**Tech Stack:** Python 3.11+, PySide6/PyQt5, IDA Pro 9.x, `pytest`, `ruff`, `mypy`, `desloppify`.

**Source spec:** `docs/superpowers/specs/2026-06-05-remove-binja-support-design.md`

---

## File Structure

**Files to delete (Phase 1, ~7,392 LOC):**
- `rikugan/binja/` — entire package (24 .py files)
- `rikugan_binaryninja.py` — BN plugin entry point
- `install_binaryninja.sh`, `install_binaryninja.bat` — BN installers
- `plugin.json` — BN plugin manifest
- `rikugan/skills/builtins/binja-scripting/` — BN Python API skill
- `rikugan/skills/builtins/smart-patch-binja/` — BN patching skill
- `rikugan/skills/builtins/deobfuscation/references/binja/` — BN deobfuscation refs
- `tests/tools/test_binja_actions.py`, `test_binja_common.py`, `test_binja_panel.py`, `test_binja_types_tools.py`, `test_rikugan_binaryninja.py` — BN tests
- `tests/core/test_host_matrix.py` — host matrix test

**Files to delete (Phase 2, 53 LOC):**
- `rikugan/agent/prompts/binja.py` — BN base system prompt

**Files to delete (Phase 3, 269 LOC):**
- `rikugan/tools/xrefs.py` — duplicate of `rikugan/ida/tools/xrefs.py`
- `rikugan/tools/functions.py` — duplicate of `rikugan/ida/tools/functions.py`

**Files to create (Phase 3, ~50 LOC):**
- `rikugan/tools/formatting.py` — shared formatting helpers (`format_callers_callees`, `format_function_summary`)

**Files to modify (Phase 2):**
- `rikugan/core/host.py` — strip BN detection
- `rikugan/agent/system_prompt.py` — drop BN prompt
- `rikugan/core/log_sinks.py` — drop BN log path
- `rikugan/state/history.py` — drop `.bndb` handling
- `rikugan/skills/loader.py` — drop BN config dir
- `rikugan/core/thread_safety.py` — drop BN thread-safety references
- `rikugan/ui/session_controller_base.py` — drop BN docstring mentions
- `rikugan/ui/panel.py` — drop BN UI strings
- `rikugan/ui/action_handlers.py` — drop BN UI strings
- `rikugan/ui/tool_widgets.py` — drop BN UI strings

**Files to modify (Phase 3):**
- `rikugan/ida/tools/xrefs.py` — import from `rikugan.tools.formatting`
- `rikugan/ida/tools/functions.py` — import from `rikugan.tools.formatting`
- `rikugan/tools/__init__.py` — update docstring

**Files to modify (Phase 4):**
- `rikugan/skills/builtins/deobfuscation/SKILL.md` — strip BN references
- `rikugan/skills/builtins/modify/SKILL.md` — strip BN references (if any)
- `rikugan/skills/builtins/smart-patch-ida/SKILL.md` — strip BN references (if any)

**Files to modify (Phase 5):**
- `tests/core/test_host.py` — drop BN test cases
- `tests/tools/test_panel_core.py` — drop BN host_name param
- `tests/tools/test_tool_widget_logic.py` — drop BN host_name param
- `tests/tools/test_context_bar.py` — drop BN host_name param (if any)
- `tests/tools/test_sanitize.py` — drop BN-specific input tests (if any)

**Files to modify (Phase 6):**
- `AGENTS.md` — rewrite to IDA-only
- `CLAUDE.md` — rewrite to IDA-only
- `ARCHITECTURE.md` — rewrite to IDA-only
- `README.md` — rewrite to IDA-only
- `DEVELOPMENT.md` — rewrite to IDA-only
- `llms.txt` — strip BN references
- `.github/workflows/ci.yml` — drop BN test job (if present)
- `pyproject.toml` — drop `rikugan/binja/**` and `rikugan/tools/functions.py` per-file-ignores
- `CHANGELOG.md` — add BN removal entry

**Files to create (Phase 0):**
- `docs/superpowers/research/binja-removal-inventory.md` — research output

---

## Phase 0: Research & Inventory

**Files:**
- Create: `docs/superpowers/research/binja-removal-inventory.md`
- Create branch: `refactor/remove-binja-support` from `dev`

- [ ] **Step 1: Verify working tree is clean and on main**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git status
git log --oneline -3
```
Expected: working tree clean, HEAD on `main` with `docs(spec): fix accuracy issues in BN removal design` as the most recent commit.

- [ ] **Step 2: Create research branch from main**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git checkout -b refactor/remove-binja-support
```
Expected: `Switched to a new branch 'refactor/remove-binja-support'`.

- [ ] **Step 3: Tag the pre-removal safety net**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git tag pre-binja-removal HEAD
```
Expected: nothing on stdout, exit code 0. Verify with `git tag --list | grep pre-binja-removal`.

- [ ] **Step 4: Build complete BN reference inventory**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -rIn 'binja\|BN\|BinaryNinja\|binaryninja' \
  rikugan/ tests/ docs/ \
  --include='*.py' --include='*.md' --include='*.yml' --include='*.json' --include='*.toml' \
  | grep -v '__pycache__' \
  > /tmp/binja-inventory.txt
wc -l /tmp/binja-inventory.txt
```
Expected: a non-empty file. Save the count for the inventory doc.

- [ ] **Step 5: Capture baseline test status**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m pytest tests/ -q 2>&1 | tail -10
```
Expected: a final line like `X passed in Y.Ys` with X ≥ 100, no failures. Record the number in the inventory doc.

- [ ] **Step 6: Write the inventory document**

Create `docs/superpowers/research/binja-removal-inventory.md` with this content:

```markdown
# Binary Ninja Removal — Pre-flight Inventory

**Date**: 2026-06-05
**Branch**: refactor/remove-binja-support
**Baseline tag**: pre-binja-removal

## Summary

- **Total BN reference matches**: <number from Step 4>
- **Baseline test count**: <X passed, from Step 5>

## Files to delete in Phase 1 (pure BN, no inbound imports from survivors)

### Package: rikugan/binja/ (24 .py files, 4,139 LOC)
- rikugan/binja/__init__.py
- rikugan/binja/bootstrap.py
- rikugan/binja/tools/__init__.py
- rikugan/binja/tools/annotations.py
- rikugan/binja/tools/comment_utils.py
- rikugan/binja/tools/compat.py
- rikugan/binja/tools/database.py
- rikugan/binja/tools/decompiler.py
- rikugan/binja/tools/disasm_utils.py
- rikugan/binja/tools/disassembly.py
- rikugan/binja/tools/fn_utils.py
- rikugan/binja/tools/functions.py
- rikugan/binja/tools/il.py
- rikugan/binja/tools/il_analysis.py
- rikugan/binja/tools/il_transform.py
- rikugan/binja/tools/navigation.py
- rikugan/binja/tools/registry.py
- rikugan/binja/tools/scripting.py
- rikugan/binja/tools/strings.py
- rikugan/binja/tools/sym_utils.py
- rikugan/binja/tools/type_utils.py
- rikugan/binja/tools/types_tools.py
- rikugan/binja/tools/xrefs.py
- rikugan/binja/ui/__init__.py
- rikugan/binja/ui/actions.py
- rikugan/binja/ui/panel.py
- rikugan/binja/ui/session_controller.py

### Root-level files
- rikugan_binaryninja.py (18 LOC)
- install_binaryninja.sh (212 LOC)
- install_binaryninja.bat (207 LOC)
- plugin.json (40 LOC)

### Skill folders
- rikugan/skills/builtins/binja-scripting/SKILL.md (314 LOC)
- rikugan/skills/builtins/binja-scripting/references/api-reference.md (460 LOC)
- rikugan/skills/builtins/smart-patch-binja/SKILL.md (95 LOC)
- rikugan/skills/builtins/deobfuscation/references/binja/algorithm-reference.md (201 LOC)
- rikugan/skills/builtins/deobfuscation/references/binja/guide.md (157 LOC)
- rikugan/skills/builtins/deobfuscation/references/binja/il-guide.md (194 LOC)
- rikugan/skills/builtins/deobfuscation/references/binja/tools.md (58 LOC)

### Test files
- tests/tools/test_binja_actions.py (249 LOC)
- tests/tools/test_binja_common.py (291 LOC)
- tests/tools/test_binja_panel.py (106 LOC)
- tests/tools/test_binja_types_tools.py (109 LOC)
- tests/tools/test_rikugan_binaryninja.py (290 LOC)
- tests/core/test_host_matrix.py (252 LOC)

## Files to delete in Phase 2 (after BN prompt is unwired)
- rikugan/agent/prompts/binja.py (53 LOC)

## Files to delete in Phase 3 (after IDA tools switch imports)
- rikugan/tools/xrefs.py (140 LOC)
- rikugan/tools/functions.py (129 LOC)

## Files to modify

### Phase 2 (core BN detection strip)
- rikugan/core/host.py
- rikugan/agent/system_prompt.py
- rikugan/core/log_sinks.py
- rikugan/state/history.py
- rikugan/skills/loader.py
- rikugan/core/thread_safety.py
- rikugan/ui/session_controller_base.py
- rikugan/ui/panel.py
- rikugan/ui/action_handlers.py
- rikugan/ui/tool_widgets.py

### Phase 3 (dedup)
- rikugan/ida/tools/xrefs.py (import update)
- rikugan/ida/tools/functions.py (import update)
- rikugan/tools/__init__.py (docstring update)

### Phase 4 (skill content)
- rikugan/skills/builtins/deobfuscation/SKILL.md
- (any other skill with BN mentions — to be found in Step 7)

### Phase 5 (tests)
- tests/core/test_host.py
- tests/tools/test_panel_core.py
- tests/tools/test_tool_widget_logic.py
- tests/tools/test_context_bar.py
- tests/tools/test_sanitize.py

### Phase 6 (docs + config)
- AGENTS.md
- CLAUDE.md
- ARCHITECTURE.md
- README.md
- DEVELOPMENT.md
- llms.txt
- .github/workflows/ci.yml
- pyproject.toml
- CHANGELOG.md

## Verification commands for end of every phase

```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
```
```

- [ ] **Step 7: Find BN mentions inside remaining skills**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -rIn 'binja\|Binary Ninja\|BN' \
  rikugan/skills/builtins/ \
  --include='*.md' \
  | grep -v 'binja-scripting' \
  | grep -v 'smart-patch-binja' \
  | grep -v 'deobfuscation/references/binja'
```
Expected: a list of files and lines that need Phase 4 cleanup. Add them to the inventory doc under "Phase 4 (skill content)".

- [ ] **Step 8: Commit the inventory**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add docs/superpowers/research/binja-removal-inventory.md
git commit -m "docs(research): inventory Binary Ninja references for removal"
```
Expected: 1 file changed, ~80 insertions.

---

## Phase 1: Pure Deletions

**Files:** All files in the "Phase 1" section of the inventory.

- [ ] **Step 1: Delete the rikugan/binja/ package**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git rm -r rikugan/binja/
```
Expected: `rm 'rikugan/binja/...'` for all 24 files inside.

- [ ] **Step 2: Delete BN entry point and installer files**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git rm rikugan_binaryninja.py install_binaryninja.sh install_binaryninja.bat plugin.json
```
Expected: 4 files removed.

- [ ] **Step 3: Delete BN skill folders**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git rm -r rikugan/skills/builtins/binja-scripting/
git rm -r rikugan/skills/builtins/smart-patch-binja/
git rm -r rikugan/skills/builtins/deobfuscation/references/binja/
```
Expected: 8 files removed (2 in binja-scripting, 1 in smart-patch-binja, 4 in deobfuscation/binja, plus 1 in each folder's parent if needed).

- [ ] **Step 4: Delete BN test files and host matrix test**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git rm tests/tools/test_binja_actions.py \
       tests/tools/test_binja_common.py \
       tests/tools/test_binja_panel.py \
       tests/tools/test_binja_types_tools.py \
       tests/tools/test_rikugan_binaryninja.py \
       tests/core/test_host_matrix.py
```
Expected: 6 files removed.

- [ ] **Step 5: Run ruff, mypy, and pytest to confirm IDA tests still pass**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
```
Expected:
- ruff: exit 0
- mypy: exit 0 (no errors)
- pytest: shows fewer tests than baseline (the BN tests are gone) but all pass

If any test FAILS: stop, investigate, and fix. The most common issue is `from rikugan.binja...` left in some test fixture — grep with `grep -rIn 'rikugan.binja' tests/` to find it. If a real bug is uncovered, revert the deletion with `git checkout HEAD -- <file>` and investigate.

- [ ] **Step 6: Commit Phase 1**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add -A
git commit -m "refactor(binja): remove Binary Ninja package and entry points

Pure deletion of 7,392 LOC of Binary Ninja host code, installers,
skills, and tests. No inbound imports from surviving code reference
any of these files, so this commit is atomic and reverts cleanly.

Files deleted:
- rikugan/binja/ (entire 24-file package)
- rikugan_binaryninja.py (BN plugin entry point)
- install_binaryninja.sh, install_binaryninja.bat (BN installers)
- plugin.json (BN plugin manifest)
- rikugan/skills/builtins/binja-scripting/ (BN Python API skill)
- rikugan/skills/builtins/smart-patch-binja/ (BN patching skill)
- rikugan/skills/builtins/deobfuscation/references/binja/ (4 files)
- 5 BN test files + tests/core/test_host_matrix.py"
```
Expected: 1 commit on top of Phase 0.

---

## Phase 2: Strip BN Detection from Core

**Files:**
- Modify: `rikugan/core/host.py`
- Modify: `rikugan/agent/system_prompt.py`
- Modify: `rikugan/core/log_sinks.py`
- Modify: `rikugan/state/history.py`
- Modify: `rikugan/skills/loader.py`
- Modify: `rikugan/core/thread_safety.py`
- Modify: `rikugan/ui/session_controller_base.py`
- Modify: `rikugan/ui/panel.py`
- Modify: `rikugan/ui/action_handlers.py`
- Modify: `rikugan/ui/tool_widgets.py`
- Delete: `rikugan/agent/prompts/binja.py`

- [ ] **Step 1: Read `rikugan/core/host.py` in full to understand current shape**

Run:
```bash
cd D:/re_dev_projects/Rikugan
wc -l rikugan/core/host.py
```
Expected: file exists, ~200 LOC. Read it with the Read tool to see the current structure.

- [ ] **Step 2: Edit `rikugan/core/host.py` — remove BN constants and globals**

Open the file and find these exact lines/blocks and delete them:

**Delete**:
```python
HOST_BINARY_NINJA = "binary_ninja"
```

**Delete**:
```python
HOST_STANDALONE = "standalone"

_HOST = HOST_STANDALONE
_idc = None
_idaapi = None
_ida_kernwin = None
try:
    _idaapi = importlib.import_module("idaapi")
    _HOST = HOST_IDA
    # Cache frequently-used IDA modules to avoid repeated importlib lookups.
    # Both are optional — headless/batch IDA may not expose them.
    try:
        _idc = importlib.import_module("idc")
    except ImportError:
        _idc = None  # optional — absent in some IDA headless configurations
    try:
        _ida_kernwin = importlib.import_module("ida_kernwin")
    except ImportError:
        _ida_kernwin = None  # optional — absent in some IDA headless configurations
except ImportError:
    try:
        importlib.import_module("binaryninja")
        _HOST = HOST_BINARY_NINJA
    except ImportError:
        _HOST = HOST_STANDALONE


_ctx_lock = threading.RLock()
_bn_bv: Any = None
_bn_address: int | None = None
_bn_navigate_cb: Callable[[int], bool] | None = None
```

**Replace with**:
```python
HOST_STANDALONE = "standalone"

_HOST = HOST_STANDALONE
_idc = None
_idaapi = None
_ida_kernwin = None
try:
    _idaapi = importlib.import_module("idaapi")
    _HOST = HOST_IDA
    # Cache frequently-used IDA modules to avoid repeated importlib lookups.
    # Both are optional — headless/batch IDA may not expose them.
    try:
        _idc = importlib.import_module("idc")
    except ImportError:
        _idc = None  # optional — absent in some IDA headless configurations
    try:
        _ida_kernwin = importlib.import_module("ida_kernwin")
    except ImportError:
        _ida_kernwin = None  # optional — absent in some IDA headless configurations
except ImportError:
    _HOST = HOST_STANDALONE
```

**Delete**:
```python
def is_binary_ninja() -> bool:
    return _HOST == HOST_BINARY_NINJA
```

**Delete**:
```python
BINARY_NINJA_AVAILABLE = is_binary_ninja()
```

(The `IDA_AVAILABLE` constant defined right after stays.)

- [ ] **Step 3: Edit `rikugan/core/host.py` — remove BN setter/getter functions**

Find and delete these entire functions:
```python
def set_binary_ninja_context(
    bv: Any,
    address: int,
    navigate_cb: Callable[[int], bool],
) -> None:
    ...

def get_binary_ninja_view() -> Any:
    ...
```

(Use Edit with the exact current text; the body is whatever the current implementation is — just delete the whole `def` block.)

- [ ] **Step 4: Edit `rikugan/core/host.py` — remove `is_binary_ninja()` branches in remaining functions**

For each of the following functions, find the branch that starts with `if is_binary_ninja():` and remove the entire `if/else` arm that handles BN (keep the IDA branch and the fallback):

- `get_current_address()`
- `set_current_address()`
- `navigate_to()`
- `get_user_config_base_dir()`
- `get_database_path()`
- `get_database_instance_id()`
- `set_database_instance_id()`

For example, if the function currently looks like:
```python
def navigate_to(address: int) -> bool:
    if is_ida():
        ...
        return True
    if is_binary_ninja():
        ...
        return True
    return False
```

Change it to:
```python
def navigate_to(address: int) -> bool:
    if is_ida():
        ...
        return True
    return False
```

- [ ] **Step 5: Edit `rikugan/core/host.py` — remove `BINARY_NINJA` from `host_display_name()`**

Find:
```python
_HOST_DISPLAY_NAMES = {
    HOST_IDA: "IDA Pro",
    HOST_BINARY_NINJA: "Binary Ninja",
    HOST_STANDALONE: "Standalone Python",
}
```

Replace with:
```python
_HOST_DISPLAY_NAMES = {
    HOST_IDA: "IDA Pro",
    HOST_STANDALONE: "Standalone Python",
}
```

- [ ] **Step 6: Edit `rikugan/agent/system_prompt.py` — drop BN prompt import and dict entry**

Find and delete:
```python
from .prompts.binja import BINJA_BASE_PROMPT
```

Find and change:
```python
_HOST_PROMPTS = {"IDA Pro": IDA_BASE_PROMPT, "Binary Ninja": BINJA_BASE_PROMPT}
```

To:
```python
_HOST_PROMPTS = {"IDA Pro": IDA_BASE_PROMPT}
```

- [ ] **Step 7: Delete `rikugan/agent/prompts/binja.py`**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git rm rikugan/agent/prompts/binja.py
```
Expected: 1 file removed.

- [ ] **Step 8: Edit `rikugan/core/log_sinks.py` — drop BN log path**

Find any line containing `binaryninja` (case-insensitive search: `grep -in binaryninja rikugan/core/log_sinks.py`) and remove the BN branch. The IDA branch must remain. The standalone fallback must remain.

- [ ] **Step 9: Edit `rikugan/state/history.py` — drop `.bndb` path handling**

Find any code path that references `bndb` (case-insensitive). Typically this is a path-extension check. Remove the BN branch, keep the IDB and standalone branches.

- [ ] **Step 10: Edit `rikugan/skills/loader.py` — drop BN config dir**

Find any line that builds a path containing `binaryninja` or `.binaryninja` and remove it. The IDA branch (`~/.idapro/rikugan/skills/`) stays. The standalone fallback stays.

- [ ] **Step 11: Edit `rikugan/core/thread_safety.py` — drop BN thread-safety references**

Find any comment or docstring that says "Binary Ninja's API is thread-safe" or similar and remove it. No code change expected.

- [ ] **Step 12: Edit `rikugan/ui/session_controller_base.py` — drop BN docstring mentions**

Find any docstring or comment containing "Binary Ninja" or "BN" and rewrite to describe IDA only.

- [ ] **Step 13: Edit UI files — drop BN strings**

For each of:
- `rikugan/ui/panel.py`
- `rikugan/ui/action_handlers.py`
- `rikugan/ui/tool_widgets.py`

Run: `grep -n 'Binary Ninja\|"BN"\|binja' rikugan/ui/<filename>`
For each match, decide:
- If it's a user-visible label like "Binary Ninja Plugin" → delete the line entirely (or replace with `pass` if needed)
- If it's a comment → delete the comment
- If it's an import that is no longer needed → delete the import

- [ ] **Step 14: Run all CI checks**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
grep -rIn 'binaryninja\|is_binary_ninja\|HOST_BINARY_NINJA' rikugan/ --include='*.py'
```
Expected:
- ruff: exit 0
- mypy: exit 0
- pytest: all pass
- grep: no matches

If any fails, fix and re-run before committing.

- [ ] **Step 15: Commit Phase 2**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add -A
git commit -m "refactor(core): strip Binary Ninja host detection and dispatch

Removes all BN branches from core abstractions:
- rikugan/core/host.py: drop HOST_BINARY_NINJA, is_binary_ninja(),
  BINARY_NINJA_AVAILABLE, set/get_binary_ninja_context(), _bn_* globals,
  and is_binary_ninja() arms in 7 utility functions. host_display_name()
  no longer returns a BN label.
- rikugan/agent/system_prompt.py: drop BINJA_BASE_PROMPT import and
  the 'Binary Ninja' entry in _HOST_PROMPTS.
- rikugan/agent/prompts/binja.py: deleted (53 LOC).
- rikugan/core/log_sinks.py: drop BN log directory.
- rikugan/state/history.py: drop .bndb path handling.
- rikugan/skills/loader.py: drop BN config dir discovery.
- rikugan/core/thread_safety.py: drop BN thread-safety comment.
- rikugan/ui/session_controller_base.py: docstring cleanup.
- rikugan/ui/{panel,action_handlers,tool_widgets}.py: drop user-visible
  'Binary Ninja' strings.

Net: -350 LOC."
```
Expected: 1 commit on top of Phase 1.

---

## Phase 3: Deduplicate `rikugan/tools/` and `rikugan/ida/tools/`

**Files:**
- Create: `rikugan/tools/formatting.py`
- Modify: `rikugan/ida/tools/xrefs.py` (one import line)
- Modify: `rikugan/ida/tools/functions.py` (one import line)
- Modify: `rikugan/tools/__init__.py` (docstring)
- Delete: `rikugan/tools/xrefs.py`
- Delete: `rikugan/tools/functions.py`

- [ ] **Step 1: Read the existing `format_callers_callees()` in `rikugan/tools/xrefs.py`**

Run: `Read rikugan/tools/xrefs.py` and locate the function `format_callers_callees` (around line 12-23).

Copy the function body exactly as-is (including the docstring).

- [ ] **Step 2: Read the existing `format_function_summary()` in `rikugan/tools/functions.py`**

Run: `Read rikugan/tools/functions.py` and locate the function `format_function_summary` (around line 12-34).

Copy the function body exactly as-is.

- [ ] **Step 3: Create `rikugan/tools/formatting.py`**

Write the file with this content:

```python
"""Shared text formatting helpers used by IDA tool implementations.

These functions are pure string formatters with no host-API dependencies,
so they live in the shared ``rikugan.tools`` framework rather than in a
host-specific subpackage.
"""

from __future__ import annotations

from collections.abc import Iterable


def format_callers_callees(
    fname: str,
    start: int,
    callers: Iterable[str],
    callees: Iterable[str],
) -> str:
    """Format a function callers/callees summary."""
    callers = sorted(callers)
    callees = sorted(callees)
    parts = [f"Function: {fname} (0x{start:x})"]
    parts.append(f"\nCallers ({len(callers)}):")
    for c in callers:
        parts.append(f"  {c}")
    parts.append(f"\nCallees ({len(callees)}):")
    for c in callees:
        parts.append(f"  {c}")
    return "\n".join(parts)


def format_function_summary(
    name: str,
    start: int,
    end: int,
    size: int,
    blocks: int,
    instrs: int,
    callers: list[str],
    callees: list[str],
) -> str:
    """Format a function info summary string."""
    parts = [
        f"Name: {name}",
        f"Address: 0x{start:x} – 0x{end:x}",
        f"Size: {size} bytes",
        f"Basic blocks: {blocks}",
        f"Instructions: {instrs}",
    ]
    if callers:
        parts.append(f"Callers ({len(callers)}): {', '.join(callers)}")
    if callees:
        parts.append(f"Callees ({len(callees)}): {', '.join(callees)}")
    return "\n".join(parts)
```

- [ ] **Step 4: Verify the new module imports cleanly**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -c "from rikugan.tools.formatting import format_callers_callees, format_function_summary; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Update import in `rikugan/ida/tools/xrefs.py`**

Find (in `rikugan/ida/tools/xrefs.py`):
```python
def format_callers_callees(fname: str, start: int, callers: Iterable[str], callees: Iterable[str]) -> str:
    """Format a function callers/callees summary (shared between IDA and BN xref tools)."""
```

Delete the entire function definition (12 lines + the blank line after it).

Then find the existing import line near the top of the file (the one that pulls in `parse_addr, tool` from `...tools.base`):
```python
from ...tools.base import parse_addr, tool
```

Leave it untouched. The `format_callers_callees` function is no longer in this file — the IDA tool that uses it (e.g., `function_xrefs`) will import it from `rikugan.tools.formatting`.

Now find the `@tool` decorated function that uses `format_callers_callees` (search for `format_callers_callees(` in this file). It will be inside something like:
```python
@tool(category="xrefs")
def function_xrefs(address: ...) -> str:
    ...
    return format_callers_callees(name, ea, callers, callees)
```

Leave the call site as-is. The import will be added in the next step.

- [ ] **Step 6: Add the new import to `rikugan/ida/tools/xrefs.py`**

Find the existing block of imports near the top of `rikugan/ida/tools/xrefs.py`:
```python
from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Annotated

from ...tools.base import parse_addr, tool
```

Add a new line after `from ...tools.base import parse_addr, tool`:
```python
from ...tools.formatting import format_callers_callees
```

So the imports section becomes:
```python
from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Annotated

from ...tools.base import parse_addr, tool
from ...tools.formatting import format_callers_callees
```

- [ ] **Step 7: Update `rikugan/ida/tools/functions.py` the same way**

Find the function `format_function_summary` in `rikugan/ida/tools/functions.py` and delete its definition (23 lines including docstring and blank line after).

Find the imports block:
```python
from __future__ import annotations

import importlib
from typing import Annotated

from ...core.logging import log_debug
from ...tools.base import parse_addr, tool
```

Add a new line after `from ...tools.base import parse_addr, tool`:
```python
from ...tools.formatting import format_function_summary
```

So the imports section becomes:
```python
from __future__ import annotations

import importlib
from typing import Annotated

from ...core.logging import log_debug
from ...tools.base import parse_addr, tool
from ...tools.formatting import format_function_summary
```

- [ ] **Step 8: Delete the now-redundant shared duplicates**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git rm rikugan/tools/xrefs.py rikugan/tools/functions.py
```
Expected: 2 files removed.

- [ ] **Step 9: Update `rikugan/tools/__init__.py` docstring**

The current content is:
```python
"""Shared tool framework: @tool decorator, ToolRegistry, and security helpers.

Host-specific tool implementations live in their respective packages:
  - rikugan.ida.tools   (IDA Pro)
  - rikugan.binja.tools (Binary Ninja)
"""
```

Replace it with:
```python
"""Shared tool framework: @tool decorator, ToolRegistry, formatting helpers,
and security helpers used by all hosts.

IDA Pro tool implementations live in ``rikugan.ida.tools``. The shared
modules here are host-agnostic; IDA-specific code must not be added to
this package.
"""
```

- [ ] **Step 10: Verify IDA tool imports work**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -c "from rikugan.ida.tools.xrefs import xrefs_to, xrefs_from, function_xrefs; print('xrefs OK')"
python -c "from rikugan.ida.tools.functions import list_functions, get_function_info, search_functions; print('functions OK')"
python -c "from rikugan.tools.formatting import format_callers_callees, format_function_summary; print('formatting OK')"
```
Expected: 3 lines of `OK`.

- [ ] **Step 11: Run full CI checks**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
```
Expected: all green.

- [ ] **Step 12: Commit Phase 3**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add -A
git commit -m "refactor(tools): extract shared formatting helpers, drop duplicate IDA tools

The shared module rikugan.tools previously contained byte-near-identical
copies of rikugan.ida.tools.xrefs and rikugan.ida.tools.functions. The
copies existed only to host the two pure-text formatters
(format_callers_callees, format_function_summary) so the Binary Ninja
versions could import them. With BN gone, the copies are pure waste.

- Create rikugan/tools/formatting.py with the two formatters.
- rikugan/ida/tools/xrefs.py: delete local copy of format_callers_callees,
  add import from rikugan.tools.formatting.
- rikugan/ida/tools/functions.py: same for format_function_summary.
- Delete rikugan/tools/xrefs.py and rikugan/tools/functions.py.
- Update rikugan/tools/__init__.py docstring to reflect new layout.

Net: -219 LOC."
```
Expected: 1 commit on top of Phase 2.

---

## Phase 4: Skill Content Cleanup

**Files:**
- Modify: `rikugan/skills/builtins/deobfuscation/SKILL.md`
- Modify: any other skill with BN mentions found in Phase 0 Step 7

- [ ] **Step 1: Grep remaining skills for BN mentions**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -rIn 'binja\|Binary Ninja\|"BN"' rikugan/skills/builtins/ --include='*.md'
```
Expected: a list of files and lines.

- [ ] **Step 2: For each match found, read the context and decide**

Run `Read` on each file. For each match, choose:
- If the line is a sentence like "for BN use this; for IDA use that" → keep the IDA half, delete the BN half (or merge into one).
- If the line is a header like "## Binary Ninja" with no remaining content under it → delete the header.
- If the line is a code block with both IDA and BN examples → keep the IDA block, delete the BN block.
- If the line is a comment that mentions BN in passing → delete the comment.

- [ ] **Step 3: For `rikugan/skills/builtins/deobfuscation/SKILL.md`, apply the standard cleanup**

The deobfuscation SKILL.md is the most likely place to find BN mentions. Read it, find every "Binary Ninja" or "BN" reference, and rewrite inline. Common patterns to look for:
- "Use this approach in IDA Pro / this in Binary Ninja" → keep IDA only
- "IDA Pro and Binary Ninja both support X" → keep IDA only, drop BN clause
- Code blocks labeled `// binja` or `# BN` → delete

- [ ] **Step 4: Verify no BN mentions remain in skills**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -rIn 'binja\|Binary Ninja' rikugan/skills/builtins/ --include='*.md' | grep -v 'deobfuscation/references/binja' | grep -v 'binja-scripting' | grep -v 'smart-patch-binja'
```
Expected: no output (exit 1 from grep is fine; we want zero matches).

If matches remain, repeat Steps 2-3 for those files.

- [ ] **Step 5: Run full CI checks**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/
python -m pytest tests/ -q
```
Expected: all green.

- [ ] **Step 6: Commit Phase 4**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add -A
git commit -m "refactor(skills): strip Binary Ninja references from shared skill content

Removes BN-specific guidance from deobfuscation/SKILL.md and any other
remaining skill that referenced the now-removed host. Keeps all
IDA-specific guidance intact.

Net: -100 LOC (in-place rewrites)."
```
Expected: 1 commit on top of Phase 3.

---

## Phase 5: Test Updates

**Files:**
- Modify: `tests/core/test_host.py`
- Modify: `tests/tools/test_panel_core.py`
- Modify: `tests/tools/test_tool_widget_logic.py`
- Modify: `tests/tools/test_context_bar.py` (if affected)
- Modify: `tests/tools/test_sanitize.py` (if affected)

- [ ] **Step 1: Run baseline tests to see what passes**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m pytest tests/ -q 2>&1 | tail -20
```
Expected: all pass. Record the test count for comparison.

- [ ] **Step 2: Edit `tests/core/test_host.py` — drop BN test cases**

Read the file. Find and delete:
- Any test function whose name contains `binary_ninja`, `bn_`, or `BN`
- Any test that calls `is_binary_ninja()` or asserts on `BINARY_NINJA_AVAILABLE`
- Any test that sets `_bn_bv` or calls `set_binary_ninja_context()`

Keep all tests for `is_ida()`, `IDA_AVAILABLE`, `HAS_HEXRAYS`, `host_kind()`, `host_display_name()`.

- [ ] **Step 3: Edit `tests/tools/test_panel_core.py` — drop BN host_name usage**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -n 'Binary Ninja\|"BN"\|host_name=' tests/tools/test_panel_core.py
```
For each match:
- If a test uses `host_name="Binary Ninja"` → change to `host_name="IDA Pro"` (or remove the kwarg if `host_name` is now ignored)
- If a test asserts that `host_name="Binary Ninja"` produces a specific result → delete the test
- If a fixture is shared → check downstream tests still work

- [ ] **Step 4: Edit `tests/tools/test_tool_widget_logic.py` — same as Step 3**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -n 'Binary Ninja\|"BN"\|host_name=' tests/tools/test_tool_widget_logic.py
```
Apply the same fixes as Step 3.

- [ ] **Step 5: Edit `tests/tools/test_context_bar.py` (if affected)**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -n 'Binary Ninja\|"BN"\|host_name=' tests/tools/test_context_bar.py
```
Apply the same fixes if matches are found.

- [ ] **Step 6: Edit `tests/tools/test_sanitize.py` (if affected)**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -n 'Binary Ninja\|"BN"\|binja' tests/tools/test_sanitize.py
```
Apply the same fixes if matches are found. (This file is usually host-agnostic; BN mentions are unlikely.)

- [ ] **Step 7: Run full CI checks**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
```
Expected: all green. Test count should be close to baseline (within 5 tests, depending on what was deleted).

- [ ] **Step 8: Check coverage**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m pytest tests/ --cov=rikugan --cov-report=term-missing -q 2>&1 | tail -40
```
Expected: overall coverage ≥ 80%. The exact percentage depends on which modules are exercised by which tests, but the removal of BN code should not drop coverage below the baseline.

If coverage drops below 80%, identify the under-covered module and add a test (or accept the lower coverage as the cost of removal and document the exception in CHANGELOG.md).

- [ ] **Step 9: Commit Phase 5**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add -A
git commit -m "test(core): drop Binary Ninja test cases, ensure IDA-only coverage

Removes test cases for is_binary_ninja(), BINARY_NINJA_AVAILABLE,
set_binary_ninja_context(), and the host_name='Binary Ninja' test
parameter from test files that referenced the removed BN code path.

All surviving tests continue to pass; coverage remains >= 80%.

Net: -200 LOC (test removals + minor rewrites)."
```
Expected: 1 commit on top of Phase 4.

---

## Phase 6: Documentation Rewrite

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `ARCHITECTURE.md`
- Modify: `README.md`
- Modify: `DEVELOPMENT.md`
- Modify: `llms.txt`
- Modify: `.github/workflows/ci.yml` (if BN test job exists)
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read all docs files to see current content**

Run:
```bash
cd D:/re_dev_projects/Rikugan
wc -l AGENTS.md CLAUDE.md ARCHITECTURE.md README.md DEVELOPMENT.md llms.txt .github/workflows/ci.yml pyproject.toml CHANGELOG.md
```
Record the line counts.

- [ ] **Step 2: Edit `AGENTS.md` — rewrite to IDA-only**

Open `AGENTS.md`. The file is large (~1,200 lines). Apply these changes in order:

1. **Title and intro paragraph**: remove "Binary Ninja" mentions. The project is now IDA-only.

2. **Section "## Directory Structure"**: in the tree diagram, delete `├── binja/    — Binary Ninja host package` line and any sub-bullets describing it.

3. **Section about agents/multi-host**: find and remove any sentence like "Rikugan supports both IDA Pro and Binary Ninja" or "The dual-host architecture is described in section X".

4. **Section "## How to Add a New Host"**: delete entirely (or rename to "## How to Add New Tools" and rewrite).

5. **Section "## Threading Model"**: remove sentence "Binary Ninja's API is thread-safe — no marshalling needed".

6. **Section "## Branch Strategy"**: remove "Binary Ninja plugin manager tracks this branch directly".

7. **Key Files table**: remove any row mentioning `rikugan_binaryninja.py`, `rikugan/binja/`, or `rikugan/agent/prompts/binja.py`.

8. Run `grep -n 'Binary Ninja\|binja\|BN\b' AGENTS.md` to find anything you missed. The expected output is empty (or matches only legitimate uses of "BN" like "Binary Ninja SDK" replaced with something IDA-equivalent).

- [ ] **Step 3: Edit `CLAUDE.md` — rewrite to IDA-only**

Open `CLAUDE.md`. Apply these changes:

1. **Project Overview**: remove "Binary Ninja" from the description. Change "Rikugan is a reverse-engineering agent plugin for **IDA Pro** and **Binary Ninja**" to "Rikugan is a reverse-engineering agent plugin for **IDA Pro**".

2. **Entry points section**: remove the `rikugan_binaryninja.py` line.

3. **Branch Model section**: remove "Binary Ninja plugin manager tracks this branch directly" sentence.

4. **Windows Dev Notes section**: remove any reference to `install_binaryninja.sh/.bat`. Keep only `install_ida.sh/.bat`.

5. Run `grep -n 'Binary Ninja\|binja\|"BN"' CLAUDE.md` to verify no matches.

- [ ] **Step 4: Edit `ARCHITECTURE.md` — rewrite to IDA-only**

Open `ARCHITECTURE.md`. Apply these changes:

1. Remove any "multi-host" or "dual-host" wording.
2. Remove any "Binary Ninja" mentions in section titles or body text.
3. Update the directory tree if it includes `binja/`.
4. Run `grep -n 'Binary Ninja\|binja' ARCHITECTURE.md` to verify no matches.

- [ ] **Step 5: Edit `README.md` — rewrite to IDA-only**

Open `README.md`. Apply these changes:

1. Remove any "Binary Ninja" mentions in the project description, badges, screenshots, or installation instructions.
2. Remove any installation instructions for Binary Ninja.
3. Run `grep -n 'Binary Ninja\|binja' README.md` to verify no matches.

- [ ] **Step 6: Edit `DEVELOPMENT.md` — rewrite to IDA-only**

Open `DEVELOPMENT.md`. Apply these changes:

1. Remove any Binary Ninja-specific install/test/release instructions.
2. Run `grep -n 'Binary Ninja\|binja' DEVELOPMENT.md` to verify no matches.

- [ ] **Step 7: Edit `llms.txt` — strip BN references**

Open `llms.txt`. Apply these changes:

1. Remove any "Binary Ninja" mentions.
2. Run `grep -n 'Binary Ninja\|binja' llms.txt` to verify no matches.

- [ ] **Step 8: Edit `.github/workflows/ci.yml` — drop BN test job (if present)**

Open `.github/workflows/ci.yml`. If there is a job or step that runs tests for Binary Ninja, remove it. IDA-only test job remains.

- [ ] **Step 9: Edit `pyproject.toml` — drop dangling per-file-ignores**

Open `pyproject.toml`. Find the section:
```toml
[tool.ruff.lint.per-file-ignores]
"rikugan/binja/**" = ["F401", "E741"]
"rikugan/ida/**" = ["F401"]
"rikugan/core/sanitize.py" = ["RUF003"]
"rikugan/tools/functions.py" = ["RUF001"]
"rikugan/ui/plan_view.py" = ["RUF001"]
```

Delete these two lines (they are now dangling config that matches no files):
```toml
"rikugan/binja/**" = ["F401", "E741"]
"rikugan/tools/functions.py" = ["RUF001"]
```

Result:
```toml
[tool.ruff.lint.per-file-ignores]
"rikugan/ida/**" = ["F401"]
"rikugan/core/sanitize.py" = ["RUF003"]
"rikugan/ui/plan_view.py" = ["RUF001"]
```

- [ ] **Step 10: Edit `CHANGELOG.md` — add BN removal entry**

Open `CHANGELOG.md`. Add a new entry at the top:

```markdown
## [Unreleased] — Breaking change: Binary Ninja support removed

### Removed

- **Binary Ninja host support**: Rikugan is now IDA Pro only. The
  `rikugan/binja/` package, `rikugan_binaryninja.py` entry point,
  `install_binaryninja.{sh,bat}` installers, `plugin.json` BN manifest,
  and all BN-specific skills (`binja-scripting/`, `smart-patch-binja/`,
  deobfuscation BN references) have been deleted.

- BN host detection logic in `rikugan/core/host.py` has been removed.
  `is_binary_ninja()`, `BINARY_NINJA_AVAILABLE`,
  `set_binary_ninja_context()`, `get_binary_ninja_view()`, and
  `HOST_BINARY_NINJA` are gone. Code that imported these will need to
  remove the imports.

- BN base system prompt (`rikugan/agent/prompts/binja.py`) is gone.

### Changed

- The `rikugan/tools/` shared framework no longer carries duplicate
  copies of the IDA xrefs and functions tool modules. The shared
  formatting helpers (`format_callers_callees`, `format_function_summary`)
  now live in a new `rikugan/tools/formatting.py` module.

### Migration

- Users who installed Rikugan for Binary Ninja should keep using the
  last BN-supporting release. No upgrade path is provided.
- Users who had custom config under `~/.binaryninja/rikugan/` can
  safely delete that directory.
```

(Adjust the header format to match whatever the existing CHANGELOG.md uses — copy the format of the most recent entry above and follow it.)

- [ ] **Step 11: Verify no BN references remain in docs/config**

Run:
```bash
cd D:/re_dev_projects/Rikugan
grep -rIn 'Binary Ninja\|binja\|binaryninja' \
  AGENTS.md CLAUDE.md ARCHITECTURE.md README.md DEVELOPMENT.md llms.txt \
  .github/workflows/ci.yml pyproject.toml CHANGELOG.md
```
Expected: no output (or matches that are part of the CHANGELOG entry describing what was removed — those are intentional and OK).

- [ ] **Step 12: Run full CI checks**

Run:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
```
Expected: all green.

- [ ] **Step 13: Commit Phase 6**

Run:
```bash
cd D:/re_dev_projects/Rikugan
git add -A
git commit -m "docs: rewrite documentation for IDA-only support

Rewrites all top-level documentation to describe a single-host
IDA Pro plugin. Removes:
- AGENTS.md: 'multi-host structure' wording, 'How to Add a New Host'
  section, BN rows in Key Files table, BN thread-safety note, BN
  branch strategy mention.
- CLAUDE.md: rikugan_binaryninja.py entry, BN install instructions,
  BN config path.
- ARCHITECTURE.md: dual-host descriptions.
- README.md: BN screenshots, badges, install instructions.
- DEVELOPMENT.md: BN install/test instructions.
- llms.txt: BN mentions.
- .github/workflows/ci.yml: BN test job (if present).
- pyproject.toml: dangling per-file-ignores for rikugan/binja/** and
  rikugan/tools/functions.py.
- CHANGELOG.md: new entry documenting the breaking change."
```
Expected: 1 commit on top of Phase 5.

---

## Phase 7: Final Verification

**Files:** None (verification only; may commit small fixes if discovered).

- [ ] **Step 1: Run the full local CI script**

On Windows:
```bash
cd D:/re_dev_projects/Rikugan
python -m ruff check rikugan/ tests/
python -m mypy rikugan/core rikugan/providers
python -m pytest tests/ -q
```

(Equivalent to `./ci-local.sh` on Unix. The Windows version runs each step directly because the bash script's `uv run` invocation may not be available.)

Expected: all green.

- [ ] **Step 2: Run desloppify to check objective score**

```bash
cd D:/re_dev_projects/Rikugan
if command -v desloppify &>/dev/null; then
    desloppify scan --profile objective --no-badge
else
    echo "desloppify not installed locally; skipping"
fi
```

Expected: objective score ≥ 89.0 (the baseline documented in AGENTS.md).

If score is below baseline, identify which dimension dropped (the tool prints a breakdown), and refactor the offending module.

- [ ] **Step 3: Final grep sweep for any leftover BN references**

```bash
cd D:/re_dev_projects/Rikugan
grep -rIn 'Binary Ninja\|binja\|binaryninja' \
  rikugan/ tests/ docs/ \
  --include='*.py' --include='*.md' --include='*.yml' --include='*.json' --include='*.toml' \
  | grep -v '__pycache__' \
  | grep -v 'CHANGELOG.md' \
  | grep -v 'binja-removal-inventory.md' \
  | grep -v 'remove-binja-support-design.md' \
  | grep -v 'remove-binja-support.md'
```

Expected: no output. (We exclude the CHANGELOG, the inventory doc, the design spec, and this plan itself because they intentionally reference BN as historical context.)

If any matches remain, fix them in this phase.

- [ ] **Step 4: Smoke test the IDA import chain**

```bash
cd D:/re_dev_projects/Rikugan
python -c "
from rikugan.core.host import is_ida, host_kind, host_display_name, HAS_HEXRAYS
from rikugan.tools.formatting import format_callers_callees, format_function_summary
from rikugan.ida.tools.xrefs import xrefs_to, xrefs_from, function_xrefs
from rikugan.ida.tools.functions import list_functions, get_function_info, search_functions
from rikugan.ida.tools.registry import create_default_registry
r = create_default_registry()
assert len(r.list_tools()) > 0
print(f'OK: host_kind={host_kind()}, has_hexrays={HAS_HEXRAYS}, tools={len(r.list_tools())}')
"
```

Expected: a single `OK:` line with tool count > 0.

- [ ] **Step 5: Verify the branch is clean and ready for PR**

```bash
cd D:/re_dev_projects/Rikugan
git status
git log --oneline main..HEAD
```

Expected:
- `git status`: working tree clean
- `git log`: 8 commits total on `refactor/remove-binja-support` (Phase 0 doc + Phase 1-6 commits, plus Phase 7 if any fixes were needed)

- [ ] **Step 6: Push branch and open PR (if user confirms)**

```bash
cd D:/re_dev_projects/Rikugan
git push -u origin refactor/remove-binja-support
gh pr create --base dev --head refactor/remove-binja-support \
  --title "refactor: remove Binary Ninja support" \
  --body "Drops Binary Ninja host support entirely, focusing Rikugan on IDA Pro only. See docs/superpowers/specs/2026-06-05-remove-binja-support-design.md for the full design and docs/superpowers/plans/2026-06-05-remove-binja-support.md for the implementation plan.

Stats: -8,260 LOC, 6 phases, all CI checks green.

Breaking change: users who installed Rikugan for Binary Ninja should keep using the last BN-supporting release."
```

(Only run if the user explicitly says they want to push and open the PR. Otherwise stop here and report status.)

---

## Self-Review Checklist (run after writing this plan)

1. **Spec coverage**: Every section/requirement of the spec maps to a task here:
   - Problem Statement goals 1-6 → Phase 1 (deletions), Phase 2 (core), Phase 3 (dedup), Phase 4 (skills), Phase 5 (tests), Phase 6 (docs)
   - Section 2.1 (Phase 1 deletions) → Phase 1 Steps 1-4
   - Section 2.1b (Coordinated deletions) → Phase 2 Step 7, Phase 3 Step 8
   - Section 2.2 (Core modifications) → Phase 2 Steps 2-13
   - Section 2.3 (Dedup refactor) → Phase 3 Steps 1-9
   - Section 2.4 (Skill content) → Phase 4
   - Section 2.5 (Test updates) → Phase 5
   - Section 2.6 (Docs) → Phase 6
   - Section 7 (Success criteria) → Phase 7

2. **Placeholder scan**: No TBD/TODO/"implement later"/"add validation" placeholders. Every step has exact commands or code blocks.

3. **Type consistency**: The function names used in later steps (`format_callers_callees`, `format_function_summary`, `format_callers_callees`) match those defined in Step 3 of Phase 3. The `host_name` parameter is consistently `"IDA Pro"` everywhere.

4. **Commit hygiene**: Every phase ends with exactly one commit. No commits span multiple phases. Commit messages follow the project's `refactor/feat/fix:` convention.

5. **Verification gates**: Every phase ends with `ruff + mypy + pytest` green. Phase 7 adds desloppify and a manual smoke test.
