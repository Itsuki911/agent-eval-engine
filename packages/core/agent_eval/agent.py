"""モデル実行を評価イベントへ変換する。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from agent_eval.benchmark import BenchmarkDefinition
from agent_eval.config import Phase3Settings
from agent_eval.events import EventCollector
from agent_eval.openrouter import (
    OpenRouterClient,
    OpenRouterStructuredOutputError,
    parse_json_response,
)


# エージェント応答を表す
class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    final_answer: str


# 実行結果を表す
@dataclass(frozen=True)
class AgentResult:
    final_state: dict[str, object]
    failure_category: str | None = None


# エージェント実行の契約を表す
class AgentRunner(Protocol):
    # benchmarkを実行して結果を返す
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult: ...


# 再現可能な模擬実行を行う
class DryRunAgent:
    # 設定を受け取る
    def __init__(self, settings: Phase3Settings) -> None:
        self._settings = settings

    # 模擬応答をイベントへ記録する
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        collector.record(
            "llm_call",
            {
                "provider": self._settings.model.provider,
                "model": self._settings.model.model,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0,
                "duration_ms": 0,
                "dry_run": True,
            },
            actor="model",
        )
        final_answer = f"dry-run: {benchmark.id}"
        collector.record(
            "model_response",
            {"content": final_answer, "dry_run": True},
            actor="model",
        )
        return AgentResult({"success": True, "answer": final_answer, "dry_run": True})


# OpenRouterモデルを実行する
class OpenRouterAgent:
    # モデル接続を初期化する
    def __init__(self, settings: Phase3Settings) -> None:
        self._settings = settings
        self._client = OpenRouterClient(settings.model)

    # モデル応答を検証して返す
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        response = self._client.complete(_system_prompt(), benchmark.task.prompt)
        collector.record(
            "llm_call",
            {
                "provider": self._settings.model.provider,
                "model": self._settings.model.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost_usd": response.estimated_cost_usd,
                "duration_ms": response.duration_ms,
                "dry_run": False,
            },
            actor="model",
        )
        json_data = parse_json_response(response.content)
        try:
            parsed = AgentResponse.model_validate(json_data)
        except ValidationError as error:
            if self._settings.model.validate_structured_output:
                raise OpenRouterStructuredOutputError(f"構造化出力検証に失敗しました: {error}") from error
            raise
        collector.record("model_response", {"content": response.content}, actor="model")
        return AgentResult({"success": parsed.success, "answer": parsed.final_answer, "dry_run": False})


# 設定に応じた実行器を作る
def build_agent(settings: Phase3Settings) -> AgentRunner:
    return DryRunAgent(settings) if settings.engine.dry_run else OpenRouterAgent(settings)


# 構造化応答の指示を作る
def _system_prompt() -> str:
    return (
        "Return only JSON with success (boolean) and final_answer (string). "
        "Do not claim tool execution because this evaluator does not execute tools."
    )
