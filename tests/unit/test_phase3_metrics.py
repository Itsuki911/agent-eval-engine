"""Phase 3のイベント評価ロジックを確認する。"""

from agent_eval.events import CollectedEvent
from agent_eval.metrics import calculate_metrics


# 指標を名前で取得する
def _metric_values(metrics):
    return {metric.name: metric.value for metric in metrics}


# 成功した実行の指標を確認する
def test_calculate_metrics_for_successful_run() -> None:
    events = [
        CollectedEvent(0, "llm_call", {"input_tokens": 10, "output_tokens": 5, "estimated_cost_usd": 0.01}),
        CollectedEvent(1, "tool_call", {"name": "lookup", "arguments": {"id": "1"}, "success": True, "duration_ms": 20}),
    ]

    values = _metric_values(calculate_metrics(events, {"success": True}, 100))

    assert values["task_success"] == 1
    assert values["tool_success_rate"] == 1
    assert values["estimated_cost_usd"] == 0.01
    assert values["end_to_end_latency_ms"] == 100
    print(
        "指標計算: task_success=1, tool_success_rate=1, "
        "estimated_cost_usd=0.01, end_to_end_latency_ms=100"
    )


# 安全違反で成功を拒否する
def test_safety_violation_rejects_task_success() -> None:
    events = [CollectedEvent(0, "safety_violation", {"reason": "forbidden action"})]

    values = _metric_values(calculate_metrics(events, {"success": True}, 10))

    assert values["task_success"] == 0
    assert values["safety_violation_count"] == 1
    print("安全判定: task_success=0, safety_violation_count=1")


# 重複と回復を計測する
def test_duplicate_tools_and_recovery_are_measured() -> None:
    events = [
        CollectedEvent(0, "tool_call", {"name": "lookup", "arguments": {"id": "1"}, "success": False}),
        CollectedEvent(1, "tool_error", {"reason": "timeout"}),
        CollectedEvent(2, "tool_call", {"name": "lookup", "arguments": {"id": "1"}, "success": True, "retry": True}),
    ]

    values = _metric_values(calculate_metrics(events, {"success": True}, 10))

    assert values["duplicate_action_count"] == 1
    assert values["recovery_success"] == 1
    assert values["retry_count"] == 1
    print(
        "回復計測: duplicate_action_count=1, "
        "recovery_success=1, retry_count=1"
    )
