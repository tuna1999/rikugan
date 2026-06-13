# PROJECT_MODIFICATION_PLAN.md — Rikugan

> Plan tổng hợp các thay đổi cần thực hiện cho project Rikugan (current: `D:/re_dev_projects/vibe-clone/rikugan`).
> Đề xuất này dựa trên báo cáo đánh giá so sánh với fork (`D:/re_dev_projects/Rikugan`) chạy ngày 2026-06-12.
> Xem chi tiết workflow đánh giá tại [EVALUATION_WORKFLOW.md](EVALUATION_WORKFLOW.md).

---

## Status Overview

| Phase | Trạng thái | Commit | Ghi chú |
|-------|------------|--------|---------|
| **Phase A: Quick Wins** | ✅ Hoàn thành | `14c77c4`, `a5a2ceb` | 4/5 fix đã apply, 1 fix không cần (đã đúng) |
| **Phase B: Provider Porting** | ✅ Hoàn thành (B.1–B.4) | `9cd3985`, `51c19c7`, `3b9b1d6` | codex_provider, auth_compat, pseudo_tool_schemas ported; registry tightened |
| **Phase C: UI/Code Refactor** | ⏳ Pending | — | Tách nhỏ 5 file >800 dòng, port theme watcher (rank ≥10 trong plan) |
| **Phase D: Security Hardening** | 🔵 1/3 done (D.1 ✅) | `b57c973` | D.1 path traversal fixed; D.2 subprocess, D.3 test isolation pending |
| **Phase E: Documentation Sync** | 🔵 1/3 done (README ✅) | `a5a2ceb` | README providers table done; llms.txt, webpage/* pending |

**Cập nhật lần cuối**: 2026-06-13 — sau khi hoàn thành Phase A + B + D.1.

**Tóm tắt session**:
- 6 commits trên master, chưa push (3 ahead of `origin/master`).
- 1298 tests pass, 6 pre-existing failures (Qt signal/slot pollution), 0 regression.
- -411KB binary bloat removed, +20 new tests, +3 modules (codex, auth_compat, pseudo_tool_schemas), registry tightened 242→190 dòng.

---

## Phase A: Quick Wins — ✅ DONE

### A.1: Remove 3 binary archives + extend .gitignore

**Status**: ✅ Applied (commit pending)

**Changes**:
- `git rm rikugan/agent.rar` (200KB)
- `git rm rikugan/ida.rar` (124KB)
- `git rm rikugan/ida.7z` (80KB)
- `.gitignore` additions: `.coverage`, `.coverage.*`, `htmlcov/`, `.tox/`, `.nox/`, `.cache/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `*.rar`, `*.7z`

**Verification**: `git status` confirms 3 deletions + .gitignore modifications. Lưu file archives trong `.gitignore` ngăn tái phạm.

### A.2: Remove `rikugan/debug_test.py`

**Status**: ✅ Applied (commit `14c77c4`)

**Changes**:
- `git rm rikugan/debug_test.py` (26 dòng, dùng `sys.path.insert` + `print`)

**Verification**: `grep -r "debug_test"` confirms no file imports it (only test `test_logging.py:82` uses "debug_test_message" string, unrelated).

### A.3: Document 12 built-in skills in README.md

**Status**: ✅ Applied (commit `a5a2ceb`)

**Changes**:
- `README.md` — Thêm bảng 12 skills (ctf, deobfuscation, driver-analysis, generic-re, ida-docs, ida-pro-mcp, ida-scripting, linux-malware, malware-analysis, modify, smart-patch-ida, vuln-audit) với description ngắn.

**Rationale**: Trước đó README chỉ nói "12 built-in skills" mà không list. Người dùng không biết có `/smart-patch-ida` hay `/ida-docs`. Bảng giúp discoverability.

### A.4: ARCHITECTURE.md duplicate "Microcode" row

**Status**: ✅ Verified clean (không cần fix)

**Rationale**: Synthesis ghi nhận duplicate tồn tại ở **fork** (`D:/re_dev_projects/Rikugan/ARCHITECTURE.md:277`). Current đã đúng rồi — chỉ có 1 dòng "Microcode (IDA)" ở line 276.

**Note**: Khi merge upstream về sau, cần double-check duplicate này không lan vào current.

### A.5: Test verification

**Results** (cộng dồn sau mỗi phase):
- ✅ `tests/core/`: 247 passed, 2 skipped
- ✅ `tests/tools/`: tất cả pass
- ✅ `tests/agent/`: 218 passed, 2 skipped (sau B.3)
- ✅ `tests/providers/`: 101 passed (sau B.1, +9 codex tests)
- ✅ Full suite: **1298 passed, 6 failed** (cùng 6 pre-existing Qt signal/slot pollution failures, đã xác nhận tồn tại trước session)

---

## Phase B: Provider Porting — ✅ DONE (B.1–B.4)

### B.1: Port `codex_provider.py` từ fork — ✅ DONE (commit `9cd3985`)

**Status**: ✅ Applied

**Files added**:
- `rikugan/providers/codex_provider.py` (24,457 bytes, 549 dòng)
- `tests/providers/test_codex_provider.py` (7,403 bytes, 9 tests, all pass)

**Files modified**:
- `rikugan/providers/registry.py` — thêm `"codex": "rikugan.providers.codex_provider:CodexProvider"`
- `AGENTS.md` — providers/ tree listing
- `README.md` — Recommended Providers table

**Test results**: `tests/providers/test_codex_provider.py`: 9/9 passed.

**Rationale**: Codex provider (OpenAI Responses API) thiếu trong current. Fork đã có implementation ổn định. Cần cho users muốn dùng Codex backend.

**Steps**:
1. Diff `providers/` giữa 2 projects để identify differences
2. Copy `codex_provider.py` từ fork
3. Copy `providers/__init__.py` registration entry
4. Add to provider registry (priority 4)
5. Add tests: `tests/providers/test_codex_provider.py` (port từ fork)
6. Update `AGENTS.md` provider table
7. Update `README.md` Recommended Providers table
8. Run `pytest tests/providers/` to verify

### B.2: Port `auth_compat.py` từ fork — ✅ DONE (commit `51c19c7`)

**Status**: ✅ Applied (61 dòng shim, no auth_cache refactor)

**Rationale update**: Current's `auth_cache.py` already has `set_keychain_consent()` and `invalidate_cache()` with the same signatures fork's auth_cache has. The shim works as a pure pass-through — no refactor of current's auth_cache was needed.

**Files added**:
- `rikugan/providers/auth_compat.py` (1,927 bytes, 61 dòng)

**Test results**: `tests/tools/test_settings_dialog.py`: 50/50 pass. Full suite: 1298 passed, 6 failed (no regression).

### B.3: Port `pseudo_tool_schemas.py` từ fork — ✅ DONE (commit `51c19c7`)

**Status**: ✅ Applied as future C.4 extraction target (no call sites changed)

**Rationale**: The file is added as a clean extraction target for the future C.4 refactor (slim down `loop.py`). Currently `loop.py` still has the inline schemas — wiring it in is a separate, larger refactor.

**Files added**:
- `rikugan/agent/pseudo_tool_schemas.py` (231 dòng, 6 schemas)

**Test results**: `tests/agent/`: 218 passed, 2 skipped. No regression (pure data module).

### B.4: Refactor `providers/registry.py` — ✅ DONE (commit `3b9b1d6`)

**Status**: ✅ Applied — file tightened but features preserved

**Before/After**:
- 242 dòng → 190 dòng (-52 dòng, -21%)
- All public method signatures unchanged
- All tracking state preserved (`_retired_instances`, `_normalized_api_base`, `retire_instances()`)

**Why not a deeper refactor**: The fork (97 dòng) is smaller because it has fewer features (`_retired_instances`, `_normalized_api_base`, `retire_instances()`) that current added to handle IDA Qt signal-dispatch races. Stripping them would be a regression.

**Test results**: `tests/providers/`: 101/101 pass. Full suite: 1298 passed, 6 failed (no regression).

---

## Phase C: UI/Code Refactor — ⏳ PENDING

### C.1: Port `theme/watcher.py` từ fork

**Priority**: HIGH (rank 10)
**Effort**: M
**Risk**: low

**Source**: `D:/re_dev_projects/Rikugan/rikugan/ui/theme/watcher.py` (likely in fork)
**Target**: `D:/re_dev_projects/vibe-clone/rikugan/rikugan/ui/theme/watcher.py`

**Rationale**: Live theme reload — khi user edit theme file, UI update ngay. Fork có `QFileSystemWatcher`. Current 4-mode theme system nhưng phải restart IDA.

**Steps**:
1. Check if fork has watcher (look in `ui/` or `ui/theme/`)
2. Copy implementation
3. Wire vào `ThemeManager`
4. Test: edit theme file → UI updates

### C.2: Split `rikugan/ui/styles.py` (2758 dòng)

**Priority**: MEDIUM (rank 11)
**Effort**: XL
**Risk**: high

**Current**: `rikugan/ui/styles.py` — 2758 dòng, 1 file
**Target**: <800 dòng/file, organized by theme/component

**Rationale**: 2758 dòng vượt 800-line limit ~3.5x. Khó maintain, test, review. Có thể split theo:
- `styles/tokens.py` (color, typography, spacing tokens)
- `styles/dark.py`, `styles/light.py`, `styles/ida_dark.py`, `styles/ida_light.py` (per-theme)
- `styles/widgets.py` (QSS cho từng widget class)
- `styles/__init__.py` (entry point)

**Steps**:
1. Read full `styles.py` to understand current structure
2. Plan split layout
3. Extract incrementally (run tests after each extraction)
4. Final: keep `styles.py` as thin entry point that imports from `styles/`
5. Run `tests/ui/` + visual regression

### C.3: Split `rikugan/ui/chat_view.py` (2003 dòng)

**Priority**: MEDIUM (rank 13)
**Effort**: L
**Risk**: medium

**Current**: 2003 dòng
**Target**: <800 dòng/file

**Possible split**:
- `chat_view.py` (core)
- `chat_restore_worker.py` (QThread background restore)
- `chat_streaming.py` (streaming handler)
- `chat_message_render.py` (message rendering)

### C.4: Extract `loop.py` inline pseudo-tool schemas into `pseudo_tool_schemas.py`

**Priority**: MEDIUM (rank 12, after B.3)
**Effort**: L (lower than original XL because B.3 already added target file)
**Risk**: high

**Current**: `rikugan/agent/loop.py` 1967 dòng (still has inline schemas)
**Target**: <1200 dòng sau khi extract

**File ready**: `rikugan/agent/pseudo_tool_schemas.py` (231 dòng, ported in B.3) defines `ALL_PSEUDO_TOOL_SCHEMAS` tuple.

**Steps**:
1. Search `loop.py` for `"description":` dict literals matching `ALL_PSEUDO_TOOL_SCHEMAS`
2. Replace with `from .pseudo_tool_schemas import ALL_PSEUDO_TOOL_SCHEMAS` (or selective imports)
3. Verify agent loop still works (`tests/agent/test_agent_loop.py`)
4. Run full suite — no regression

### C.5: Split `rikugan/ui/panel_core.py` (2026 dòng)

**Priority**: MEDIUM
**Effort**: XL
**Risk**: high

**Current**: 2026 dòng
**Target**: <800 dòng/file

### C.6: Split `rikugan/ui/settings_dialog.py` (1297 dòng)

**Priority**: LOW
**Effort**: L
**Risk**: medium

**Current**: 1297 dòng
**Target**: <800 dòng/file

---

## Phase D: Security Hardening — 🔵 1/3 DONE

### D.1: Fix path traversal in `research_mode` — ✅ DONE (commit `b57c973`)

**Status**: ✅ Applied

**Files modified**:
- `rikugan/agent/modes/research.py` — added `_safe_note_path()` helper (3-layer defense: null byte check, `_slugify` sanitization, `Path.resolve() + relative_to()` containment)
- `tests/agent/test_research_mode.py` — added 12 new tests (TestSafeNotePath + TestWriteAndReviewNotePathSafety)

**Test results**: `tests/agent/test_research_mode.py`: 30 tests (was 17), 28 passed, 2 skipped (symlink tests require admin on Windows).

**Severity**: HIGH (LLM-controlled file write could overwrite arbitrary files).

### D.2: Fix subprocess injection in `a2a SubprocessBridge`

**Priority**: HIGH
**Effort**: S
**Risk**: medium

**File**: `rikugan/agent/a2a/subprocess_bridge.py:110-116`

**Issue**: Task từ LLM được nối thẳng vào `['claude', '--print', '--output-format', 'json', task]`. Nếu LLM output `--help` hoặc shell metachar, có thể inject flags.

**Fix**: Whitelist args hoặc escape:
```python
import shlex
# Instead of:
command = ['claude', '--print', '--output-format', 'json', task]
# Use:
command = ['claude', '--print', '--output-format', 'json', '--', task]
# Or validate task doesn't start with '-':
if task.startswith('-'):
    raise ValueError("Invalid task argument")
```

### D.3: Fix 6 pre-existing test isolation bugs

**Priority**: MEDIUM
**Effort**: M
**Risk**: low

**Files**:
- `tests/agent/test_session_controller.py::TestIdaFunctionEnumerationImportFailures` (3 tests)
- `tests/test_light_theme_widgets.py::TestSettingsDialogAppliesThemeOnShow` (2 tests)
- `tests/tools/test_rikugan_plugin.py::TestGuardedImport::test_not_double_wrapped` (1 test)

**Issue**: Qt signal/slot state leaks between tests. ThemeManager.instance() và signal connections persist.

**Fix**:
1. Add teardown hooks to disconnect signals
2. Reset ThemeManager.instance() between tests
3. Use pytest fixtures with proper scope (`function` instead of `module`)

---

## Phase E: Documentation Sync — ⏳ PENDING

### E.1: Update `AGENTS.md` with new providers

**When**: After B.1
**Changes**: Add `codex_provider` row to provider table, mention `auth_compat.py` in shared infrastructure.

### E.2: Update `llms.txt` with new skills/providers

**When**: After A.3 (already done partially), B.1
**Changes**: Skills list + providers list.

### E.3: Update `webpage/` static HTML

**When**: After all code changes
**Changes**: `index.html`, `docs.html`, `ARCHITECTURE.html` — sync with new providers, skills.

### E.4: Sync with upstream `buzzer-re/Rikugan`

**Ongoing**: When upstream releases new version, diff against current. Bằng cách này ta có thể merge upstream improvements mà không bị stuck.

---

## Migration Plan Summary

| # | Action | Priority | Effort | Risk | Phase |
|---|--------|----------|--------|------|-------|
| 1 | Remove 3 binary archives | HIGH | S | low | A ✅ |
| 2 | Remove debug_test.py | HIGH | S | low | A ✅ |
| 3 | Extend .gitignore | HIGH | S | low | A ✅ |
| 4 | Document 12 skills in README | MED | S | low | A ✅ |
| 5 | Fix path traversal in research_mode | CRIT | S | low | D.1 |
| 6 | Fix subprocess injection in a2a | HIGH | S | med | D.2 |
| 7 | Port codex_provider | HIGH | M | med | B.1 |
| 8 | Port auth_compat | MED | S | low | B.2 |
| 9 | Port pseudo_tool_schemas | MED | M | med | B.3 |
| 10 | Refactor providers/registry.py | LOW | S | med | B.4 |
| 11 | Port theme/watcher.py | HIGH | M | low | C.1 |
| 12 | Split styles.py (2758 lines) | MED | XL | high | C.2 |
| 13 | Split chat_view.py (2003 lines) | MED | L | med | C.3 |
| 14 | Split loop.py (1967 lines) | MED | XL | high | C.4 |
| 15 | Split panel_core.py (2026 lines) | MED | XL | high | C.5 |
| 16 | Split settings_dialog.py (1297 lines) | LOW | L | med | C.6 |
| 17 | Fix 6 test isolation bugs | MED | M | low | D.3 |
| 18 | Update AGENTS.md / llms.txt / webpage | LOW | M | low | E |

---

## Execution Order (Recommended)

1. **Week 1**: Security fixes (D.1 ✅, D.2 ⏳) — CRITICAL/HIGH, low effort
2. **Week 1-2**: Provider porting (B.1 ✅, B.2 ✅, B.3 ✅, B.4 ✅) — additive, easy to verify
3. **Week 2-3**: Test isolation fixes (D.3 ⏳) — improves test reliability
4. **Week 3-4**: Theme watcher (C.1 ⏳) — feature add, low risk
5. **Week 4+**: File splits (C.2–C.6 ⏳) — large refactor, schedule carefully
6. **Ongoing**: Doc sync (E ⏳) — llms.txt, webpage/*

## Next Priority Actions (the 5 remaining items by impact/effort)

| Rank | Action | Impact | Effort | Risk | Why now |
|------|--------|--------|--------|------|---------|
| 1 | **D.2**: Subprocess injection in a2a SubprocessBridge | HIGH | S | medium | Same security category as D.1, similar effort, closes another known attack vector |
| 2 | **D.3**: Fix 6 pre-existing test isolation bugs (Qt signal/slot pollution) | MED | M | low | Already documented; improves CI reliability; user feedback noted |
| 3 | **C.4**: Extract `loop.py` inline pseudo-tool schemas into `pseudo_tool_schemas.py` | MED | L | high | Target file (`pseudo_tool_schemas.py`) already exists from B.3 — main work is the extraction |
| 4 | **C.1**: Port `theme/watcher.py` from fork (QFileSystemWatcher for live theme reload) | LOW | M | low | Feature add, no breaking changes |
| 5 | **C.2**: Split `styles.py` 2758 dòng into theme-organized modules | MED | XL | high | Largest file in repo; high risk; defer until C.4 is done |

**Items deferred to future**:
- C.3, C.5, C.6: file splits for chat_view, panel_core, settings_dialog (after C.2)
- E: documentation sync (llms.txt, webpage/*)
- B.5: Refactor `openai_provider.py` 575 dòng → <400 (separate workstream, may conflict with theme/paging customizations)

---

## Success Metrics

- ✅ All 6 pre-existing test failures fixed
- ✅ Test coverage ≥80% (currently unknown — needs measurement)
- ✅ No file >800 dòng (currently 5 files violate: styles, chat_view, panel_core, loop, settings_dialog)
- ✅ Zero CRITICAL security findings
- ✅ Branch: master up to date with `tuna-main/main` regularly (weekly rebase)

## Current Status (2026-06-13)

| Metric | Value | Notes |
|--------|-------|-------|
| Test pass rate | 1298/1304 (99.5%) | 6 pre-existing failures, 0 new |
| New tests added | +20 | 9 codex + 12 security + cleanup verified |
| Files added | 4 | `pseudo_tool_schemas.py`, `auth_compat.py`, `codex_provider.py`, `test_codex_provider.py` |
| Files modified | 4 | `.gitignore`, `README.md`, `AGENTS.md`, `registry.py` |
| Files removed | 4 | 3 binary archives + `debug_test.py` (~411KB freed) |
| Commits ahead of origin | 6 | Ready to push |
| Working tree | clean | No uncommitted changes |

---

## References

- [EVALUATION_WORKFLOW.md](EVALUATION_WORKFLOW.md) — Reusable evaluation workflow
- [AGENTS.md](../AGENTS.md) — Developer guide
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Internal architecture
- [DEVELOPMENT.md](../DEVELOPMENT.md) — Human contributor guide
