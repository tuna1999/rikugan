# Remove RIKUGAN.md Legacy — Cutover to Central MEMORY.md

**Ngày:** 2026-07-16
**Trạng thái:** Approved (brainstormed 2026-07-16)
**Spec authority cho:** implementation plan kế tiếp

## Mục tiêu

Chuyển hoàn toàn (cutover) persistent memory runtime từ legacy `RIKUGAN.md` (markdown file cạnh IDB) sang central memory subsystem (`BinaryMemoryService` — SQLite structured facts + `MEMORY.md` managed region). Xóa toàn bộ legacy read/write code runtime, xóa importer `legacy.py`, xóa 3 dark-scaffolding config flags. Không còn dual-path, không còn fallback.

**Scope:** Final cleanup của cutover đã được dark-scaffold. Hệ thống central memory (Tasks 1-6 trong `2026-07-14-central-memory-cutover.md`) đã hoàn thiện — phần còn lại chỉ là flip default + dọn legacy.

## Bối cảnh

Rikugan có 2 lớp memory:
- **Legacy (xóa):** `RIKUGAN.md` file cạnh IDB, ghi bởi `save_memory` tool, đọc bởi `_load_persistent_memory()`, append bởi `append_to_memory_file()`.
- **Central (giữ, làm default):** `rikugan/memory/` package — `BinaryMemoryService` façade, SQLite repository, `MemoryProjector` ghi managed region vào `MEMORY.md`, `MemoryWriteAuthority` (non-serializable, main-agent-only).

Codebase đã có dispatch song song (central vs legacy) tại 3 điểm:
- `_handle_save_memory_tool` (`loop.py:1625`)
- `_handle_memory_command` (`loop_commands.py:106`)
- `build_system_prompt` (`system_prompt.py:128`)

Central path kích hoạt qua `memory_workspaces_enabled` flag, hiện `False`.

## Quyết định thiết kế

1. **Central memory luôn-on.** Xóa flag `memory_workspaces_enabled` — không còn cách disable. `case_memory_enabled` và `peer_retrieval_enabled` cũng xóa (chúng phụ thuộc central memory).
2. **Không giữ importer.** Xóa `rikugan/memory/legacy.py` hoàn toàn (user chọn clean break — ai đang có `RIKUGAN.md` cũ phải copy thủ công).
3. **Giữ `sanitize_memory()`.** Hàm này vẫn dùng trong central path để wrap `manual_memory_notes` từ `MEMORY.md` unmanaged region (`system_prompt.py:132`). Đổi docstring mention `RIKUGAN.md` → `MEMORY.md`.
4. **Không backward-compat runtime.** Legacy branch bị xóa, không giữ "deprecated but functional".

## Thay đổi chi tiết

### Phase 1 — Config layer (flip flags)

**`rikugan/core/config.py`:**
- Xóa 3 dataclass field: `memory_workspaces_enabled` (dòng 156), `case_memory_enabled` (dòng 160), `peer_retrieval_enabled` (dòng 165) và comment block dòng 149-165.
- Xóa 3 entry khỏi load-key tuple (dòng 362-364).
- Xóa 3 entry khỏi `_BOOLEAN_FIELDS` set (dòng 402-404).
- Trong `load()`: các key cũ nếu xuất hiện trong config file user sẽ tự bị bỏ qua (không trong load-key list → không `setattr`). Không cần cleanup riêng — behavior tự nhiên.

**Hệ quả (không cần sửa — đã always-on):**
- `MemoryWorkspaceManager.__init__` luôn `self._registry.initialize()` (guard `if config.memory_workspaces_enabled` dòng 52 trở thành always-true → xóa guard).
- `MemoryWorkspaceManager.bind()` xóa dark-mode branch (dòng 65-74).
- `MemoryWorkspaceManager.set_active_case()` xóa guard dòng 112-113.
- `session_controller_base.py:491` xóa `if getattr(self.config, "memory_workspaces_enabled", False)` → luôn gọi `_wire_central_memory()`.

### Phase 2 — Runtime legacy code cleanup

**`rikugan/agent/system_prompt.py`:**
- Xóa: `_MAX_MEMORY_LINES` (dòng 21), `_MEMORY_CACHE` (dòng 40), `_MEMORY_MISSING_SENTINEL` (dòng 41), toàn bộ `_load_persistent_memory()` (dòng 44-96), comment block dòng 20-39.
- `build_system_prompt()`: xóa param `idb_dir` (dòng 115). Xóa legacy branch `else` (dòng 133-137). Memory chỉ đến từ `structured_memory` / `manual_memory_notes`. Refactor: nếu cả hai rỗng → không thêm section memory nào.
- Xóa import `os` (dòng 5) nếu không còn dùng. Giữ import `sanitize_memory` (dòng 10).
- **2 caller cần cập nhật:**
  - `loop.py:543` `_build_system_prompt()` — xóa `idb_dir=idb_dir` arg (dòng 552), dọn biến `idb_dir` dòng 516-518 nếu không dùng mục đích khác.
  - `agent/orchestra/main_agent.py:145` — xóa `idb_dir=idb_dir` arg (dòng 152), dọn biến dòng 141-143.

**`rikugan/agent/loop.py`:**
- Xóa `_MEMORY_HEADER` (dòng 84) + `append_to_memory_file()` (dòng 251-...).
- `_handle_save_memory_tool()` (dòng 1601): xóa legacy `else` branch (dòng 1643-1668) bao gồm `make_store`/`ingest_save_memory` auto-ingest import. Logic mới: nếu `memory_service is None or _memory_authority is None` → trả error "Central memory is not available in this context." (không ghi file).
- Cập nhật docstring/comment mention `RIKUGAN.md` (dòng 269, 285, 1609, 1617) → `MEMORY.md` hoặc "MEMORY.md managed region".
- `loop.memory_service` / `_memory_authority` / `_memory_manager` giữ nguyên (vẫn injection point từ controller).

**`rikugan/agent/modes/plan.py`:**
- `persist_plan()` (dòng 109): thay body. Nếu `loop.memory_service is not None and loop._memory_authority is not None` → `loop.memory_service.save_plan(loop._memory_authority, goal=user_goal, steps=steps)`, log success. Không thì no-op + `log_debug`. Xóa import `append_to_memory_file`, xóa `os.path.join(idb_dir, "RIKUGAN.md")`, xóa `time.strftime` formatting (service tự format).
- **Caller `exploration.py:249`** giữ signature `persist_plan(loop, user_goal, steps)` — không thay đổi.

**`rikugan/agent/loop_commands.py`:**
- `_handle_memory_command()` (dòng 98): xóa legacy branch (dòng 124-147). Nếu `memory_service is None` → `TurnEvent.text_done("Central memory is not available...")` + return.

**`rikugan/agent/modes/research.py`:**
- Docstring/prompt mention `RIKUGAN.md` (dòng 146, 162) → `MEMORY.md`.

### Phase 3 — Module removal + docstring cleanup

- **Xóa file `rikugan/memory/legacy.py`** hoàn toàn.
- `rikugan/memory/__init__.py`: docstring mention dark mode (dòng 7-17) → cập nhật hoặc rút gọn. Note: module này export `KnowledgeRawStore` cho knowledge subsystem (khác central memory) — **không** xóa, chỉ sửa docstring.
- `rikugan/memory/paths.py`: docstring dòng 11 mention `RIKUGAN.md` → `MEMORY.md` hoặc bỏ câu. Giữ entity-ID helpers + `knowledge_paths()`.
- `rikugan/memory/manager.py`: docstring mention dark mode (dòng 7-9) → cập nhật. Xóa guards như Phase 1.
- `rikugan/core/sanitize.py`: docstring dòng 5 "(skills, RIKUGAN.md)" → "(skills, MEMORY.md)".

### Phase 4 — Tests

- **Xóa file** `tests/memory/test_legacy.py` (importer đã xóa).
- **Sửa** `tests/agent/test_memory_cutover.py`: xóa `test_legacy_path_still_works_without_service` (dòng 74-88) — legacy path không còn.
- **Sửa** `tests/memory/test_foundation_gate.py`: xóa assertion `_load_persistent_memory` callable (dòng 35-38).
- **Kiểm tra + sửa nếu cần:** `tests/agent/test_prompt_cutover.py`, `tests/agent/test_memory_write_ownership.py`, `tests/agent/test_system_prompt.py` — remove RIKUGAN.md references, update cho `build_system_prompt` không còn param `idb_dir`.
- **Giữ nguyên:** `tests/core/test_sanitize.py`, `rikugan/tests/test_session_restore_sanitization.py` (sanitize_memory vẫn dùng), các test central memory service/repo/workspace/case.
- **Thêm 1 test guard:** grep-based test hoặc assertion rằng `build_system_prompt` không accept `idb_dir` (optional, phòng regression).

### Phase 5 — Docs

- `CLAUDE.md`: dòng 209 bảng sanitize (`RIKUGAN.md` → `MEMORY.md`), mục "Persistent memory" mention `RIKUGAN.md` (tìm + replace).
- `AGENTS.md`: dòng 579 + grep toàn bộ `RIKUGAN.md` mention.
- `ARCHITECTURE.md`, `README.md`, `llms.txt`, `webpage/llms.txt`, `webpage/index.html`, `webpage/docs.html`, `webpage/ARCHITECTURE.html`: cập nhật mention.
- `CHANGELOG.md`: thêm entry `feat(memory): cut over to central MEMORY.md, remove legacy RIKUGAN.md`.
- **Không sửa** `docs/superpowers/plans/2026-07-14-central-memory-cutover.md` và spec liên quan — đây là historical record của việc build hệ thống mới.

## Rủi ro và mitigations

| Rủi ro | Mitigation |
|--------|------------|
| User đang có config file chứa 3 flags cũ → load fail | Flags không trong load-key list → tự bỏ qua. Test `test_config.py` verify. |
| User đang có `RIKUGAN.md` cũ → mất dữ liệu | Clean break (user chọn b). Note trong CHANGELOG rằng dữ liệu legacy không auto-migrate. |
| `memory_service` None trong headless/a2a context → `save_memory` báo error thay vì ghi | Behavior đúng — central memory cần controller wire service. Headless phải wire hoặc disable. Verify headless path. |
| `idb_dir` param xóa khỏi `build_system_prompt` → caller khác miss | Chỉ 2 caller (đã map). Grep verify sau khi sửa. |
| Test `test_legacy.py` xóa nhưng có import vào conftest | Kiểm tra `tests/memory/__init__.py` và conftest. |

## Out of scope

- Build mới central memory subsystem (đã xong — Tasks 1-6 cutover plan).
- Knowledge subsystem (`notes/`, `.rikugan-kb/`, `KnowledgeRawStore`) — đây là JSONL knowledge store riêng, **không** phải persistent memory. Giữ nguyên.
- Headless memory wiring chi tiết (verify-only, không build mới).
- Version bump (task riêng theo release flow).

## Thứ tự thực thi đề xuất

1. Phase 1 (config) — thấp rủi ro, enable feature
2. Phase 2 (runtime code) — core thay đổi
3. Phase 3 (module removal) — sau khi Phase 2 xóa hết caller
4. Phase 4 (tests) — song song với Phase 2-3 (TDD-style khi sửa logic)
5. Phase 5 (docs) — cuối cùng
6. Verify: `./ci-local.sh` + grep "RIKUGAN.md" trong `rikugan/` không còn runtime reference
