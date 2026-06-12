# Fixing Plan: Regression Review Before Commit

## Verdict

Not ready for commit. Targeted pytest coverage is mostly green, but review and live IDA testing found confirmed runtime regressions in theme signal wiring, OpenAI streaming tool-call handling, light-theme styling, plus commit-readiness issues in IDA enumeration cleanup, lint, whitespace, and staged/untracked file state.

Do not commit until all fix steps and the final verification checklist pass.

## Review evidence

Commands run from `C:\Users\kiennd14\.rikugan`:

```powershell
python -m pytest tests/providers/test_openai_provider.py -q
python -m pytest tests/agent/test_session_controller.py -q
python -m pytest tests/ui/test_chat_view_restore.py -q
python -m pytest tests/agent/test_session_controller.py tests/headless/test_provider_config.py tests/tools/test_panel_core.py tests/ui/test_chat_view_restore.py -q
python -m ruff check rikugan/ui/markdown.py rikugan/ui/highlight.py rikugan/ui/styles.py rikugan/ui/chat_view.py rikugan/ui/session_controller_base.py rikugan/ui/panel_core.py rikugan/ui/theme/manager.py tests/ui/test_chat_view_restore.py tests/tools/test_panel_core.py tests/agent/test_session_controller.py tests/qt_stubs.py
git diff --check
git status --short
```

Observed results:

- `tests/providers/test_openai_provider.py`: 13 passed.
- `tests/agent/test_session_controller.py`: 23 passed.
- `tests/ui/test_chat_view_restore.py`: 33 passed.
- Combined targeted run: 161 passed.
- Manual OpenAI streaming reproduction confirmed that when argument bytes arrive before the tool-call id, only the later argument fragment is emitted to the consumer; the earlier buffered fragment is dropped.
- Live IDA traceback shows async restore crashes while constructing restored message widgets:
  - `UserMessageWidget.__init__` calls `ThemeManager.instance().themeChanged.connect(...)`.
  - `_ThinkingBlock.__init__` calls the same pattern.
  - Runtime error: `AttributeError: 'PySide6.QtCore.Signal' object has no attribute 'connect'`.
- User-visible theme regression: in light/white theme, settings UI and chat input show mixed black boxes on otherwise white UI.
- Focused ruff failed on changed tests:
  - `tests/agent/test_session_controller.py:16-18` E402.
  - `tests/tools/test_panel_core.py:34` RUF100, `:179` UP037, `:203` and `:224` I001 or E402, `:924` F401.
- `git diff --check` failed: `tests/headless/test_provider_config.py:424: new blank line at EOF`.
- `git status --short` shows `tests/conftest.py` untracked and several partially staged `AM` paths. A commit made from the current staged set would be incomplete.

## Fix steps

### 1. Fix ThemeManager signal wiring in real PySide6

**Files:**

- `rikugan/ui/theme/manager.py`
- `rikugan/ui/message_widgets.py` only if a temporary defensive helper is needed
- `tests/ui/test_chat_view_restore.py` or a new dedicated theme-manager regression test
- `tests/tools/test_panel_core.py` / `tests/tools/test_settings_dialog.py` if stubs need updates

**Problem:**

`ThemeManager.__init__()` assigns `self.themeChanged = Signal(object)` in real Qt mode. A PySide6 `Signal` works as a descriptor only when declared on the QObject subclass; when assigned to an instance it remains an unbound `Signal` object and does not expose `.connect`. This causes restored chat messages to crash as soon as `UserMessageWidget` or `_ThinkingBlock` subscribes to `themeChanged`.

The current code comment says instance-local signals are intentional, but that approach is invalid for real PySide6. Instance-local signal replacement is only safe for the no-Qt/dummy fallback.

**Required implementation:**

- Keep a class-level `themeChanged = Signal(object)` for real Qt/PySide6. Do not shadow it with `self.themeChanged = Signal(object)` in `__init__` when `_HAS_QT` is true.
- For the no-Qt/dummy fallback, keep or add instance-local `_DummySignal` so `ThemeManager.reset()` does not retain old listeners across singleton resets.
- Ensure `ThemeManager.instance().themeChanged.connect(...)` works in real PySide6 and in the stub/no-Qt fallback.
- Ensure `_apply_now()` emits through the bound signal in both modes.
- Add a regression test that fails on the current code. Preferred coverage:
  - In a real PySide6-capable test, reset/create `ThemeManager`, assert `hasattr(ThemeManager.instance().themeChanged, 'connect')`, connect a listener, call `set_mode(ThemeMode.LIGHT)` or `_apply_now()`, and assert the listener runs.
  - Construct `UserMessageWidget` and `_ThinkingBlock` under a QApplication and assert no `AttributeError` occurs when they subscribe to `themeChanged`.
  - In fallback/stub mode, reset manager and assert old dummy listeners are not retained.

**Goal for completion:**

The provided IDA traceback cannot occur: `ThemeManager.instance().themeChanged` is always a bound signal-like object with `.connect`, and restored user/thinking widgets construct successfully.

### 2. Fix light-theme black boxes in settings dialog and chat input

**Files:**

- `rikugan/ui/settings_dialog.py`
- `rikugan/ui/input_area.py`
- `rikugan/ui/panel_core.py` if input styling is centrally applied there
- `rikugan/ui/styles.py` if new reusable style helpers are added
- `tests/tools/test_settings_dialog.py`
- `tests/tools/test_input_area.py` or `tests/tools/test_panel_core.py`

**Problem:**

In light/white theme, parts of the settings dialog and chat input still render with black/dark backgrounds. This likely happens because some widgets rely on the host/IDA palette or stale default Qt palette instead of explicit ThemeTokens when the user selected Rikugan Light mode. The settings dialog builds many QLineEdit/QComboBox/QTabWidget/QGroupBox controls without applying a light-token stylesheet, and `InputArea` currently has no theme-aware stylesheet or subscription.

**Required implementation:**

- Add a clear theme-style application path for SettingsDialog, for example `_apply_theme_styles()`:
  - Read `ThemeManager.instance().tokens()`.
  - For non-host themes (`light`/`dark`), apply QSS for `QDialog`, `QWidget`, `QGroupBox`, `QTabWidget`, `QTabBar`, `QLineEdit`, `QComboBox`, `QSpinBox`, `QDoubleSpinBox`, `QPlainTextEdit` if present, `QCheckBox`, `QLabel`, and dialog buttons using token fields (`base`, `alt_base`, `text`, `button`, `button_text`, `mid`, `highlight`, `highlight_text`).
  - For host/IDA native mode, avoid overriding the host palette or use only safe host fallback styling.
  - Call it after `_build_ui()` and after the theme combo changes.
  - Subscribe the dialog to `ThemeManager.themeChanged` safely and disconnect/ignore after close if needed.
- Add a theme-aware stylesheet path for `InputArea` and its skill popup:
  - Use `tokens.base` / `tokens.text` for the editor background/text.
  - Use a visible border from `tokens.mid` and focus border from `tokens.highlight`.
  - Use `tokens.alt_base` for the popup background and `tokens.highlight`/`highlight_text` for selected items.
  - Apply on construction and re-apply on `themeChanged`, or have `panel_core._on_theme_changed()` call an `InputArea.apply_theme()` method.
- Avoid hard-coded `black`, `#000`, or dark fallback colors in the light-theme path unless they are strictly text colors on a light background and pass contrast.
- Make sure the fix does not reintroduce broad global QWidget selectors that bleed into the rest of IDA.

**Required regression tests:**

- Settings dialog light-theme test:
  - Force `ThemeManager` to `ThemeMode.LIGHT` and legacy styles to light if needed.
  - Construct `SettingsDialog` or call its style helper directly.
  - Assert the applied stylesheet contains light tokens such as `LIGHT_TOKENS.base`/`LIGHT_TOKENS.alt_base` and text token `LIGHT_TOKENS.text`.
  - Assert editable controls (`QLineEdit`, `QComboBox`, spin boxes) are covered by explicit selectors.
  - Assert the light-theme stylesheet does not contain `background: #000`, `background-color: #000`, or `background: black` for settings/input controls.
- Input area light-theme test:
  - Construct `InputArea` under light mode or call its style builder.
  - Assert its stylesheet includes light background and dark text tokens.
  - If the popup has a separate style builder, assert popup unselected background uses `alt_base`/`base` and selected background uses `highlight`, not black.
- Theme-change test:
  - Switch from dark to light and assert SettingsDialog/InputArea styles update, preventing stale dark QSS from remaining after the user selects white theme.

**Goal for completion:**

In Rikugan Light mode, settings and input areas have white/light backgrounds and readable dark text with no black rectangles. Tests fail if these widgets fall back to black/dark backgrounds or fail to refresh after a theme switch.

### 3. Fix OpenAI streamed tool-call arguments when the id arrives late

**Files:**

- `rikugan/providers/openai_provider.py`
- `tests/providers/test_openai_provider.py`

**Problem:**

`OpenAIProvider._stream_chunks()` buffers `tc_delta.function.arguments` into per-index state when a provider emits arguments before a non-empty tool-call id, but it only yields `tool_args_delta` while an id is already present. When the id appears later, the provider emits a start chunk but never replays the earlier buffered arguments. The agent loop then assembles a tool call with missing or truncated JSON arguments.

**Required implementation:**

- Track how much buffered argument text has already been emitted for each tool-call index, for example `emitted_args_len` on each `current_tool_calls[idx]` entry.
- Process each tool-call delta in this order:
  1. Ensure the per-index state exists.
  2. Update late id and late function name values.
  3. Append any new function-argument fragment to the buffered args string.
  4. If a non-empty id is now available and no start has been emitted for that id, emit exactly one `is_tool_call_start` chunk.
  5. If a non-empty id is available, emit only `args[emitted_args_len:]` as `tool_args_delta` when that substring is non-empty, then update `emitted_args_len`.
- Preserve existing duplicate start, duplicate end, duplicate finish-reason, and cumulative usage behavior.
- Move the local `import uuid as _uuid` in `_format_messages()` to a module-level `import uuid` while touching this file.
- Add a focused streaming test for late-id args:
  - first delta: index 0, no id, name `f`, first argument fragment;
  - second delta: index 0, id `call_1`, second argument fragment;
  - final chunk: finish reason `tool_calls`.
- Assert there is exactly one start for `call_1`, exactly one end for `call_1`, and concatenated emitted argument deltas include both fragments in order.

**Goal for completion:**

The new late-id streaming test fails on the current code and passes after the fix. Manual inspection of emitted chunks shows no argument text is lost when id arrives after argument bytes.

### 4. Restore defensive IDA enumeration cleanup on import failures

**Files:**

- `rikugan/ida/ui/session_controller.py`
- `tests/agent/test_session_controller.py` or a new IDA-controller test module

**Problem:**

The refactored chunked function enumeration imports `idautils`, `ida_funcs`, and `ida_name` directly. The old code cleared enumeration state before re-raising `ImportError`. The new code can leave stale `_funcs_iter` state if an IDA module disappears or is unavailable partway through enumeration. `get_function_count()` and `list_functions_raw()` also propagate missing-IDAModule exceptions without logging, which is acceptable only if callers explicitly handle that contract.

**Required implementation:**

- In `begin_function_enumeration()`, wrap `importlib.import_module('idautils')` in `try/except ImportError`, set `self._funcs_iter = None`, log with `log_debug`, then re-raise.
- In `next_function_chunk()`, wrap imports of `ida_funcs` and `ida_name` similarly, clear `_funcs_iter`, log, then re-raise.
- Keep `ida_segment` optional and best-effort.
- Add tests that monkeypatch `importlib.import_module` so:
  - `begin_function_enumeration()` fails to import `idautils` and leaves `_funcs_iter is None`;
  - `next_function_chunk()` starts with a fake iterator but fails to import `ida_funcs` or `ida_name`, then leaves `_funcs_iter is None`.
- If the intended contract is graceful empty results instead of re-raising, document that and update callers/tests consistently. Otherwise, keep re-raise for compatibility with the older code.

**Goal for completion:**

A failed IDA import never leaves an active or stale enumeration iterator. Tests pin the intended import-failure behavior.

### 5. Fix lint failures in changed tests

**Files:**

- `tests/agent/test_session_controller.py`
- `tests/tools/test_panel_core.py`

**Problem:**

Focused ruff currently fails on changed test files. Even when pytest is green, the diff is not ready if lint is part of the project gate.

**Required implementation:**

- In `tests/agent/test_session_controller.py`, add explicit `# noqa: E402` to module-level rikugan imports that must run after `install_ida_mocks()`, or restructure setup so imports are ruff-clean without breaking the mock installation order.
- In `tests/tools/test_panel_core.py`:
  - remove the unused `D401` noqa on `_StubModule.__getattr__`;
  - remove quotes from `_StubThemeManager | None` now that future annotations are active;
  - move or annotate the late `import pytest` so ruff accepts the deliberate post-stub import order;
  - sort the `from rikugan.ui.panel_core import ...` block;
  - remove the unused `import rikugan.ui.panel_core as _panel_core_mod` in `test_shutdown_disconnects_theme_changed`.
- Prefer minimal lint-only edits; do not change test semantics.

**Goal for completion:**

The focused ruff command from the verification section passes.

### 6. Fix whitespace error in provider-config test

**Files:**

- `tests/headless/test_provider_config.py`

**Problem:**

`git diff --check` reports a new blank line at EOF.

**Required implementation:**

- Remove the extra trailing blank line at the end of the file.
- Re-run `git diff --check`.

**Goal for completion:**

`git diff --check` reports no whitespace errors.

### 7. Make staged and unstaged changes coherent before commit

**Files:**

- Repository staging area, especially:
  - `tests/conftest.py`
  - `rikugan/ui/theme/manager.py`
  - `tests/ui/test_chat_view_restore.py`
  - all new UI/theme files

**Problem:**

The current tree has an untracked required file and multiple `AM` paths. Some files are staged, then modified again. A commit from the current index would omit required fixes and test infrastructure.

**Required implementation:**

- Do not commit until after all code fixes and verification are complete.
- Stage `tests/conftest.py`; it is required for stub purge behavior.
- For every `AM` or partially staged file, inspect `git diff` and `git diff --cached`; stage the final intended version only after reviewing it.
- Confirm no local-only artifacts, secrets, generated caches, or accidental config files are staged.

**Goal for completion:**

`git status --short` shows only intentional tracked changes, no `?? tests/conftest.py`, and no accidental partial staging. The final staged diff is the exact diff intended for commit.

### 8. Replace or remove the green-paint duplicate-tool-call test

**Files:**

- `rikugan/tests/test_settings_dialog_fixes.py`
- optionally `rikugan/agent/loop.py` if extracting a helper is the cleanest route

**Problem:**

`TestAgentLoopDuplicateToolCallIdGuard.test_duplicate_end_chunks_return_one_tool_call` constructs `AgentLoop.__new__(AgentLoop)` and discards it, then manually copies the dedupe logic inside the test instead of exercising production code. This can pass while production regresses.

**Required implementation:**

Choose one:

- Extract a small production helper for duplicate `tool_call_end` handling and test that helper directly; or
- Build a minimal fake provider/session path that drives `AgentLoop` streaming logic enough to produce duplicate end chunks and assert only one `ToolCall` is persisted; or
- Remove this test if reliable production-path coverage already exists elsewhere, and replace it with a focused provider streaming test from step 3.

**Goal for completion:**

No test merely reimplements the production guard in test code. The remaining test fails if the production duplicate-end guard is removed or broken.

### 9. Keep optional fixture/test-data behavior safe

**Files:**

- Only applicable if new integration tests with binary fixtures are added.

**Problem:**

No `optional_test_data_path` implementation exists today. Future integration tests must not make default CI depend on local binary samples.

**Required implementation:**

- If optional fixture tests are added, gate them behind an environment variable or fixture such as `optional_test_data_path`.
- Skip or return early when the path is not configured.
- Preserve existing early-return guards in runtime initialization paths; do not move heavy startup work before cancellation or shutdown checks.

**Goal for completion:**

Default test runs pass without local binary fixtures. Optional fixture tests skip cleanly when their path is absent.

## Final verification checklist

Run from `C:\Users\kiennd14\.rikugan` after implementing all fixes:

```powershell
python -m pytest tests/providers/test_openai_provider.py -q
python -m pytest tests/agent/test_session_controller.py tests/headless/test_provider_config.py tests/tools/test_panel_core.py tests/ui/test_chat_view_restore.py -q
python -m pytest tests/tools/test_settings_dialog.py tests/tools/test_chat_view.py tests/tools/test_input_area.py tests/tools/test_markdown.py tests/tools/test_mutation_log_view.py -q
python -m pytest rikugan/tests/test_settings_dialog_fixes.py -q
python -m ruff check rikugan/providers/openai_provider.py rikugan/ida/ui/session_controller.py rikugan/ui/theme/manager.py rikugan/ui/message_widgets.py rikugan/ui/settings_dialog.py rikugan/ui/input_area.py rikugan/ui/markdown.py rikugan/ui/highlight.py rikugan/ui/styles.py rikugan/ui/chat_view.py rikugan/ui/session_controller_base.py rikugan/ui/panel_core.py tests/ui/test_chat_view_restore.py tests/tools/test_panel_core.py tests/tools/test_settings_dialog.py tests/tools/test_input_area.py tests/agent/test_session_controller.py tests/providers/test_openai_provider.py tests/qt_stubs.py
git diff --check
git status --short
git diff --cached --stat
git diff --stat
```

Success criteria:

- All listed pytest commands pass.
- Focused ruff passes.
- `git diff --check` reports no whitespace errors.
- Real PySide6 smoke coverage proves `ThemeManager.instance().themeChanged.connect` works and message widgets construct without the reported AttributeError.
- Light-theme regression tests prove settings and input do not render black/dark backgrounds in Rikugan Light mode and refresh after theme changes.
- `git status --short` shows only intentional files, with no untracked required files and no accidental local-only artifacts.
- Staged and unstaged changes are coherent before committing; do not commit a partial staged tree by accident.

## Prompt for the coding agent

Use this prompt:

```text
You are fixing a Python/Qt repository before commit. Read `.kilo/fixing-plan.md` and implement every required fix step in order. Do not create a git commit.

Key goals:
1. Fix the real PySide6 ThemeManager signal regression. `ThemeManager.instance().themeChanged.connect(...)` must work in real Qt and in fallback/stub tests. Add regression coverage that constructs `UserMessageWidget` and `_ThinkingBlock` or otherwise proves the reported AttributeError cannot happen.
2. Fix the light/white theme black-box regression in settings and chat input. Apply explicit ThemeTokens-based styles for SettingsDialog and InputArea in non-host light/dark modes, refresh them on theme changes, and add regression tests proving light mode uses light backgrounds/readable text with no black boxes.
3. Fix `OpenAIProvider._stream_chunks()` so streamed tool-call argument fragments are never lost when the tool-call id arrives after the first argument fragment. Add a focused failing-then-passing test for the late-id argument replay case. Preserve duplicate start/end suppression and cumulative usage behavior.
4. Restore defensive cleanup in `IdaSessionController` function enumeration when required IDA modules cannot be imported, and add tests that state is cleared on import failure.
5. Fix current focused ruff failures in `tests/agent/test_session_controller.py` and `tests/tools/test_panel_core.py` without changing test semantics.
6. Remove the blank-line-at-EOF whitespace issue in `tests/headless/test_provider_config.py`.
7. Make the staging area coherent: include `tests/conftest.py`, resolve `AM` paths, and avoid committing partial staged versions or local-only artifacts.
8. Replace or remove the duplicate-tool-call green-paint test in `rikugan/tests/test_settings_dialog_fixes.py` so coverage exercises production code or a real production helper.
9. If you add optional binary fixture tests, gate them behind `optional_test_data_path` or equivalent and skip or return early when absent.

After changes, run the verification commands in `.kilo/fixing-plan.md`. Return a concise summary of changed files, test results, and any remaining risks. Do not stage or commit unless explicitly asked.
```
