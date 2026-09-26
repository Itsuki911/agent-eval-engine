"""評価実行のイベントを収集する。"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from opentelemetry.trace import Span, Tracer

from agent_eval.tool_tracer import ToolTracer


# 実行中の1イベントを表す
@dataclass(frozen=True)
class CollectedEvent:
    sequence: int
    event_type: str
    payload: dict[str, Any]
    actor: str = "engine"
    previous_state: dict[str, Any] | None = None
    next_state: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    trace_id: str | None = None
    span_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# イベントを順序付きで収集する
class EventCollector:
    # 収集先とトレーサーを受け取る
    def __init__(
        self,
        tracer: Tracer,
        listener: Callable[[CollectedEvent], None] | None = None,
        tool_tracer: ToolTracer | None = None,
    ) -> None:
        self._tracer = tracer
        self._tool_tracer = tool_tracer or ToolTracer(tracer)
        self._events: list[CollectedEvent] = []
        self._listener = listener

    # 現在の追跡IDを文字列へ変える
    def _trace_context(self) -> tuple[str | None, str | None]:
        span = self._tracer.start_span("event.collect")
        span_context = span.get_span_context()
        span.end()
        if not span_context.is_valid:
            return None, None
        return f"{span_context.trace_id:032x}", f"{span_context.span_id:016x}"

    # ツール実行をイベントへ連携する
    @contextmanager
    def tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        category: str | None = None,
    ) -> Generator[Span, None, None]:
        with self._tool_tracer.tool(tool_name, arguments, category) as span:
            yield span

    # イベントを記録して返す
    def record(
        self,
        event_type: str,
        payload: dict[str, Any],
        actor: str = "engine",
        previous_state: dict[str, Any] | None = None,
        next_state: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> CollectedEvent:
        trace_id, span_id = self._trace_context()
        event = CollectedEvent(
            sequence=len(self._events),
            event_type=event_type,
            payload=payload,
            actor=actor,
            previous_state=previous_state,
            next_state=next_state,
            error=error,
            trace_id=trace_id,
            span_id=span_id,
        )
        self._events.append(event)
        if self._listener is not None:
            self._listener(event)
        return event

    # 収集済みイベントを返す
    def events(self) -> list[CollectedEvent]:
        return list(self._events)
