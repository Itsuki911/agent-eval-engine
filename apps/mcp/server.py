"""評価エンジン用MCP Serverを定義する。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from mcp.server import MCPServer
from sqlalchemy.orm import Session

from agent_eval.config import Phase3Settings, load_settings
from agent_eval.real_agent_adapter import import_agent_transcript, resolve_agent_transcript_path
from agent_eval.workflow import EvaluationService
from apps.api.main import agent_trace_root, evaluation_output, resolve_benchmark, settings_path
from database.migration import upgrade_database
from database.repositories import RunRepository
from database.session import create_session_factory


SessionFactory = Callable[[], Session]
SettingsLoader = Callable[[Path], Phase3Settings]


# MCP出力の秘密情報を伏せる
def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(word in key.casefold() for word in ("api_key", "token", "secret", "password")) else redact_secrets(nested)
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(nested) for nested in value]
    return value


# MCPツールの処理を提供する
class EvaluationMCPService:
    # DBと設定読込を受け取る
    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        load_phase_settings: SettingsLoader = load_settings,
        migrate_on_first_use: bool = True,
    ) -> None:
        self._session_factory = session_factory or create_session_factory()
        self._load_phase_settings = load_phase_settings
        self._migrate_on_first_use = migrate_on_first_use
        self._migration_checked = False

    # 既存migrationの適用を確認する
    def _ensure_migration(self) -> None:
        if self._migrate_on_first_use and not self._migration_checked:
            upgrade_database()
        self._migration_checked = True

    # live実行の許可状態を確認する
    def _settings(self) -> Phase3Settings:
        settings = self._load_phase_settings(settings_path())
        if not settings.engine.dry_run and os.environ.get("AGENT_EVAL_MCP_ALLOW_LIVE") != "1":
            raise PermissionError("live LLM 実行は AGENT_EVAL_MCP_ALLOW_LIVE=1 が必要です")
        return settings

    # benchmarkを評価して保存する
    def run_benchmark(self, benchmark_id: str, source: str = "sample") -> dict[str, Any]:
        if source not in ("sample", "user-created"):
            raise ValueError("source は sample または user-created を指定してください")
        self._ensure_migration()
        benchmark_path = resolve_benchmark(benchmark_id, source)
        with self._session_factory() as session:
            result = EvaluationService(self._settings(), session).run(benchmark_path)
        return redact_secrets(evaluation_output(result))

    # Agent評価の互換入口を提供する
    def evaluate_agent(self, benchmark_id: str, source: str = "sample") -> dict[str, Any]:
        return self.run_benchmark(benchmark_id, source)

    # 指定runの全記録を取得する
    def get_run(self, run_id: str) -> dict[str, Any]:
        self._ensure_migration()
        with self._session_factory() as session:
            try:
                details = RunRepository(session).get_run_details(UUID(run_id), event_limit=100, event_offset=0)
            except ValueError as error:
                raise ValueError("run が見つかりません") from error
        return redact_secrets(details)

    # 指定runの時系列traceを取得する
    def get_trace(self, run_id: str, limit: int = 100) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("limit は 1 から 100 を指定してください")
        self._ensure_migration()
        parsed_run_id = UUID(run_id)
        with self._session_factory() as session:
            repository = RunRepository(session)
            if repository.get_run(parsed_run_id) is None:
                raise ValueError("run が見つかりません")
            result = {
                "run_id": run_id,
                "events": [repository.event_output(event) for event in repository.list_events(parsed_run_id, limit)],
                "total": repository.count_events(parsed_run_id),
            }
        return redact_secrets(result)

    # 指定runのエラーイベントを取得する
    def get_errors(self, run_id: str) -> dict[str, Any]:
        trace = self.get_trace(run_id)
        return {"run_id": run_id, "errors": [event for event in trace["events"] if event["error"] is not None]}

    # 2runの評価指標を比較する
    def compare_runs(self, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        self._ensure_migration()
        with self._session_factory() as session:
            repository = RunRepository(session)
            try:
                left = repository.get_run_details(UUID(left_run_id), event_limit=1)
                right = repository.get_run_details(UUID(right_run_id), event_limit=1)
            except ValueError as error:
                raise ValueError("比較対象のrunが見つかりません") from error
        left_metrics = {f"{item['category']}.{item['name']}": float(item["value"]) for item in left["metrics"]}
        right_metrics = {f"{item['category']}.{item['name']}": float(item["value"]) for item in right["metrics"]}
        return {
            "left_run_id": left_run_id,
            "right_run_id": right_run_id,
            "metrics": [
                {"name": name, "left": left_metrics.get(name), "right": right_metrics.get(name), "difference": right_metrics.get(name, 0) - left_metrics.get(name, 0)}
                for name in sorted(set(left_metrics) | set(right_metrics))
            ],
        }

    # 小規模な回帰評価を実行する
    def run_regression(self, benchmark_ids: list[str], source: str = "sample") -> dict[str, Any]:
        if not 1 <= len(benchmark_ids) <= 10:
            raise ValueError("benchmark_ids は 1件から10件を指定してください")
        results = [self.run_benchmark(benchmark_id, source) for benchmark_id in benchmark_ids]
        return {
            "source": source,
            "total": len(results),
            "passed": sum(result["status"] in ("completed", "simulated") for result in results),
            "failed": sum(result["status"] == "failed" for result in results),
            "runs": results,
        }

    # 外部Agentの標準記録を取り込む
    def import_agent_trace(self, transcript_file: str) -> dict[str, Any]:
        self._ensure_migration()
        transcript_path = resolve_agent_transcript_path(agent_trace_root(), transcript_file)
        with self._session_factory() as session:
            result = import_agent_transcript(RunRepository(session), transcript_path)
        return redact_secrets(result)


# MCP Serverを生成する
def create_server(service: EvaluationMCPService | None = None) -> MCPServer:
    current_service = service or EvaluationMCPService()
    server = MCPServer(
        "agent-eval-engine",
        instructions="評価はrun_benchmarkで開始します。get_run、get_trace、get_errorsは読み取り専用です。live LLMは明示的な環境変数許可が必要です。",
    )

    # benchmark評価ツールを公開する
    @server.tool()
    def run_benchmark(benchmark_id: str, source: str = "sample") -> dict[str, Any]:
        """指定benchmarkを評価して保存する。"""
        return current_service.run_benchmark(benchmark_id, source)

    # Agent評価互換ツールを公開する
    @server.tool()
    def evaluate_agent(benchmark_id: str, source: str = "sample") -> dict[str, Any]:
        """Agent評価の互換入口。"""
        return current_service.evaluate_agent(benchmark_id, source)

    # run詳細取得ツールを公開する
    @server.tool()
    def get_run(run_id: str) -> dict[str, Any]:
        """指定runの保存済み詳細を取得する。"""
        return current_service.get_run(run_id)

    # trace取得ツールを公開する
    @server.tool()
    def get_trace(run_id: str, limit: int = 100) -> dict[str, Any]:
        """指定runの時系列イベントを取得する。"""
        return current_service.get_trace(run_id, limit)

    # エラー取得ツールを公開する
    @server.tool()
    def get_errors(run_id: str) -> dict[str, Any]:
        """指定runのエラーイベントを取得する。"""
        return current_service.get_errors(run_id)

    # run比較ツールを公開する
    @server.tool()
    def compare_runs(left_run_id: str, right_run_id: str) -> dict[str, Any]:
        """2runの評価指標を比較する。"""
        return current_service.compare_runs(left_run_id, right_run_id)

    # 回帰実行ツールを公開する
    @server.tool()
    def run_regression(benchmark_ids: list[str], source: str = "sample") -> dict[str, Any]:
        """最大10件のbenchmarkを回帰評価する。"""
        return current_service.run_regression(benchmark_ids, source)

    # 外部Agent記録の取込ツールを公開する
    @server.tool()
    def import_agent_trace(transcript_file: str) -> dict[str, Any]:
        """許可フォルダの外部Agent記録を保存する。"""
        return current_service.import_agent_trace(transcript_file)

    return server


mcp = create_server()
