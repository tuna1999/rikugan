"""Chat view: scrollable area containing message widgets."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from ..agent.turn import TurnEvent, TurnEventType
from ..core.types import Message, Role, ToolCall, ToolResult
from .message_widgets import (
    AssistantMessageWidget,
    ErrorMessageWidget,
    ExplorationFindingWidget,
    ExplorationPhaseWidget,
    QueuedMessageWidget,
    ResearchNoteWidget,
    SubagentEventWidget,
    ThinkingWidget,
    UserMessageWidget,
    UserQuestionWidget,
)
from .plan_view import PlanView
from .qt_compat import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    Qt,
    QThread,
    QTimer,
    QVBoxLayout,
    QWidget,
    Signal,
)
from .tool_widgets import ToolApprovalWidget, ToolCallWidget, ToolGroupWidget

_THINKING_MIN_DISPLAY_MS = 500

# How many MessageSpec objects the worker accumulates before emitting
# a single ``chunk_ready`` signal to the main thread.  Larger chunks
# reduce per-emit overhead but increase latency-to-first-paint.
_RESTORE_CHUNK_SIZE = 20

# Collapse consecutive tool runs once they reach this many calls.
# A single tool call is shown inline with its name visible;
# only 2+ consecutive calls get grouped into a collapsible widget.
_TOOL_GROUP_MIN_CALLS = 2


def _is_hidden_system_user_message(content: str) -> bool:
    """Internal system hints are persisted as user messages but not shown in UI."""
    if not content:
        return False
    return content.lstrip().startswith("[SYSTEM]")


# ---------------------------------------------------------------------------
# Async restore: spec types, placeholder, worker
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    """Pre-serialized tool call/result pair for async restore.

    Frozen so it can safely cross thread boundaries without locks.
    """

    id: str
    name: str
    arguments_json: str  # pre-serialized via json.dumps
    # Estimated pixel height of the rendered ToolCallWidget.
    estimated_height: int = 80
    # ToolResult side: optional result content / error flag.
    result_content: str = ""
    result_is_error: bool = False


@dataclass(frozen=True)
class MessageSpec:
    """Pre-built description of a single chat message.

    Built off the UI thread by :class:`RestoreWorker`.  Carries everything
    needed to instantiate the real Qt widget on the main thread without
    further I/O or computation.
    """

    # Stable identifier — set once in the worker so the main thread can
    # correlate emitted chunks with their original position in the list.
    msg_id: str
    role: str  # one of Role.{USER,ASSISTANT,TOOL}
    # USER / ASSISTANT raw text (assistant text is the *markdown* source;
    # the worker has already pre-rendered it to HTML in ``content_html``).
    content: str = ""
    content_html: str = ""  # pre-rendered via md_to_html (assistant only)
    # USER_QUESTION payload
    question_options: tuple[str, ...] = ()
    # TOOL side: list of ToolSpec (call + result)
    tool_specs: tuple[ToolSpec, ...] = ()
    # Estimated pixel height of the widget once it is laid out at the
    # current viewport width.  Used for MessagePlaceholder sizing.
    estimated_height: int = 60


@dataclass
class _RenderedChunk:
    """A batch of MessageSpecs delivered from worker to main thread.

    Wrapped in a mutable dataclass so the queued signal can carry an
    object (signals carrying ``tuple`` work but are harder to extend).
    """

    specs: list[MessageSpec] = field(default_factory=list)


def _estimate_assistant_height(text: str, html: str) -> int:
    """Cheap line-count based height estimate for an assistant message.

    Used to size MessagePlaceholder widgets before the real
    AssistantMessageWidget is constructed.  18px per text line + 32px
    for header/footer chrome.  Falls back to 80px for empty content.
    """
    if not html and not text:
        return 32
    # Use raw text line count if available, else approximate from html
    # by counting <div> / <br> tags.
    if text:
        lines = text.count("\n") + 1
    else:
        lines = html.count("<div") + html.count("<br>") + 1
    # ~18px per wrapped line, capped to a sensible minimum
    return max(64, min(800, 32 + lines * 18))


def _estimate_tool_height(spec: ToolSpec) -> int:
    """Cheap height estimate for a single tool call + result."""
    # Base chrome (header, result box) is ~80px.  Result content adds
    # ~14px per wrapped line, capped.
    result_lines = (spec.result_content.count("\n") + 1) if spec.result_content else 0
    extra = min(400, result_lines * 14)
    return 80 + extra


def _estimate_user_height(text: str) -> int:
    """Cheap height estimate for a user message."""
    if not text:
        return 40
    lines = text.count("\n") + 1
    # ~16px per wrapped line
    return max(40, min(600, 32 + lines * 16))


class MessagePlaceholder(QFrame):
    """Lightweight sized spacer used during async restore.

    Holds the vertical space for an upcoming real widget so the
    QScrollArea can compute correct scrollbar geometry.  Replaced by
    the real widget via :func:`replace_with` when the chunk is
    rendered.  Holds no real content — just a fixed ``minimumHeight``.
    """

    def __init__(self, estimated_height: int, msg_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._msg_id = msg_id
        self.setObjectName("chat_msg_placeholder")
        # QFrame with no frame looks invisible — exactly what we want.
        # We only need its size contribution to the layout.
        self.setMinimumHeight(max(16, int(estimated_height)))
        self.setMaximumHeight(self.minimumHeight())

    @property
    def msg_id(self) -> str:
        return self._msg_id


class RestoreWorker(QThread):
    """Background thread that builds MessageSpec objects.

    Walks the input ``list[Message]`` and emits a single
    ``chunk_ready(_RenderedChunk)`` signal per :data:`_RESTORE_CHUNK_SIZE`
    messages.  When the loop is exhausted, ``finished_ok`` is emitted
    so the main thread can finalise the restore (apply viewport
    detection, scrollbar geometry, etc.).

    Cancellation: :func:`cancel`` sets a stop flag the worker checks at
    the top of each iteration.  Late signals from a cancelled worker
    are ignored by the main thread via a generation counter.
    """

    chunk_ready = Signal(object)  # _RenderedChunk
    finished_ok = Signal()

    def __init__(self, messages: list[Message], parent=None):
        super().__init__(parent)
        self._messages = messages
        self._stop_requested = False

    def cancel(self) -> None:
        """Request the worker to stop at the next safe point."""
        self._stop_requested = True

    def run(self) -> None:
        # Import inside run() so the worker's own import cost doesn't
        # slow down ChatView construction on the main thread.
        from .markdown import md_to_html

        chunk = _RenderedChunk()
        for idx, msg in enumerate(self._messages):
            if self._stop_requested:
                return
            spec = self._build_spec(msg, idx, md_to_html)
            if spec is None:
                continue  # filtered out (e.g. hidden [SYSTEM] user msg)
            chunk.specs.append(spec)
            if len(chunk.specs) >= _RESTORE_CHUNK_SIZE:
                self.chunk_ready.emit(chunk)
                chunk = _RenderedChunk()
        # Flush remainder
        if chunk.specs and not self._stop_requested:
            self.chunk_ready.emit(chunk)
        if not self._stop_requested:
            self.finished_ok.emit()

    @staticmethod
    def _build_spec(msg: Message, idx: int, md_to_html) -> MessageSpec | None:
        """Convert one Message into a MessageSpec (or None to skip)."""
        # msg_id is derived here and only here — used for correlation
        # between emitted chunks and their original position.
        msg_id = msg.id or f"restore_{idx}"

        if msg.role == Role.USER:
            if _is_hidden_system_user_message(msg.content):
                return None
            return MessageSpec(
                msg_id=msg_id,
                role=Role.USER.value,
                content=msg.content,
                estimated_height=_estimate_user_height(msg.content),
            )

        if msg.role == Role.ASSISTANT:
            content = msg.content or ""
            html = md_to_html(content) if content else ""
            return MessageSpec(
                msg_id=msg_id,
                role=Role.ASSISTANT.value,
                content=content,
                content_html=html,
                estimated_height=_estimate_assistant_height(content, html),
            )

        if msg.role == Role.TOOL:
            # Build ToolSpec for each call + matching result.
            results_by_id: dict[str, ToolResult] = {
                r.tool_call_id: r for r in msg.tool_results
            }
            tool_specs: list[ToolSpec] = []
            for tc in msg.tool_calls:
                tr = results_by_id.get(tc.id)
                # json.dumps once on the worker thread; the main thread
                # never touches raw arguments.
                try:
                    args_json = json.dumps(tc.arguments or {}, ensure_ascii=False)
                except (TypeError, ValueError):
                    args_json = "{}"
                spec = ToolSpec(
                    id=tc.id,
                    name=tc.name,
                    arguments_json=args_json,
                    estimated_height=_estimate_tool_height(
                        ToolSpec(
                            id=tc.id,
                            name=tc.name,
                            arguments_json="",
                            result_content=tr.content if tr else "",
                            result_is_error=tr.is_error if tr else False,
                        )
                    ),
                    result_content=tr.content if tr else "",
                    result_is_error=tr.is_error if tr else False,
                )
                tool_specs.append(spec)
            return MessageSpec(
                msg_id=msg_id,
                role=Role.TOOL.value,
                tool_specs=tuple(tool_specs),
                estimated_height=sum(s.estimated_height for s in tool_specs) or 60,
            )

        # SYSTEM / unknown — skip
        return None


class ChatView(QScrollArea):
    """Scrollable chat area that renders TurnEvents into widgets."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("chat_scroll")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setObjectName("chat_container")
        # Prevent the container from requesting more width than the viewport;
        # this is critical for word-wrap to work inside a QScrollArea.
        self._container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)
        self._layout.addStretch()
        self.setWidget(self._container)

        # Set to True during ``restore_from_messages`` so the per-widget
        # ``resizeEvent`` cascade is suppressed. See that method.
        self._in_restore: bool = False

        # Track current assistant widget for streaming
        self._current_assistant: AssistantMessageWidget | None = None
        self._tool_widgets: dict[str, ToolCallWidget] = {}
        self._thinking: ThinkingWidget | None = None
        self._thinking_shown_at: float = 0.0
        self._plan_view: PlanView | None = None

        # Consecutive tool run state (collapsed when threshold is reached)
        self._tool_run_ids: list[str] = []
        self._tool_run_names: list[str] = []
        self._tool_run_widgets: list[ToolCallWidget] = []
        # Active collapsible group for the current run
        self._tool_group: ToolGroupWidget | None = None
        # Map tool_call_id -> group it belongs to (for result routing/status)
        self._group_map: dict[str, ToolGroupWidget] = {}

        # Async restore state.  ``_restore_generation`` is bumped on
        # every new restore (and on cancel) so any in-flight chunks
        # from a superseded worker are ignored.
        self._restore_generation: int = 0
        self._restore_worker: RestoreWorker | None = None
        self._placeholders: dict[str, MessagePlaceholder] = {}

        # Member timer for scroll-to-bottom — coalesce at 80ms to reduce
        # layout thrashing during rapid streaming
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(80)
        self._scroll_timer.timeout.connect(self._do_scroll)

        # Timer for minimum thinking display duration (500ms)
        self._thinking_hide_timer = QTimer(self)
        self._thinking_hide_timer.setSingleShot(True)
        self._thinking_hide_timer.timeout.connect(self._force_hide_thinking)

        # Plain Python callbacks avoid extra Qt signal traffic in the hot chat path.
        self._tool_approval_callback = None
        self._user_answer_callback = None

    def set_tool_approval_callback(self, callback) -> None:
        self._tool_approval_callback = callback

    def set_user_answer_callback(self, callback) -> None:
        self._user_answer_callback = callback

    def add_user_message(self, text: str) -> None:
        widget = UserMessageWidget(text, parent=self._container)
        self._insert_widget(widget)
        self._current_assistant = None

    def add_error_message(self, text: str) -> None:
        self._insert_widget(ErrorMessageWidget(text, parent=self._container))
        self._scroll_to_bottom()

    def add_queued_message(self, text: str) -> None:
        self._insert_widget(QueuedMessageWidget(text, parent=self._container))
        self._scroll_to_bottom()

    def remove_queued_messages(self) -> None:
        """Remove all [queued] message widgets (e.g. on cancel)."""
        for i in reversed(range(self._layout.count())):
            item = self._layout.itemAt(i)
            widget = item.widget() if item else None
            if isinstance(widget, QueuedMessageWidget):
                self._layout.removeWidget(widget)
                widget.deleteLater()

    def pop_first_queued_message(self) -> None:
        """Remove the first [queued] widget (when it gets submitted)."""
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            widget = item.widget() if item else None
            if isinstance(widget, QueuedMessageWidget):
                self._layout.removeWidget(widget)
                widget.deleteLater()
                return

    def _show_thinking(self) -> None:
        if self._thinking is not None:
            return
        self._thinking = ThinkingWidget(parent=self._container)
        self._thinking_shown_at = time.monotonic()
        self._insert_widget(self._thinking)
        self._scroll_to_bottom()

    def _hide_thinking(self) -> None:
        if self._thinking is None:
            return
        elapsed_ms = (time.monotonic() - self._thinking_shown_at) * 1000
        if elapsed_ms < _THINKING_MIN_DISPLAY_MS:
            remaining = int(_THINKING_MIN_DISPLAY_MS - elapsed_ms)
            self._thinking_hide_timer.start(remaining)
            return
        self._force_hide_thinking()

    def _force_hide_thinking(self) -> None:
        if self._thinking is None:
            return
        self._thinking.stop()
        self._layout.removeWidget(self._thinking)
        self._thinking.deleteLater()
        self._thinking = None

    def _reset_tool_run(self) -> None:
        """End the current consecutive tool run (state only)."""
        self._tool_group = None
        self._tool_run_ids.clear()
        self._tool_run_names.clear()
        self._tool_run_widgets.clear()

    def _register_tool_widget(self, tool_name: str, tool_id: str, widget: ToolCallWidget) -> None:
        """Attach a new tool widget to the current run, collapsing at threshold."""
        self._tool_run_ids.append(tool_id)
        self._tool_run_names.append(tool_name)
        self._tool_run_widgets.append(widget)

        run_len = len(self._tool_run_widgets)

        # Below threshold: show tool calls directly.
        if self._tool_group is None and run_len < _TOOL_GROUP_MIN_CALLS:
            self._insert_widget(widget)
            return

        # Threshold reached: move entire run into a new collapsible group.
        if self._tool_group is None and run_len == _TOOL_GROUP_MIN_CALLS:
            self._tool_group = ToolGroupWidget()
            self._insert_widget(self._tool_group)

            for idx, run_widget in enumerate(self._tool_run_widgets):
                self._layout.removeWidget(run_widget)
                run_widget.hide_preview()

                run_tool_id = self._tool_run_ids[idx]
                run_tool_name = self._tool_run_names[idx]
                self._tool_group.add_widget(run_widget, run_tool_name)
                self._group_map[run_tool_id] = self._tool_group
            return

        # Already collapsed: add new call directly to existing group.
        widget.hide_preview()
        if self._tool_group is not None:
            self._tool_group.add_widget(widget, tool_name)
            self._group_map[tool_id] = self._tool_group

    def handle_event(self, event: TurnEvent) -> None:
        """Process a TurnEvent and update the UI accordingly."""
        etype = event.type
        if etype in (TurnEventType.TEXT_DELTA, TurnEventType.TEXT_DONE):
            self._handle_text_event(event)
        elif etype in (
            TurnEventType.TOOL_CALL_START,
            TurnEventType.TOOL_CALL_ARGS_DELTA,
            TurnEventType.TOOL_CALL_DONE,
            TurnEventType.TOOL_RESULT,
            TurnEventType.TOOL_APPROVAL_REQUEST,
        ):
            self._handle_tool_event(event)
        elif etype in (
            TurnEventType.TURN_START,
            TurnEventType.TURN_END,
            TurnEventType.CANCELLED,
        ):
            self._handle_lifecycle_event(event)
        elif etype in (
            TurnEventType.PLAN_GENERATED,
            TurnEventType.PLAN_STEP_START,
            TurnEventType.PLAN_STEP_DONE,
        ):
            self._handle_plan_event(event)
        elif etype in (
            TurnEventType.EXPLORATION_PHASE_CHANGE,
            TurnEventType.EXPLORATION_FINDING,
        ):
            self._handle_exploration_event(event)
        elif etype in (
            TurnEventType.RESEARCH_NOTE_SAVED,
            TurnEventType.RESEARCH_NOTE_REVIEWED,
        ):
            self._handle_research_event(event)
        elif etype in (
            TurnEventType.USER_QUESTION,
            TurnEventType.SAVE_APPROVAL_REQUEST,
        ):
            self._handle_question_event(event)
        elif etype in (
            TurnEventType.SUBAGENT_SPAWNED,
            TurnEventType.SUBAGENT_COMPLETED,
            TurnEventType.SUBAGENT_FAILED,
        ):
            self._handle_subagent_event(event)
        elif etype == TurnEventType.ERROR:
            self._hide_thinking()
            self._reset_tool_run()
            self._insert_widget(ErrorMessageWidget(event.error or "Unknown error", parent=self._container))
            self._scroll_to_bottom()

    def _handle_text_event(self, event: TurnEvent) -> None:
        self._hide_thinking()
        self._reset_tool_run()
        if event.type == TurnEventType.TEXT_DELTA:
            if self._current_assistant is None:
                self._current_assistant = AssistantMessageWidget(parent=self._container)
                self._insert_widget(self._current_assistant)
            self._current_assistant.append_text(event.text)
            self._scroll_to_bottom()
        else:  # TEXT_DONE
            if self._current_assistant is not None:
                self._current_assistant.set_text(event.text)
            self._current_assistant = None

    def _handle_tool_event(self, event: TurnEvent) -> None:
        etype = event.type
        if etype == TurnEventType.TOOL_CALL_START:
            self._hide_thinking()
            tw = ToolCallWidget(event.tool_name, event.tool_call_id, parent=self._container)
            self._tool_widgets[event.tool_call_id] = tw
            self._register_tool_widget(event.tool_name, event.tool_call_id, tw)
            self._scroll_to_bottom()
        elif etype == TurnEventType.TOOL_CALL_ARGS_DELTA:
            existing_tw = self._tool_widgets.get(event.tool_call_id)
            if existing_tw is not None:
                existing_tw.append_args_delta(event.tool_args)
        elif etype == TurnEventType.TOOL_CALL_DONE:
            existing_tw = self._tool_widgets.get(event.tool_call_id)
            if existing_tw is not None:
                existing_tw.set_arguments(event.tool_args)
        elif etype == TurnEventType.TOOL_RESULT:
            self._reset_tool_run()
            existing_tw = self._tool_widgets.get(event.tool_call_id)
            if existing_tw is not None:
                existing_tw.set_result(event.tool_result, event.tool_is_error)
            group = self._group_map.get(event.tool_call_id)
            if group:
                group.notify_result(event.tool_is_error)
            self._scroll_to_bottom()
        elif etype == TurnEventType.TOOL_APPROVAL_REQUEST:
            self._hide_thinking()
            self._reset_tool_run()
            widget = ToolApprovalWidget(
                event.tool_call_id,
                event.tool_name,
                event.tool_args,
                event.text,
                parent=self._container,
            )
            widget.set_approved_callback(self._on_tool_approval)
            self._insert_widget(widget)
            self._scroll_to_bottom()

    def _handle_lifecycle_event(self, event: TurnEvent) -> None:
        etype = event.type
        if etype == TurnEventType.TURN_START:
            self._current_assistant = None
            self._reset_tool_run()
            self._group_map.clear()
            self._show_thinking()
            self._scroll_to_bottom()
        elif etype == TurnEventType.TURN_END:
            self._hide_thinking()
            self._reset_tool_run()
            self._current_assistant = None
        elif etype == TurnEventType.CANCELLED:
            self._hide_thinking()
            self._reset_tool_run()
            self._insert_widget(ErrorMessageWidget("Cancelled by user", parent=self._container))
            self._scroll_to_bottom()

    def _handle_plan_event(self, event: TurnEvent) -> None:
        etype = event.type
        if etype == TurnEventType.PLAN_GENERATED:
            self._hide_thinking()
            self._reset_tool_run()
            self._plan_view = PlanView(parent=self._container)
            if event.plan_steps:
                self._plan_view.set_plan(event.plan_steps)

            def _on_plan_approve(pv=self._plan_view):
                pv.set_buttons_visible(False)
                self._on_user_answer("approve")

            def _on_plan_reject(pv=self._plan_view):
                pv.set_buttons_visible(False)
                self._on_user_answer("reject")

            self._plan_view.set_approved_callback(_on_plan_approve)
            self._plan_view.set_rejected_callback(_on_plan_reject)
            self._insert_widget(self._plan_view)
            self._scroll_to_bottom()
        elif etype == TurnEventType.PLAN_STEP_START:
            if self._plan_view:
                self._plan_view.set_step_status(event.plan_step_index, "active")
                self._plan_view.set_buttons_visible(False)
            self._scroll_to_bottom()
        elif etype == TurnEventType.PLAN_STEP_DONE:
            if self._plan_view:
                self._plan_view.set_step_status(event.plan_step_index, "done")
            self._scroll_to_bottom()

    def _handle_exploration_event(self, event: TurnEvent) -> None:
        meta = event.metadata
        if event.type == TurnEventType.EXPLORATION_PHASE_CHANGE:
            self._hide_thinking()
            self._reset_tool_run()
            self._insert_widget(
                ExplorationPhaseWidget(
                    meta.get("from_phase", ""),
                    meta.get("to_phase", ""),
                    event.text,
                    parent=self._container,
                )
            )
        else:  # EXPLORATION_FINDING
            self._insert_widget(
                ExplorationFindingWidget(
                    meta.get("category", "general"),
                    event.text,
                    meta.get("address"),
                    meta.get("relevance", "medium"),
                    parent=self._container,
                )
            )
        self._scroll_to_bottom()

    def _handle_research_event(self, event: TurnEvent) -> None:
        meta = event.metadata
        if event.type == TurnEventType.RESEARCH_NOTE_SAVED:
            self._hide_thinking()
            self._reset_tool_run()
            self._insert_widget(
                ResearchNoteWidget(
                    title=event.text,
                    genre=meta.get("genre", "general"),
                    path=meta.get("path", ""),
                    preview=meta.get("preview", ""),
                    review_passed=meta.get("review_passed", True),
                    parent=self._container,
                )
            )
            self._scroll_to_bottom()
        # RESEARCH_NOTE_REVIEWED — no separate widget, info is in the saved event

    def _handle_subagent_event(self, event: TurnEvent) -> None:
        meta = event.metadata
        if event.type == TurnEventType.SUBAGENT_SPAWNED:
            name = event.text
            agent_type = meta.get("agent_type", "custom")
            self._insert_widget(SubagentEventWidget("spawned", name, f"type: {agent_type}", parent=self._container))
        elif event.type == TurnEventType.SUBAGENT_COMPLETED:
            name = meta.get("name", "")
            turns = meta.get("turn_count", 0)
            elapsed = meta.get("elapsed", 0.0)
            detail = f"{turns} turns, {elapsed:.0f}s"
            self._insert_widget(SubagentEventWidget("completed", name, detail, parent=self._container))
        elif event.type == TurnEventType.SUBAGENT_FAILED:
            name = meta.get("name", "")
            error = event.error or "Unknown error"
            self._insert_widget(SubagentEventWidget("failed", name, error, parent=self._container))
        self._scroll_to_bottom()

    def _handle_question_event(self, event: TurnEvent) -> None:
        self._hide_thinking()
        self._reset_tool_run()
        if event.type == TurnEventType.SAVE_APPROVAL_REQUEST:
            options = ["Save All", "Discard All"]
        else:  # USER_QUESTION
            options = event.metadata.get("options", [])
        widget = UserQuestionWidget(event.text, options, parent=self._container)
        widget.set_option_selected_callback(self._on_user_answer)
        self._insert_widget(widget)
        self._scroll_to_bottom()

    def _on_tool_approval(self, tool_call_id: str, decision: str) -> None:
        """Forward tool approval decision to the panel/controller."""
        if self._tool_approval_callback is not None:
            self._tool_approval_callback(tool_call_id, decision)

    def _on_user_answer(self, answer: str) -> None:
        """Forward a button-selected answer to the panel/controller."""
        if self._user_answer_callback is not None:
            self._user_answer_callback(answer)

    def restore_from_messages(self, messages: list[Message]) -> None:
        """Replay saved Message objects into the chat view.

        Sets ``_in_restore`` so the cascade of ``resizeEvent`` calls
        triggered by every ``insertWidget`` is suppressed — without
        this, 50+ widgets can each trigger a ``setFixedWidth`` and a
        full layout pass, which dominates restore time (~50% in
        profiling). The width is fixed up explicitly at the end.
        """
        self.clear_chat()
        self._in_restore = True

        for msg in messages:
            if msg.role == Role.USER:
                if _is_hidden_system_user_message(msg.content):
                    continue
                self._reset_tool_run()
                self.add_user_message(msg.content)

            elif msg.role == Role.ASSISTANT:
                self._reset_tool_run()
                if msg.content:
                    w = AssistantMessageWidget(parent=self._container)
                    # Defer markdown render: while the widget is hidden
                    # (e.g. inside an inactive tab) there's no need to
                    # pay the md_to_html cost. ``showEvent`` triggers the
                    # render on first visibility, which is exactly when
                    # the user is about to see the message.
                    w.set_text_deferred(msg.content)
                    self._insert_widget(w)

                for tc in msg.tool_calls:
                    tw = ToolCallWidget(tc.name, tc.id, parent=self._container)
                    try:
                        args_str = json.dumps(tc.arguments, indent=2)
                    except (TypeError, ValueError):
                        args_str = str(tc.arguments)
                    tw.set_arguments(args_str)
                    tw.mark_done()
                    self._tool_widgets[tc.id] = tw
                    self._register_tool_widget(tc.name, tc.id, tw)

            elif msg.role == Role.TOOL:
                self._reset_tool_run()
                for tr in msg.tool_results:
                    existing_tw = self._tool_widgets.get(tr.tool_call_id)
                    if existing_tw is not None:
                        existing_tw.set_result(tr.content, tr.is_error)
                    group = self._group_map.get(tr.tool_call_id)
                    if group:
                        group.notify_result(tr.is_error)

        self._current_assistant = None
        self._reset_tool_run()
        # Restore finished — width is constant for the whole batch, so
        # re-apply it once here and re-enable per-widget resize handling.
        self._in_restore = False
        if self._container is not None:
            self._container.setFixedWidth(self.viewport().width())
        self._scroll_to_bottom()

    # ------------------------------------------------------------------
    # Async restore — uses a worker thread to build MessageSpecs without
    # blocking the GUI.  The main thread inserts MessagePlaceholders up
    # front (so scrollbar geometry is correct from frame 1) and replaces
    # them with real widgets as each chunk_ready signal arrives.
    # ------------------------------------------------------------------

    def restore_from_messages_async(self, messages: list[Message]) -> None:
        """Start a background restore of *messages*.

        Behaviour:
        1. Cancels any in-flight restore (its worker is told to stop and
           any late signals are dropped via a generation counter).
        2. Clears the view and immediately inserts one
           :class:`MessagePlaceholder` per message so the layout has a
           correct total height.  This gives the QScrollArea an accurate
           ``verticalScrollBar().maximum()`` from the first paint.
        3. Starts a :class:`RestoreWorker` thread that builds
           ``MessageSpec`` objects off the UI thread.  Each
           ``chunk_ready`` slot replaces the corresponding placeholders
           with real widgets.

        Idempotency: calling this method twice cancels the first
        worker and discards its late signals.
        """
        # Cancel any prior worker — late signals are dropped via
        # ``_restore_generation`` below.
        self._cancel_restore()

        self.clear_chat()
        self._in_restore = True

        # Bump generation so any late signals from the prior worker
        # are ignored.  Captured in closures for chunk/finished slots.
        self._restore_generation += 1
        generation = self._restore_generation

        # Insert one placeholder per message so the layout is full from
        # the start.  Skip hidden system messages — the worker also
        # skips them, so we mirror the count.
        self._placeholders: dict[str, MessagePlaceholder] = {}
        for idx, msg in enumerate(messages):
            if msg.role == Role.USER and _is_hidden_system_user_message(msg.content):
                continue
            placeholder_id = msg.id or f"restore_{idx}"
            # Use a per-message heuristic so placeholders track the
            # content size closely enough for the scrollbar.
            est = self._placeholder_height_for(msg)
            ph = MessagePlaceholder(est, placeholder_id, parent=self._container)
            self._insert_widget(ph)
            self._placeholders[placeholder_id] = ph

        # Pin width once now; widgets added later inherit it.
        if self._container is not None:
            self._container.setFixedWidth(self.viewport().width())

        # Start the worker.  Slots capture ``generation`` so they can
        # bail out if a newer restore has superseded us.
        worker = RestoreWorker(messages, parent=self)
        worker.chunk_ready.connect(
            lambda chunk, gen=generation: self._on_chunk_ready(chunk, gen)
        )
        worker.finished_ok.connect(
            lambda gen=generation: self._on_restore_finished(gen)
        )
        # ``finished`` is emitted by QThread when ``run`` returns; use
        # it as a hard cleanup point regardless of ``finished_ok``.
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
        self._restore_worker = worker
        worker.start()

    @staticmethod
    def _placeholder_height_for(msg: Message) -> int:
        """Cheap height estimate for the placeholder of a single message."""
        if msg.role == Role.USER:
            return _estimate_user_height(msg.content)
        if msg.role == Role.ASSISTANT:
            return _estimate_assistant_height(msg.content, "")
        if msg.role == Role.TOOL:
            return max(60, 80 * len(msg.tool_results or msg.tool_calls))
        return 60

    def _cancel_restore(self) -> None:
        """Cancel the in-flight restore (if any) and bump generation."""
        worker = getattr(self, "_restore_worker", None)
        if worker is not None:
            try:
                worker.cancel()
            except RuntimeError:
                pass  # already deleted
        self._restore_generation += 1
        self._restore_worker = None

    def _on_chunk_ready(self, chunk: _RenderedChunk, generation: int) -> None:
        """Replace placeholders with real widgets for one chunk.

        Drops the chunk if a newer restore has superseded this worker.
        """
        if generation != self._restore_generation:
            return  # superseded
        for spec in chunk.specs:
            ph = self._placeholders.pop(spec.msg_id, None)
            if ph is None:
                continue
            widget = self._build_widget_from_spec(spec)
            if widget is None:
                # Filtered out — leave a 0-height placeholder? Easier to
                # just remove the placeholder so the layout shrinks.
                ph.setMinimumHeight(0)
                ph.setMaximumHeight(0)
                ph.deleteLater()
                continue
            # Replace placeholder with the real widget at the same
            # position.  ``_insert_at`` swaps them preserving layout.
            self._replace_placeholder(ph, widget)
        # Trigger a single repaint of the affected region.
        if self._container is not None:
            self._container.update()

    def _on_restore_finished(self, generation: int) -> None:
        if generation != self._restore_generation:
            return
        # All placeholders should be gone; clear any leftovers.
        leftovers = list(self._placeholders.values())
        self._placeholders.clear()
        for ph in leftovers:
            ph.deleteLater()
        self._in_restore = False
        # Reapply width and scroll-to-bottom now that the real widgets
        # are in place.
        if self._container is not None:
            self._container.setFixedWidth(self.viewport().width())
        self._scroll_to_bottom()

    def _on_worker_finished(self, worker: RestoreWorker) -> None:
        """Cleanup hook for the worker's QThread.finished signal.

        Decouples the worker from the view so it can be GC'd.  Note:
        we do NOT touch _restore_worker here because the worker's
        ``finished_ok`` slot (or a cancel) is the source of truth for
        restore completion.
        """
        try:
            worker.chunk_ready.disconnect()
            worker.finished_ok.disconnect()
        except (TypeError, RuntimeError):
            pass
        worker.deleteLater()

    def _replace_placeholder(
        self, placeholder: MessagePlaceholder, widget: QWidget
    ) -> None:
        """Replace *placeholder* in the layout with *widget* in-place."""
        layout = self._layout
        if layout is None:
            return
        # Find placeholder's index in the layout.
        idx = layout.indexOf(placeholder)
        if idx < 0:
            # Placeholder already gone — just insert at end.
            self._insert_widget(widget)
            return
        # Drop placeholder, insert widget at the same slot.
        layout.removeWidget(placeholder)
        placeholder.setParent(None)
        placeholder.deleteLater()
        # The original layout has a trailing stretch; insert at the
        # captured index so the new widget sits exactly where the
        # placeholder was.
        if idx >= layout.count():
            self._insert_widget(widget)
        else:
            layout.insertWidget(idx, widget)

    def _build_widget_from_spec(self, spec: MessageSpec) -> QWidget | None:
        """Materialise a real widget from a pre-built MessageSpec."""
        try:
            role = Role(spec.role)
        except ValueError:
            return None

        if role == Role.USER:
            if _is_hidden_system_user_message(spec.content):
                return None
            return UserMessageWidget(spec.content, parent=self._container)

        if role == Role.ASSISTANT:
            if not spec.content:
                return None
            w = AssistantMessageWidget(parent=self._container)
            # ``content_html`` was pre-rendered on the worker thread,
            # so we can short-circuit set_text_deferred by setting the
            # text directly.  But to keep behaviour identical to the
            # sync path, we still call set_text_deferred which will
            # re-render on first show.  This is a no-op the user will
            # see (the assistant message text is the same).
            w.set_text_deferred(spec.content)
            return w

        if role == Role.TOOL:
            # Build ToolCallWidget for each tool spec and route the
            # result via the existing TOOL handler path.
            # The current sync path processes ASSISTANT tool_calls and
            # TOOL results in two separate iterations; mirror that.
            # For async, we collapse them into one widget by building
            # the tool widget with a result.  ``ToolCallWidget.set_result``
            # is the public way to attach a result.
            for ts in spec.tool_specs:
                try:
                    args = json.loads(ts.arguments_json) if ts.arguments_json else {}
                except (ValueError, TypeError):
                    args = {}
                tc = ToolCall(
                    id=ts.id,
                    name=ts.name,
                    arguments=args,
                )
                tw = ToolCallWidget(tc.name, tc.id, parent=self._container)
                # Pre-set the result so the widget shows complete state.
                if ts.result_content or ts.result_is_error:
                    tw.set_result(ts.result_content, ts.result_is_error)
                self._tool_widgets[tc.id] = tw
                self._register_tool_widget(tc.name, tc.id, tw)
            # The actual TOOL message has no body — just tool widgets.
            # Return a dummy 0-height frame so the layout keeps a slot.
            # In practice the per-tool widgets above have already been
            # inserted; we return None to signal "no body widget".
            return None

        return None

    def clear_chat(self) -> None:
        # Cancel any in-flight async restore so its worker stops
        # emitting signals while we tear down the widgets.
        self._cancel_restore()
        self._force_hide_thinking()
        self._thinking_hide_timer.stop()
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._current_assistant = None
        self._tool_widgets.clear()
        self._plan_view = None
        self._reset_tool_run()
        self._group_map.clear()
        self._placeholders.clear()

    def _insert_widget(self, widget: QWidget) -> None:
        """Insert before the stretch at the end."""
        idx = self._layout.count() - 1
        self._layout.insertWidget(idx, widget)

    def resizeEvent(self, event) -> None:
        """Keep the container width pinned to the viewport width.

        QScrollArea.setWidgetResizable(True) handles this when there is no
        horizontal scrollbar, but QLabel rich-text word-wrap still sometimes
        requests a wider sizeHint.  Explicitly clamping here guarantees text
        wraps to the visible area.

        Suppressed during ``restore_from_messages`` because every
        ``insertWidget`` triggers a resize cascade; 50+ widgets in
        a row causes 50+ ``setFixedWidth`` calls (~50% of total
        restore time in profiling). The width is reapplied once at
        the end of the restore.
        """
        super().resizeEvent(event)
        if self._container is not None and not getattr(self, "_in_restore", False):
            self._container.setFixedWidth(self.viewport().width())

    def _is_near_bottom(self) -> bool:
        """True if the user hasn't scrolled up (within ~60px of bottom)."""
        sb = self.verticalScrollBar()
        return sb.maximum() - sb.value() < 60

    def _scroll_to_bottom(self) -> None:
        if self._is_near_bottom():
            self._scroll_timer.start()

    def _do_scroll(self) -> None:
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def shutdown(self) -> None:
        self._cancel_restore()
        self._scroll_timer.stop()
        self._thinking_hide_timer.stop()
        self._force_hide_thinking()
        self._tool_approval_callback = None
        self._user_answer_callback = None
