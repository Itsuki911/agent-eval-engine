"""個別ツールのOpenTelemetry計測を行う。"""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry.trace import Span, Status, StatusCode, Tracer


_SECRET_MARKERS = ("api_key", "authorization", "password", "secret", "token")


# 属性値を安全に変換する
def _sanitize_attribute(key: str, value: Any) -> str | int | float | bool:
    if any(marker in key.casefold() for marker in _SECRET_MARKERS):
        return "[REDACTED]"
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


# 個別ツールのSpanを計測する
@contextmanager
def trace_tool(
    tracer: Tracer,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    category: str | None = None,
) -> Generator[Span, None, None]:
    span_name = f"tool.{tool_name}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("tool.name", tool_name)
        if category:
            span.set_attribute("tool.category", category)
        if arguments:
            for key, value in arguments.items():
                span.set_attribute(f"tool.arguments.{key}", _sanitize_attribute(key, value))
        try:
            yield span
        except Exception as error:
            span.set_status(Status(StatusCode.ERROR, f"{type(error).__name__}: {error}"))
            raise


# ツール計測用ヘルパーを表す
class ToolTracer:
    # トレーサーを初期化する
    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    # ツール実行を計測する
    @contextmanager
    def tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        category: str | None = None,
    ) -> Generator[Span, None, None]:
        with trace_tool(self._tracer, tool_name, arguments, category) as span:
            yield span

    # フェーズ実行を計測する
    @contextmanager
    def step(self, step_name: str) -> Generator[Span, None, None]:
        with self._tracer.start_as_current_span(step_name) as span:
            yield span
