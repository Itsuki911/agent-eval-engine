"""イベントから評価指標を計算する。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_eval.events import CollectedEvent


# 保存用の指標値を表す
@dataclass(frozen=True)
class ComputedMetric:
    category: str
    name: str
    value: float
    unit: str | None = None
    dimensions: dict[str, Any] | None = None


# 指標の比率を安全に計算する
def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


# 指定種別のイベントを数える
def _events_of_type(events: list[CollectedEvent], event_type: str) -> list[CollectedEvent]:
    return [event for event in events if event.event_type == event_type]


# 全評価指標を計算する
def calculate_metrics(
    events: list[CollectedEvent], final_state: dict[str, Any], elapsed_ms: float
) -> list[ComputedMetric]:
    tool_calls = _events_of_type(events, "tool_call")
    errors = [event for event in events if event.event_type.endswith("error")]
    safety_events = _events_of_type(events, "safety_violation")
    llm_calls = _events_of_type(events, "llm_call")
    successful_tools = sum(bool(event.payload.get("success")) for event in tool_calls)
    invalid_tools = sum(not bool(event.payload.get("arguments_valid", True)) for event in tool_calls)
    retried_tools = sum(bool(event.payload.get("retry")) for event in tool_calls)
    input_tokens = sum(int(event.payload.get("input_tokens", 0)) for event in llm_calls)
    output_tokens = sum(int(event.payload.get("output_tokens", 0)) for event in llm_calls)
    estimated_cost = sum(float(event.payload.get("estimated_cost_usd", 0)) for event in llm_calls)
    tool_latency = sum(float(event.payload.get("duration_ms", 0)) for event in tool_calls)
    duplicate_calls = _duplicate_tool_calls(tool_calls)
    recovered = _recovered_after_error(events)
    task_success = bool(final_state.get("success")) and not safety_events
    environment_failed = any(event.event_type in {"environment_error", "timeout_error"} for event in errors)

    return [
        ComputedMetric("success", "task_success", float(task_success), "ratio"),
        ComputedMetric("trajectory", "step_count", float(len(events)), "count"),
        ComputedMetric("trajectory", "duplicate_action_count", float(duplicate_calls), "count"),
        ComputedMetric("tool_usage", "tool_call_count", float(len(tool_calls)), "count"),
        ComputedMetric("tool_usage", "tool_success_rate", _ratio(successful_tools, len(tool_calls)), "ratio"),
        ComputedMetric("tool_usage", "invalid_argument_rate", _ratio(invalid_tools, len(tool_calls)), "ratio"),
        ComputedMetric("tool_usage", "retry_count", float(retried_tools), "count"),
        ComputedMetric("tool_usage", "tool_latency_ms", tool_latency, "ms"),
        ComputedMetric("recovery", "recovery_success", float(not errors or recovered), "ratio"),
        ComputedMetric("cost", "input_tokens", float(input_tokens), "tokens"),
        ComputedMetric("cost", "output_tokens", float(output_tokens), "tokens"),
        ComputedMetric("cost", "estimated_cost_usd", estimated_cost, "usd"),
        ComputedMetric("latency", "end_to_end_latency_ms", elapsed_ms, "ms"),
        ComputedMetric("robustness", "environment_stable", float(not environment_failed), "ratio"),
        ComputedMetric("safety", "safety_violation_count", float(len(safety_events)), "count"),
        ComputedMetric("safety", "safety_score", float(not safety_events), "ratio"),
    ]


# 重複したツール呼び出しを数える
def _duplicate_tool_calls(tool_calls: list[CollectedEvent]) -> int:
    seen_calls: set[tuple[str, str]] = set()
    duplicates = 0
    for event in tool_calls:
        call = (str(event.payload.get("name")), repr(event.payload.get("arguments", {})))
        if call in seen_calls:
            duplicates += 1
        seen_calls.add(call)
    return duplicates


# エラー後の回復を判定する
def _recovered_after_error(events: list[CollectedEvent]) -> bool:
    error_seen = False
    for event in events:
        if event.event_type.endswith("error"):
            error_seen = True
        if error_seen and event.event_type == "tool_call" and event.payload.get("success"):
            return True
    return False
