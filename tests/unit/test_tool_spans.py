# 注意点: InMemoryExporterで検証し本番影響を防ぐ
# 別案: 実コンソール出力の正規表現検証も可能
"""個別ツールのOpenTelemetryスパン階層を検証する。"""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from agent_eval.events import EventCollector
from tests.output import print_test_result
from agent_eval.tool_tracer import ToolTracer, trace_tool


# メモリ内エクスポータとトレーサーを作る
@pytest.fixture
def memory_telemetry():
    exporter = InMemorySpanExporter()
    resource = Resource.create({SERVICE_NAME: "tool-span-test"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("tool_span_test")
    return tracer, exporter


# 個別ツールの独立スパン階層を検証する
def test_individual_tool_spans_hierarchy(memory_telemetry) -> None:
    tracer, exporter = memory_telemetry

    # ルートスパン -> ステップスパン -> 個別ツールスパン
    with tracer.start_as_current_span("agent.run") as root_span:
        root_context = root_span.get_span_context()

        with tracer.start_as_current_span("inspect") as step_span:
            step_context = step_span.get_span_context()

            # tool.read の個別スパン
            with trace_tool(tracer, "read", {"path": "main.py"}):
                pass

            # tool.search の個別スパン
            with trace_tool(tracer, "search", {"query": "def run"}):
                pass

        with tracer.start_as_current_span("test") as test_step_span:
            test_step_context = test_step_span.get_span_context()

            # tool.bash の個別スパン
            with trace_tool(tracer, "bash", {"command": "pytest"}):
                pass

    spans = exporter.get_finished_spans()
    span_by_name = {span.name: span for span in spans}

    # 必要なスパンがすべて存在すること
    assert "agent.run" in span_by_name
    assert "inspect" in span_by_name
    assert "tool.read" in span_by_name
    assert "tool.search" in span_by_name
    assert "test" in span_by_name
    assert "tool.bash" in span_by_name

    root_id = root_context.span_id
    trace_id = root_context.trace_id

    # 全スパンが同一の Trace ID を持つこと
    for span in spans:
        assert span.context.trace_id == trace_id

    # 階層関係（親ID）の検証
    inspect_span = span_by_name["inspect"]
    assert inspect_span.parent.span_id == root_id

    read_span = span_by_name["tool.read"]
    assert read_span.parent.span_id == inspect_span.context.span_id
    assert read_span.attributes.get("tool.name") == "read"
    assert read_span.attributes.get("tool.arguments.path") == "main.py"

    search_span = span_by_name["tool.search"]
    assert search_span.parent.span_id == inspect_span.context.span_id

    bash_span = span_by_name["tool.bash"]
    assert bash_span.parent.span_id == test_step_span.get_span_context().span_id
    assert bash_span.attributes.get("tool.name") == "bash"

    print_test_result(
        "individual_tool_spans_hierarchy",
        "passed",
        span_count=len(spans),
        tool_spans=["tool.read", "tool.search", "tool.bash"],
    )


# ツールエラー時にスパンへ異常が記録される
def test_tool_span_records_error(memory_telemetry) -> None:
    tracer, exporter = memory_telemetry

    with pytest.raises(FileNotFoundError):
        with trace_tool(tracer, "read", {"path": "missing.py"}):
            raise FileNotFoundError("missing.py が存在しません")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    tool_span = spans[0]

    assert tool_span.name == "tool.read"
    assert tool_span.status.status_code == StatusCode.ERROR
    assert "FileNotFoundError" in tool_span.status.description

    # 例外イベントがスパン内に記録されていること
    exception_events = [ev for ev in tool_span.events if ev.name == "exception"]
    assert len(exception_events) == 1
    assert "missing.py" in str(exception_events[0].attributes.get("exception.message"))

    print_test_result(
        "tool_span_records_error",
        "passed",
        status_code=tool_span.status.status_code.name,
        error_recorded=True,
    )


# 秘密情報をSpan属性へ記録しない
def test_tool_span_masks_secret_arguments(memory_telemetry) -> None:
    tracer, exporter = memory_telemetry

    with trace_tool(tracer, "request", {"api_key": "secret-value", "path": "main.py"}):
        pass

    tool_span = exporter.get_finished_spans()[0]
    assert tool_span.attributes.get("tool.arguments.api_key") == "[REDACTED]"
    assert tool_span.attributes.get("tool.arguments.path") == "main.py"

    print_test_result(
        "tool_span_masks_secret_arguments",
        "passed",
        secret_redacted=True,
    )


# ツール実行中イベントとスパンが連動する
def test_tool_span_with_event_collector(memory_telemetry) -> None:
    tracer, exporter = memory_telemetry
    collector = EventCollector(tracer)

    with tracer.start_as_current_span("agent.run") as root_span:
        with collector.tool("write", {"path": "out.txt", "size": 100}) as current_tool_span:
            tool_context = current_tool_span.get_span_context()
            # ツール実行中にイベントを記録
            event = collector.record("tool_called", {"file": "out.txt"}, actor="agent")

    spans = exporter.get_finished_spans()
    span_by_name = {span.name: span for span in spans}

    assert "tool.write" in span_by_name
    # イベント収集時のスパンの親が tool.write であること
    collect_spans = [s for s in spans if s.name == "event.collect"]
    assert len(collect_spans) == 1
    assert collect_spans[0].parent.span_id == tool_context.span_id
    assert event.trace_id == f"{tool_context.trace_id:032x}"

    print_test_result(
        "tool_span_with_event_collector",
        "passed",
        event_type=event.event_type,
        parent_span="tool.write",
    )


# 03_ARCHITECTURE設計書のツリー構造を検証する
def test_agent_architecture_tree_hierarchy(memory_telemetry) -> None:
    tracer, exporter = memory_telemetry
    tt = ToolTracer(tracer)

    with tracer.start_as_current_span("agent.run") as root_span:
        root_id = root_span.get_span_context().span_id

        # 1. planner -> llm.call
        with tt.step("planner") as planner_span:
            with tracer.start_as_current_span("llm.call"):
                pass

        # 2. inspect -> tool.read, tool.search
        with tt.step("inspect") as inspect_span:
            with tt.tool("read", {"file": "core.py"}):
                pass
            with tt.tool("search", {"pattern": "class Runner"}):
                pass

        # 3. edit -> tool.write
        with tt.step("edit") as edit_span:
            with tt.tool("write", {"file": "core.py", "lines": 10}):
                pass

        # 4. test -> tool.bash
        with tt.step("test") as test_span:
            with tt.tool("bash", {"cmd": "pytest -q"}):
                pass

        # 5. reflection -> llm.call
        with tt.step("reflection") as refl_span:
            with tracer.start_as_current_span("llm.call"):
                pass

    spans = exporter.get_finished_spans()
    span_map = {span.name: [] for span in spans}
    for span in spans:
        span_map[span.name].append(span)

    # 各フェーズの親が root (agent.run) であること
    for step_name in ["planner", "inspect", "edit", "test", "reflection"]:
        step_spans = span_map[step_name]
        assert len(step_spans) == 1
        assert step_spans[0].parent.span_id == root_id

    # inspect の子が tool.read, tool.search
    inspect_id = span_map["inspect"][0].context.span_id
    assert span_map["tool.read"][0].parent.span_id == inspect_id
    assert span_map["tool.search"][0].parent.span_id == inspect_id

    # edit の子が tool.write
    edit_id = span_map["edit"][0].context.span_id
    assert span_map["tool.write"][0].parent.span_id == edit_id

    # test の子が tool.bash
    test_id = span_map["test"][0].context.span_id
    assert span_map["tool.bash"][0].parent.span_id == test_id

    print_test_result(
        "agent_architecture_tree_hierarchy",
        "passed",
        total_spans=len(spans),
        architecture_verified=True,
    )
