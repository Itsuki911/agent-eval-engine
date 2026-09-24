"""LangGraphで評価処理を接続する。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from agent_eval.agent import AgentRunner, build_agent
from agent_eval.benchmark import BenchmarkDefinition, load_benchmark
from agent_eval.config import Phase3Settings
from agent_eval.events import EventCollector
from agent_eval.metrics import ComputedMetric, calculate_metrics
from agent_eval.openrouter import (
    OpenRouterAuthenticationError,
    OpenRouterBadRequestError,
    OpenRouterConnectionError,
    OpenRouterContentFilterError,
    OpenRouterCostLimitError,
    OpenRouterEmptyResponseError,
    OpenRouterError,
    OpenRouterIdempotencyError,
    OpenRouterInputLimitError,
    OpenRouterInvalidFormatError,
    OpenRouterNotFoundError,
    OpenRouterOutputLimitError,
    OpenRouterPermissionError,
    OpenRouterRateLimitError,
    OpenRouterRetryLimitError,
    OpenRouterSafetyFilterError,
    OpenRouterServerError,
    OpenRouterServiceUnavailableError,
    OpenRouterStreamDisconnectedError,
    OpenRouterStructuredOutputError,
    OpenRouterTimeoutError,
    OpenRouterToolCallError,
)
from agent_eval.telemetry import Telemetry, create_telemetry
from database.repositories import RunRepository


# ワークフロー共有状態を表す
class EvaluationState(TypedDict, total=False):
    benchmark_path: str
    benchmark: BenchmarkDefinition
    collector: EventCollector
    run_id: UUID
    final_state: dict[str, Any]
    failure_category: str | None
    metrics: list[ComputedMetric]
    started_at: float
    elapsed_ms: float


# 端末へ返す実行結果を表す
@dataclass(frozen=True)
class EvaluationResult:
    run_id: UUID
    status: str
    benchmark_id: str
    final_state: dict[str, Any]
    metrics: list[ComputedMetric]
    event_count: int


# 評価処理全体を調整する
class EvaluationService:
    # 依存する設定とDBを受け取る
    def __init__(self, settings: Phase3Settings, session: Session, agent: AgentRunner | None = None) -> None:
        self._settings = settings
        self._repository = RunRepository(session)
        self._telemetry: Telemetry = create_telemetry(settings.telemetry)
        self._agent = agent or build_agent(settings)

    # benchmarkを評価して保存する
    def run(self, benchmark_path: str | Path) -> EvaluationResult:
        started_at = perf_counter()
        collector = EventCollector(self._telemetry.tracer)
        graph = self._build_graph()
        with self._telemetry.tracer.start_as_current_span("agent.run"):
            state = graph.invoke(
                {"benchmark_path": str(benchmark_path), "collector": collector, "started_at": started_at}
            )
        elapsed_ms = (perf_counter() - started_at) * 1000
        metrics = state["metrics"]
        self._telemetry.provider.force_flush()
        return EvaluationResult(
            run_id=state["run_id"],
            status="simulated" if state["final_state"].get("dry_run") else "completed" if state["final_state"].get("success") else "failed",
            benchmark_id=state["benchmark"].id,
            final_state=state["final_state"],
            metrics=metrics,
            event_count=len(collector.events()),
        )

    # LangGraphを組み立てる
    def _build_graph(self):
        graph = StateGraph(EvaluationState)
        graph.add_node("load_benchmark", self._load_benchmark)
        graph.add_node("setup_environment", self._setup_environment)
        graph.add_node("run_agent", self._run_agent)
        graph.add_node("collect_trajectory", self._collect_trajectory)
        graph.add_node("evaluate", self._evaluate)
        graph.add_node("persist", self._persist)
        graph.add_edge(START, "load_benchmark")
        graph.add_edge("load_benchmark", "setup_environment")
        graph.add_edge("setup_environment", "run_agent")
        graph.add_edge("run_agent", "collect_trajectory")
        graph.add_edge("collect_trajectory", "evaluate")
        graph.add_edge("evaluate", "persist")
        graph.add_edge("persist", END)
        return graph.compile()

    # benchmarkを検証して読み込む
    def _load_benchmark(self, state: EvaluationState) -> EvaluationState:
        with self._telemetry.tracer.start_as_current_span("load_benchmark"):
            benchmark = load_benchmark(state["benchmark_path"], "schemas/benchmark.schema.json")
            state["collector"].record("benchmark_loaded", {"benchmark_id": benchmark.id})
            return {"benchmark": benchmark}

    # 実行レコードを開始する
    def _setup_environment(self, state: EvaluationState) -> EvaluationState:
        with self._telemetry.tracer.start_as_current_span("setup_environment"):
            benchmark = state["benchmark"]
            run = self._repository.create_run(
                benchmark.id,
                self._settings.engine.agent_name,
                self._settings.model.provider,
                self._settings.model.model,
                architecture={"framework": "langgraph", "pattern": "linear-evaluation"},
                run_config=self._settings.model_dump(mode="json"),
            )
            state["collector"].record("environment_ready", {"dry_run": self._settings.engine.dry_run})
            return {"run_id": run.id}

    # モデル実行を記録する
    def _run_agent(self, state: EvaluationState) -> EvaluationState:
        with self._telemetry.tracer.start_as_current_span("run_agent"):
            collector = state["collector"]
            collector.record("user_prompt", {"content": state["benchmark"].task.prompt}, actor="user")
        try:
            result = self._agent.run(state["benchmark"], collector)
            return {"final_state": result.final_state, "failure_category": result.failure_category}
        except OpenRouterError as error:
            category = _map_openrouter_error_category(error)
            event_type = f"{category}_error"
            collector.record(
                event_type,
                {
                    "message": str(error),
                    "source": "openrouter",
                    "status_code": error.status_code,
                    "retry_count": error.retry_count,
                    "retry_delays_seconds": error.retry_delays_seconds,
                },
                error={"type": type(error).__name__, "message": str(error)},
            )
            return {
                "final_state": {"success": False, "error": str(error), "dry_run": False},
                "failure_category": category,
            }
        except Exception as error:
            collector.record(
                "model_error",
                {"message": str(error)},
                error={"type": type(error).__name__, "message": str(error)},
            )
            return {
                "final_state": {"success": False, "error": str(error), "dry_run": False},
                "failure_category": "model",
            }

    # 軌跡収集の完了を記録する
    def _collect_trajectory(self, state: EvaluationState) -> EvaluationState:
        with self._telemetry.tracer.start_as_current_span("collect_trajectory"):
            state["collector"].record("trajectory_collected", {"event_count": len(state["collector"].events())})
            return {}

    # 評価指標を計算する
    def _evaluate(self, state: EvaluationState) -> EvaluationState:
        with self._telemetry.tracer.start_as_current_span("evaluate"):
            elapsed_ms = (perf_counter() - state["started_at"]) * 1000
            metrics = calculate_metrics(state["collector"].events(), state["final_state"], elapsed_ms)
            state["collector"].record("evaluation_completed", {"metric_count": len(metrics)})
            return {"metrics": metrics, "elapsed_ms": elapsed_ms}

    # 実行結果をDBへ保存する
    def _persist(self, state: EvaluationState) -> EvaluationState:
        with self._telemetry.tracer.start_as_current_span("persist"):
            collector = state["collector"]
            collector.record("persistence_requested", {"event_count": len(collector.events())})
            for event in collector.events():
                self._repository.add_event(
                    state["run_id"], event.sequence, event.event_type, event.payload,
                    event.previous_state, event.next_state, event.error, event.actor,
                    event.trace_id, event.span_id,
                )
            for metric in state["metrics"]:
                self._repository.add_metric(
                    state["run_id"], metric.category, metric.name, metric.value,
                    metric.unit, metric.dimensions,
                )
            success = bool(state["final_state"].get("success"))
            evaluation_status = "simulated" if state["final_state"].get("dry_run") else "passed" if success else "failed"
            self._repository.add_evaluation(
                state["run_id"], "rule-based", "0.1", evaluation_status,
                1.0 if success else 0.0,
                summary={"dry_run": self._settings.engine.dry_run},
                findings=[event.error for event in collector.events() if event.error],
            )
            self._repository.finish_run(
                state["run_id"], "completed" if success else "failed", state["final_state"], state["failure_category"],
            )
            self._repository.session.commit()
            return {}


# OpenRouter例外を分類する
def _map_openrouter_error_category(error: OpenRouterError) -> str:
    category_map = {
        OpenRouterTimeoutError: "timeout",
        OpenRouterRateLimitError: "rate_limit",
        OpenRouterAuthenticationError: "auth",
        OpenRouterPermissionError: "permission",
        OpenRouterBadRequestError: "bad_request",
        OpenRouterInputLimitError: "input_limit",
        OpenRouterOutputLimitError: "output_limit",
        OpenRouterNotFoundError: "not_found",
        OpenRouterServerError: "server_error",
        OpenRouterServiceUnavailableError: "service_unavailable",
        OpenRouterConnectionError: "connection",
        OpenRouterStreamDisconnectedError: "stream_disconnected",
        OpenRouterInvalidFormatError: "invalid_format",
        OpenRouterEmptyResponseError: "empty_response",
        OpenRouterSafetyFilterError: "safety_filter",
        OpenRouterContentFilterError: "content_filter",
        OpenRouterToolCallError: "tool_call",
        OpenRouterStructuredOutputError: "structured_output",
        OpenRouterCostLimitError: "cost_limit",
        OpenRouterRetryLimitError: "retry_limit",
        OpenRouterIdempotencyError: "idempotency",
    }
    return category_map.get(type(error), "openrouter")
