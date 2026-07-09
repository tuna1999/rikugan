# Execute Python Unified Widget + Docs-Review Display — Design Spec

**Date:** 2026-07-09
**Status:** Approved (Approach A — Unified ExecutePythonWidget; hard-block docs gate)
**Branch target:** `feat/execute-python-unified-widget`
**Origin:** Bug reports về hiển thị `execute_python` — block bị 2 khoảng trống
lớn, approval block có dòng code redundant, docs-review message trộn vào
assistant bubble.

---

## Context

`execute_python` hiện trải qua **3 luồng event tách biệt** để hiển thị trên chat:

1. `TOOL_CALL_START` → tạo `ToolCallWidget` (hiện args + result)
2. `TEXT_DELTA` từ `_review_complex_idapython_script()` → trộn vào
   `AssistantMessageWidget` (cùng bubble với text LLM)
3. `TOOL_APPROVAL_REQUEST` → tạo `ToolApprovalWidget` thứ 2 (riêng biệt)

Hậu quả quan sát được (qua screenshot 2026-07-09):

| Ảnh | Vấn đề | Nguyên nhân |
|------|--------|-------------|
| Image #2 | Block `execute_python` bị 2 khoảng trống lớn (trên + dưới) | `_args_label` (`_HeightCachedLabel`, word-wrap, không max-height) hiển thị full code → tràn + spacing layout |
| Image #3 | Approval block có dòng code redundant ở đầu | `_describe_tool_call` sinh description chứa dòng code đầu (`import ...`), rồi code editor lại hiển thị lại toàn bộ → dòng import xuất hiện 2 lần |
| Cả hai | User thấy **2 widget riêng** cho cùng 1 tool | `ToolCallWidget` + `ToolApprovalWidget` tách rời, code hiển thị 2 kiểu (QLabel vs QPlainTextEdit) |
| Chat | Docs-review message `[IDA docs review] ...` lẫn vào assistant output | Emit `TEXT_DELTA`, append vào `AssistantMessageWidget` (`chat_view.py:812-878`), lưu vào history |

---

## Decisions (đã chốt qua brainstorming)

1. **Approach**: **A — Unified `ExecutePythonWidget`**. Một widget duy nhất
   cho toàn bộ vòng đời `execute_python`: approval → execution → result.
   Các tool khác vẫn dùng `ToolCallWidget` cũ (không ảnh hưởng).
2. **Loại bỏ redundancy**: bỏ description "Run Python code (N lines): import..."
   (`_describe_tool_call`); code chỉ hiển thị 1 lần trong code editor vàng.
3. **Always-allow behavior**: khi `_always_allow_scripts=True`, widget tạo ở
   state `AUTO_APPROVED`, **collapse code editor mặc định** (chỉ header +
   result khi xong). Toggle ▶ để expand.
4. **Docs-review display**: thu gọn thành **1 dòng status** đặt **giữa code
   block và result**. APPROVED luôn hiện 1 dòng mờ (không tự ẩn).
5. **Docs-gate BLOCKED**: giữ **hard block** (như hiện tại) — không cho user
   override. Script không chạy, agent phải viết lại. Lý do: gate tồn tại để
   ngăn API hallucinated có thể corrupt IDB; override dễ dàng sẽ triệt tiêu
   lớp bảo vệ.
6. **Event mới**: `DOCS_GATE_STATUS` gắn với `tool_call_id` — thay thế
   `TEXT_DELTA` cho docs-review. Không chảy vào assistant text, không lưu
   vào history. Chỉ là UI signal.
7. **Cơ chế approval signal**: giữ nguyên `approved(tool_call_id, decision)`
   → `_on_tool_approval` → `tool_approval_submitted`. Không đổi controller
   wiring.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  AgentLoop (rikugan/agent/loop.py)                                 │
│                                                                     │
│  _review_complex_idapython_script()                                 │
│    ├── yield DOCS_GATE_STATUS(running, reasons)   ← thay TEXT_DELTA │
│    ├── SubagentRunner.run_task(silent=True)                         │
│    └── yield DOCS_GATE_STATUS(approved | blocked, summary)          │
│                                                                     │
│  _execute_single_tool() — execute_python path                      │
│    ├── docs gate (nếu complex) → DOCS_GATE_STATUS events            │
│    ├── TOOL_APPROVAL_REQUEST (nếu không always-allow)               │
│    └── TOOL_RESULT                                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ TurnEvent stream (queue.Queue → QTimer)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ChatView._handle_tool_event (rikugan/ui/chat_view.py)             │
│                                                                     │
│  TOOL_CALL_START:                                                   │
│    if tool_name == EXECUTE_PYTHON_TOOL_NAME:                        │
│        tw = ExecutePythonWidget(tool_call_id)   ← NEW              │
│    else:                                                            │
│        tw = ToolCallWidget(...)                  ← unchanged        │
│                                                                     │
│  DOCS_GATE_STATUS (NEW handler):                                    │
│    tw = self._tool_widgets.get(event.tool_call_id)                  │
│    tw.set_docs_gate_status(event.metadata)                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ExecutePythonWidget (rikugan/ui/tool_widgets.py) — NEW            │
│                                                                     │
│  States: PENDING_APPROVAL | AUTO_APPROVED | RUNNING | DONE         │
│                                                                     │
│  Layout (top→bottom):                                               │
│    ├── header: ▶ ● execute_python              ⟳/✓/✗               │
│    ├── code editor (vàng, QPlainTextEdit, syntax highlight)         │
│    ├── label "Python code — N lines"                                │
│    ├── status line (docs gate) — 1 dòng, màu theo state             │
│    ├── buttons: Allow | Always Allow | Deny (chỉ khi cần approval) │
│    └── result block (chỉ sau TOOL_RESULT)                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. `DOCS_GATE_STATUS` event (`rikugan/agent/turn.py`)

Thêm vào `TurnEventType`:
```python
DOCS_GATE_STATUS = "docs_gate_status"
```

Factory method `TurnEvent.docs_gate_status(tool_call_id, state, reasons=(), summary="")`:
- `state`: `"running" | "approved" | "blocked" | "failed"`
- `reasons`: `tuple[str, ...]` — complexity reasons (cho "running")
- `summary`: `str` — reviewer summary (cho "blocked" / "failed")
- Gắn `tool_call_id` để UI route đúng widget

`metadata` dict: `{"docs_gate_state": state, "docs_gate_reasons": list(reasons), "docs_gate_summary": summary}`.

### 2. AgentLoop changes (`rikugan/agent/loop.py`)

**`_review_complex_idapython_script()`**:
- Thay 2 `yield TurnEvent.text_delta("[IDA docs review] ...")` (dòng 1165-1168
  và 1220/1230) bằng `yield TurnEvent.docs_gate_status(tc.id, state=...)`.
- Trước khi spawn reviewer: `state="running", reasons=complexity.reasons`.
- Sau khi parse verdict: `state="approved"` hoặc `state="blocked", summary=...`.
- Exception path: `state="failed", error=str(e)`.

Giữ nguyên logic return `(approved, summary)` — caller (`_execute_single_tool`)
không đổi.

**`_describe_tool_call()`** (dòng 1056-1064):
- Branch `execute_python` hiện sinh description chứa code. Vì widget mới tự
  hiển thị code, description không còn cần thiết cho `execute_python`.
- Trả `""` (empty) cho `EXECUTE_PYTHON_TOOL_NAME` → `ToolApprovalWidget` cũ
  sẽ không còn dùng cho tool này (widget mới接管), nhưng giữ logic an toàn.

### 3. `ExecutePythonWidget` (`rikugan/ui/tool_widgets.py`)

```python
class ExecutePythonWidget(QFrame):
    approved = Signal(str, str)  # (tool_call_id, "allow"/"allow_all"/"deny")

    def __init__(self, tool_call_id, code="", parent=None): ...
    def set_code(self, code: str) -> None: ...
    def set_docs_gate_status(self, state, reasons=(), summary="") -> None: ...
    def show_approval_buttons(self) -> None: ...
    def set_result(self, result: str, is_error: bool = False) -> None: ...
```

**States** (widget tự suy ra, không cần biết `_always_allow_scripts` của loop):
| State | Trigger | Hiển thị |
|-------|---------|----------|
| `IDLE` | init | header + code (**collapsed**) + status (nếu có). Không buttons. |
| `PENDING_APPROVAL` | nhận `TOOL_APPROVAL_REQUEST` (`show_approval_buttons()`) | header + code (**expanded**) + status + **buttons** |
| `RUNNING` | user Allow (`_on_allow`) | buttons → "Allowed" (disabled), spinner |
| `DONE` | `set_result()` | ✓/✗, result block hiện, status stay |

**Auto-approve flow**: khi `_always_allow_scripts=True`, loop **không** emit
`TOOL_APPROVAL_REQUEST` (xem `loop.py:1099-1100`) → widget không bao giờ nhận
`show_approval_buttons()` → stay `IDLE` với code collapsed → nhận `TOOL_RESULT`
chuyển thẳng sang `DONE`. ChatView không cần biết auto-allow state.

**Code editor**: reuse logic từ `ToolApprovalWidget._build_code_editor` —
`QPlainTextEdit` read-only, `_PythonHighlighter`, `setFixedHeight` dựa trên
`min(len(lines), 15)`. Không dùng `_HeightCachedLabel` → **fix khoảng trống
(Image #2)**.

**Status line** (`set_docs_gate_status`):
| state | text | style |
|-------|------|-------|
| `running` | `🔍 Reviewing script... (complex: <reasons>)` | xám + spinner nhỏ |
| `approved` | `✓ Docs review passed` | xanh, mờ (opacity thấp) |
| `blocked` | `✗ Docs review blocked: <reason ngắn>` | đỏ, đậm, click → expand detail |
| `failed` | `⚠ Docs review error — review manually` | vàng |
| (no event) | ẩn | — |

Khi `blocked`: **ẩn buttons** (hard block — agent phải rewrite). Hiện summary
expandable để user hiểu lý do.

**Buttons**: reuse `_build_approval_buttons` / styles từ `ToolApprovalWidget`.
`_on_allow` / `_on_always_allow` / `_on_deny` emit cùng signal cũ.

**Result block**: `QFrame` riêng với label "Result:" + content label. Giới hạn
height + scroll nếu dài (fix QLabel full-height issue). Màu xanh/xanh lá/xanh
đỏ theo `is_error`.

### 4. ChatView routing (`rikugan/ui/chat_view.py`)

**`_handle_tool_event()`**:
- `TOOL_CALL_START`: nếu `tool_name == EXECUTE_PYTHON_TOOL_NAME`, tạo
  `ExecutePythonWidget`. **Lưu ý**: tại `TOOL_CALL_START` chưa có code (code
  đến qua `TOOL_CALL_ARGS_DELTA` / `TOOL_CALL_DONE`). Widget cần method
  `set_code(code)` để update khi `TOOL_CALL_DONE` đến.
- ChatView **không cần biết** `_always_allow_scripts` — auto-allow được widget
  tự xử lý (xem §3: nếu không có `TOOL_APPROVAL_REQUEST`, widget stay `IDLE`,
  nhận `TOOL_RESULT` chuyển sang `DONE` trực tiếp).

- `TOOL_CALL_DONE`: nếu widget là `ExecutePythonWidget`, gọi `set_code(code)`.
- `DOCS_GATE_STATUS` (handler mới): route tới `ExecutePythonWidget.set_docs_gate_status()`.
- `TOOL_APPROVAL_REQUEST` cho `execute_python`: route tới widget hiện có
  (thay vì tạo `ToolApprovalWidget` mới). Cần check: nếu đã có
  `ExecutePythonWidget` cho tool_call_id, gọi method `show_approval_buttons()`
  thay vì tạo widget mới.

**Lưu ý**: `TOOL_APPROVAL_REQUEST` mang `tool_call_id` — khớp với widget đã
tạo từ `TOOL_CALL_START`. Route vào widget đó.

### 5. Backward compat

- `ToolCallWidget`, `ToolApprovalWidget` **không xóa** — vẫn dùng cho các tool
  khác (mutating tools cần approval nhưng không phải execute_python).
- `_describe_tool_call` vẫn dùng cho `ToolApprovalWidget` của mutating tools.

---

## Data flow example (complex script, user approves)

```
1. TOOL_CALL_START(execute_python, id=abc)
   → ExecutePythonWidget(id=abc), state=waiting, code trống

2. TOOL_CALL_ARGS_DELTA → accumulate
3. TOOL_CALL_DONE(id=abc, code="import idautils...")
   → widget.set_code(code) → code editor hiện

4. DOCS_GATE_STATUS(id=abc, state=running, reasons=["2 IDA modules", ...])
   → status line: "🔍 Reviewing script... (complex: 2 IDA modules)"

5. [SubagentRunner chạy silent — không TEXT_DELTA vào chat]

6. DOCS_GATE_STATUS(id=abc, state=approved)
   → status line: "✓ Docs review passed" (xanh mờ)

7. TOOL_APPROVAL_REQUEST(id=abc, execute_python, code, desc="")
   → widget.show_approval_buttons() → hiện Allow/Always/Deny

8. User click Allow → widget.approved.emit(abc, "allow")
   → _on_tool_approval → tool_approval_submitted → controller → queue

9. [Script thực thi]

10. TOOL_RESULT(id=abc, result="...", is_error=False)
    → widget.set_result() → ✓, result block hiện, buttons ẩn
```

---

## Error handling

| Trường hợp | Behavior |
|------------|----------|
| Script syntax error (validator block) | DOCS_GATE_STATUS blocked, agent rewrite |
| Reviewer exception | DOCS_GATE_STATUS failed, **fall through to user approval** (user vẫn decide — không hard-block vì reviewer crash, không phải script fault) |
| User Deny | TOOL_RESULT error "denied", widget ✓→✗ |
| Script runtime error | TOOL_RESULT is_error=True, widget ✗, result block đỏ |
| Cancellation | CancellationError raise, widget stays in last state |

**Refinement §5**: `failed` state (reviewer crash) khác `blocked` (reviewer
chặn). `blocked` = hard block (ẩn buttons). `failed` = reviewer không chạy
được → vẫn cho user approval (hiện buttons + warning). Đây là điểm khác biệt
quan trọng: crash của subagent không được biến thành block cứng.

---

## Testing

**Unit tests** (`tests/ui/test_execute_python_widget.py` — NEW):
- `test_widget_states_transition` — PENDING → RUNNING → DONE
- `test_auto_approved_collapses_code` — auto_approved=True → code collapsed
- `test_docs_gate_status_running` — status line text + color
- `test_docs_gate_status_blocked_hides_buttons` — blocked → buttons invisible
- `test_docs_gate_status_failed_shows_buttons` — failed → buttons visible
- `test_set_result_error_shows_red` — is_error → red result block
- `test_allow_emits_signal` — click Allow → approved signal
- `test_code_displayed_once` — không có redundant description

**Loop tests** (`tests/agent/test_idapython_docs_gate.py` — UPDATE):
- Verify `_review_complex_idapython_script` emit `DOCS_GATE_STATUS` (không
  phải TEXT_DELTA) — assert event types trong captured events
- `test_failed_falls_through_to_user_approval` — reviewer crash → không block

**Integration**: manual test trong IDA với:
- Script đơn giản (no gate)
- Script complex (gate fire, approved)
- Script complex (gate fire, blocked)
- Reviewer crash (mock exception)
- Always-allow flow
- User deny

---

## Scope & non-goals

**In scope:**
- Unified `ExecutePythonWidget`
- `DOCS_GATE_STATUS` event
- Docs-review status line (1 dòng)
- Fix khoảng trống block (Image #2)
- Fix redundant description (Image #3)
- Hard-block behavior cho docs-gate BLOCKED
- Fall-through cho docs-gate FAILED

**Non-goals (YAGNI):**
- Không refactor `ToolCallWidget` / `ToolApprovalWidget` cho tools khác
- Không thêm config mới (dùng `require_ida_docs_for_complex_scripts` hiện có)
- Không thay đổi logic subagent reviewer
- Không thay đổi `_always_allow_scripts` semantics
- Không thêm persistence cho docs-review status (chỉ UI runtime)

---

## Risk & mitigation

| Risk | Mitigation |
|------|------------|
| ChatView routing phức tạp (widget đã tồn tại khi TOOL_APPROVAL_REQUEST đến) | Check `_tool_widgets[tool_call_id]` isinstance ExecutePythonWidget → call method, không tạo mới |
| DOCS_GATE_STATUS đến trước TOOL_CALL_START (race) | Handler check widget tồn tại, nếu không → buffer hoặc drop (UI-only signal, an toàn) |
| Code chưa có ở TOOL_CALL_START | Widget init với code="", `set_code()` update khi TOOL_CALL_DONE |
| Widget lớn ảnh hưởng layout cascade (chat lag memory) | Code editor có max height (15 lines + scroll), result block có max height. Match pattern đã có trong ToolApprovalWidget |

---

## Files touched

| File | Change |
|------|--------|
| `rikugan/agent/turn.py` | + `DOCS_GATE_STATUS` enum + `docs_gate_status()` factory |
| `rikugan/agent/loop.py` | `_review_complex_idapython_script`: TEXT_DELTA → DOCS_GATE_STATUS. `_describe_tool_call`: empty cho execute_python |
| `rikugan/ui/tool_widgets.py` | + `ExecutePythonWidget` class |
| `rikugan/ui/chat_view.py` | routing: ExecutePythonWidget cho execute_python, DOCS_GATE_STATUS handler, route TOOL_APPROVAL_REQUEST vào widget hiện có |
| `tests/ui/test_execute_python_widget.py` | NEW — unit tests |
| `tests/agent/test_idapython_docs_gate.py` | UPDATE — assert DOCS_GATE_STATUS events |
