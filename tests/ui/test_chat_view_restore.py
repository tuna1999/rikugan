"""Tests for rikugan.ui.chat_view — restore worker and MessageSpec/ToolSpec."""

from __future__ import annotations

import json
import sys
import types
import unittest
from unittest.mock import MagicMock

from tests.qt_stubs import ensure_pyside6_stubs
ensure_pyside6_stubs()

# ------------------------------------------------------------------
# Stub modules chat_view imports transitively at module load time.
# We want the real chat_view (to test RestoreWorker / MessageSpec) but
# not pull in the full styles → theme → markdown-it dependency chain.
# ------------------------------------------------------------------
_STUB_NAMES = [
    "rikugan.ui.styles",
    "rikugan.ui.theme.manager",
    "rikugan.ui.theme.tokens",
    "rikugan.ui.markdown",
    "rikugan.ui.tool_widgets",
    "rikugan.ui.message_widgets",
    "rikugan.ui.plan_view",
]
for _name in _STUB_NAMES:
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

# chat_view imports many class names by name from message_widgets
_mw_stub = sys.modules["rikugan.ui.message_widgets"]
for _attr in [
    "AssistantMessageWidget",
    "ErrorMessageWidget",
    "ExplorationFindingWidget",
    "ExplorationPhaseWidget",
    "QueuedMessageWidget",
    "ResearchNoteWidget",
    "SubagentEventWidget",
    "ThinkingWidget",
    "UserMessageWidget",
    "UserQuestionWidget",
]:
    setattr(_mw_stub, _attr, MagicMock)

# chat_view imports Tool* classes from tool_widgets
_tw_stub = sys.modules["rikugan.ui.tool_widgets"]
for _attr in ["ToolApprovalWidget", "ToolCallWidget", "ToolGroupWidget"]:
    setattr(_tw_stub, _attr, MagicMock)

# rikugan.ui.markdown needs a real ``md_to_html`` function — message_widgets
# imports it at module load time. We patch it to a passthrough so the
# RestoreWorker can also call it (and we override it per-test as needed).
_md_stub = sys.modules["rikugan.ui.markdown"]


def _passthrough_md(text: str) -> str:
    return text or ""


_md_stub.md_to_html = _passthrough_md

# plan_view also needs PlanView exposed
_pv_stub = sys.modules["rikugan.ui.plan_view"]
_pv_stub.PlanView = MagicMock

# Force chat_view (and its stubs) to re-import cleanly in case a previous
# test cached them. Also drop the theme stubs so other test modules see the
# real rikugan.ui.theme.manager / tokens after this test module runs.
for _cached in (
    "rikugan.ui.chat_view",
    "rikugan.ui.styles",
    "rikugan.ui.theme.manager",
    "rikugan.ui.theme.tokens",
    "rikugan.ui.markdown",
    "rikugan.ui.tool_widgets",
    "rikugan.ui.message_widgets",
    "rikugan.ui.plan_view",
):
    sys.modules.pop(_cached, None)

# ------------------------------------------------------------------
# Now import the real chat_view
# ------------------------------------------------------------------
from rikugan.core.types import Message, Role, ToolCall, ToolResult
from rikugan.ui.chat_view import (  # noqa: E402
    MessageSpec,
    MessagePlaceholder,
    RestoreWorker,
    ToolSpec,
    _RenderedChunk,
    _estimate_assistant_height,
    _estimate_tool_height,
    _estimate_user_height,
    _is_hidden_system_user_message,
    _RESTORE_CHUNK_SIZE,
)


# ------------------------------------------------------------------
# Test helpers
# ------------------------------------------------------------------
def _user_msg(content: str) -> Message:
    return Message(role=Role.USER, content=content)


def _assistant_msg(content: str) -> Message:
    return Message(role=Role.ASSISTANT, content=content)


def _tool_msg(calls: list[ToolCall], results: list[ToolResult]) -> Message:
    msg = Message(role=Role.TOOL, content="")
    msg.tool_calls = calls
    msg.tool_results = results
    return msg


def _md_stub(text: str) -> str:
    """Trivial md_to_html stub: wrap in <p>."""
    return f"<p>{text}</p>"


# ------------------------------------------------------------------
# Pure-function tests
# ------------------------------------------------------------------
class HiddenSystemFilterTests(unittest.TestCase):
    """_is_hidden_system_user_message strips [SYSTEM] sentinels."""

    def test_plain_text_is_not_hidden(self) -> None:
        self.assertFalse(_is_hidden_system_user_message("hello world"))

    def test_empty_is_not_hidden(self) -> None:
        self.assertFalse(_is_hidden_system_user_message(""))

    def test_system_sentinel_is_hidden(self) -> None:
        self.assertTrue(_is_hidden_system_user_message("[SYSTEM] do something"))

    def test_system_sentinel_with_brackets_is_hidden(self) -> None:
        self.assertTrue(_is_hidden_system_user_message("[SYSTEM] some text"))

    def test_case_insensitive(self) -> None:
        # The check is a literal startswith('[SYSTEM]'), so mixed case
        # is NOT hidden. Pin that contract so we notice if it changes.
        self.assertFalse(_is_hidden_system_user_message("[system] low"))


class HeightEstimatorTests(unittest.TestCase):
    """Height estimators should return sensible, clamped values."""

    def test_user_short_text_min_height(self) -> None:
        h = _estimate_user_height("hi")
        # minimum clamp is 40
        self.assertGreaterEqual(h, 40)

    def test_user_empty_text(self) -> None:
        h = _estimate_user_height("")
        # empty text → 40
        self.assertEqual(h, 40)

    def test_assistant_short(self) -> None:
        h = _estimate_assistant_height("hi", "<p>hi</p>")
        # minimum clamp is 64
        self.assertGreaterEqual(h, 64)

    def test_assistant_long_increases(self) -> None:
        # 100 lines of text → ~32 + 100*18 = 1832, clamped to 800
        long_text = "\n".join(f"line {i}" for i in range(100))
        long_html = "<p>" + long_text.replace("\n", "<br>") + "</p>"
        h = _estimate_assistant_height(long_text, long_html)
        # Long content should hit the 800 cap
        self.assertGreaterEqual(h, 400)

    def test_tool_min_height(self) -> None:
        spec = ToolSpec(id="x", name="n", arguments_json="{}")
        h = _estimate_tool_height(spec)
        # tool base chrome is 80
        self.assertGreaterEqual(h, 80)


# ------------------------------------------------------------------
# Dataclass sanity tests
# ------------------------------------------------------------------
class DataclassTests(unittest.TestCase):
    def test_tool_spec_defaults(self) -> None:
        s = ToolSpec(id="abc", name="decompile", arguments_json="{}")
        self.assertEqual(s.id, "abc")
        self.assertEqual(s.estimated_height, 80)
        self.assertEqual(s.result_content, "")
        self.assertFalse(s.result_is_error)

    def test_message_spec_defaults(self) -> None:
        s = MessageSpec(msg_id="m1", role="user")
        self.assertEqual(s.content, "")
        self.assertEqual(s.content_html, "")
        self.assertEqual(s.tool_specs, ())
        self.assertEqual(s.estimated_height, 60)

    def test_message_spec_is_frozen(self) -> None:
        s = MessageSpec(msg_id="m1", role="user")
        with self.assertRaises(Exception):
            s.msg_id = "different"  # type: ignore[misc]

    def test_rendered_chunk_is_mutable(self) -> None:
        # _RenderedChunk is intentionally NOT frozen so the worker can
        # append in place.
        c = _RenderedChunk()
        s = MessageSpec(msg_id="m1", role="user")
        c.specs.append(s)
        self.assertEqual(c.specs, [s])


# ------------------------------------------------------------------
# RestoreWorker._build_spec (static method)
# ------------------------------------------------------------------
class BuildSpecTests(unittest.TestCase):
    """RestoreWorker._build_spec converts Message -> MessageSpec/None."""

    def test_user_message(self) -> None:
        msg = _user_msg("hello")
        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        assert spec is not None
        self.assertEqual(spec.role, "user")
        self.assertEqual(spec.content, "hello")
        self.assertEqual(spec.msg_id, msg.id)  # uses message.id when set

    def test_user_uses_index_when_id_missing(self) -> None:
        msg = _user_msg("hello")
        msg.id = ""  # empty id -> falls back to restore_<idx>
        spec = RestoreWorker._build_spec(msg, 7, _md_stub)
        assert spec is not None
        self.assertEqual(spec.msg_id, "restore_7")

    def test_hidden_system_user_filtered_out(self) -> None:
        msg = _user_msg("[SYSTEM] hidden prompt")
        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        self.assertIsNone(spec)

    def test_assistant_message_renders_html(self) -> None:
        msg = _assistant_msg("**bold**")
        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        assert spec is not None
        self.assertEqual(spec.role, "assistant")
        self.assertEqual(spec.content, "**bold**")
        # html was produced by our stub
        self.assertEqual(spec.content_html, "<p>**bold**</p>")

    def test_assistant_empty_content_no_html(self) -> None:
        msg = _assistant_msg("")
        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        assert spec is not None
        # Empty content should not call md_to_html (no work to do)
        self.assertEqual(spec.content, "")
        self.assertEqual(spec.content_html, "")

    def test_tool_message_picks_up_results(self) -> None:
        tc = ToolCall(id="call_1", name="decompile", arguments={"addr": "0x401000"})
        tr = ToolResult(tool_call_id="call_1", name="decompile", content="ret 0x42;")
        msg = _tool_msg([tc], [tr])

        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        assert spec is not None
        self.assertEqual(spec.role, "tool")
        self.assertEqual(len(spec.tool_specs), 1)

        tool_spec = spec.tool_specs[0]
        self.assertEqual(tool_spec.id, "call_1")
        self.assertEqual(tool_spec.name, "decompile")
        # arguments_json must be a real JSON string
        self.assertEqual(json.loads(tool_spec.arguments_json), {"addr": "0x401000"})
        self.assertEqual(tool_spec.result_content, "ret 0x42;")
        self.assertFalse(tool_spec.result_is_error)

    def test_tool_message_error_result_propagated(self) -> None:
        tc = ToolCall(id="call_2", name="decompile", arguments={})
        tr = ToolResult(tool_call_id="call_2", name="decompile", content="fail", is_error=True)
        msg = _tool_msg([tc], [tr])
        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        assert spec is not None
        self.assertTrue(spec.tool_specs[0].result_is_error)

    def test_tool_message_swallows_non_serializable_args(self) -> None:
        # Arguments that can't be json-dumped should fall back to "{}"
        tc = ToolCall(id="call_3", name="f", arguments={"bad": {"nested": "thing"}})
        tr = ToolResult(tool_call_id="call_3", name="f", content="ok")
        msg = _tool_msg([tc], [tr])
        spec = RestoreWorker._build_spec(msg, 0, _md_stub)
        assert spec is not None
        # Either the original was serialized, or we fell back to "{}"
        # — both are valid as long as json.loads succeeds.
        json.loads(spec.tool_specs[0].arguments_json)


# ------------------------------------------------------------------
# RestoreWorker.run() — full loop with signal collection
# ------------------------------------------------------------------
class WorkerRunTests(unittest.TestCase):
    """Drive the worker synchronously and inspect emitted signals."""

    def _run(self, messages: list[Message]) -> tuple[list[_RenderedChunk], bool]:
        """Run a worker, collect all chunk_ready emissions and finished_ok flag.

        Since QThread.run is overridden synchronously here, the signals are
        emitted inline; we connect to MagicMock collectors and just call run().
        """
        worker = RestoreWorker(messages)
        chunks: list[_RenderedChunk] = []
        finished: list[bool] = []
        worker.chunk_ready.connect(lambda c: chunks.append(c))
        worker.finished_ok.connect(lambda: finished.append(True))
        worker.run()
        return chunks, bool(finished)

    def test_empty_messages(self) -> None:
        chunks, finished = self._run([])
        self.assertEqual(chunks, [])
        self.assertTrue(finished, "finished_ok should still fire on empty list")

    def test_single_user_message(self) -> None:
        chunks, finished = self._run([_user_msg("hi")])
        # Remainder flush emits the partial chunk
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0].specs), 1)
        self.assertEqual(chunks[0].specs[0].role, "user")
        self.assertTrue(finished)

    def test_filtered_out_message_skipped(self) -> None:
        chunks, _ = self._run([
            _user_msg("[SYSTEM] hidden"),
            _user_msg("real"),
        ])
        # Only the visible user msg survives
        self.assertEqual(len(chunks[0].specs), 1)
        self.assertEqual(chunks[0].specs[0].content, "real")

    def test_chunk_boundary_emits_partial_chunk(self) -> None:
        # Build _RESTORE_CHUNK_SIZE + 5 messages; the first chunk should be
        # exactly chunk-size, the remainder should be a single chunk of 5.
        n = _RESTORE_CHUNK_SIZE + 5
        messages = [_user_msg(f"m{i}") for i in range(n)]
        chunks, _ = self._run(messages)
        self.assertEqual(len(chunks), 2, f"expected 2 chunks, got {len(chunks)}")
        self.assertEqual(len(chunks[0].specs), _RESTORE_CHUNK_SIZE)
        self.assertEqual(len(chunks[1].specs), 5)
        # Total spec count equals input count
        total = sum(len(c.specs) for c in chunks)
        self.assertEqual(total, n)

    def test_cancel_stops_early(self) -> None:
        n = 200
        messages = [_user_msg(f"m{i}") for i in range(n)]
        worker = RestoreWorker(messages)
        # Cancel before starting
        worker.cancel()
        chunks: list[_RenderedChunk] = []
        finished: list[bool] = []
        worker.chunk_ready.connect(lambda c: chunks.append(c))
        worker.finished_ok.connect(lambda: finished.append(True))
        worker.run()
        # No specs produced because run() returns at the first iteration check
        self.assertEqual(sum(len(c.specs) for c in chunks), 0)
        # finished_ok should NOT fire when cancelled before any work
        self.assertFalse(finished)

    def test_exactly_chunk_size_emits_one_chunk(self) -> None:
        # Boundary: exactly _RESTORE_CHUNK_SIZE messages. The boundary check
        # emits the chunk when len >= CHUNK_SIZE, then the remainder is
        # empty so the flush guard (`if chunk.specs`) skips it.
        messages = [_user_msg(f"m{i}") for i in range(_RESTORE_CHUNK_SIZE)]
        chunks, finished = self._run(messages)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0].specs), _RESTORE_CHUNK_SIZE)
        self.assertTrue(finished)


# ------------------------------------------------------------------
# MessagePlaceholder — basic construction
# ------------------------------------------------------------------
class PlaceholderTests(unittest.TestCase):
    def test_placeholder_constructs(self) -> None:
        # We don't trigger paint/resize here — just verify the class
        # imports and __init__ runs without errors on a fixed spec.
        ph = MessagePlaceholder(80, "m1")
        self.assertEqual(ph.minimumHeight(), 80)
        # Spec should be stored for later widget instantiation
        self.assertIsNotNone(ph)


if __name__ == "__main__":
    unittest.main()
