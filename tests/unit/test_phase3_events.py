"""Phase 3の観測イベントを確認する。"""

from agent_eval.config import TelemetrySettings
from agent_eval.events import EventCollector
from agent_eval.telemetry import create_telemetry


# イベントへ追跡IDを付与する
def test_event_collector_adds_trace_context() -> None:
    telemetry = create_telemetry(TelemetrySettings(service_name="test", exporter="none"))
    collector = EventCollector(telemetry.tracer)

    with telemetry.tracer.start_as_current_span("agent.run"):
        event = collector.record("user_prompt", {"content": "test"}, actor="user")

    assert event.sequence == 0
    assert event.trace_id is not None
    assert event.span_id is not None
    print(
        "追跡情報: sequence=0, "
        f"trace_id_length={len(event.trace_id)}, "
        f"span_id_length={len(event.span_id)}"
    )
