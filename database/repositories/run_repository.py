"""評価実行の永続化操作を提供する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from database.models import AgentTarget, Artifact, Evaluation, Event, Metric, Run, RunAgentExecution


# 秘密情報を含む設定を拒否する
def reject_secret_configuration(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(word in key.casefold() for word in ("api_key", "token", "secret", "password")):
                raise ValueError("Agent接続先へ秘密情報を保存できません")
            reject_secret_configuration(nested)
    if isinstance(value, list):
        for nested in value:
            reject_secret_configuration(nested)


# 実行履歴をDBへ保存する
class RunRepository:
    # セッションを受け取る
    def __init__(self, session: Session) -> None:
        self.session = session

    # 実行を開始状態で保存する
    def create_run(
        self,
        benchmark_id: str,
        agent_name: str,
        provider: str | None = None,
        model: str | None = None,
        architecture: dict[str, Any] | None = None,
        run_config: dict[str, Any] | None = None,
    ) -> Run:
        run = Run(
            benchmark_id=benchmark_id,
            agent_name=agent_name,
            provider=provider,
            model=model,
            architecture=architecture or {},
            run_config=run_config or {},
        )
        self.session.add(run)
        self.session.flush()
        return run

    # Agent接続先を登録する
    def create_agent_target(
        self,
        name: str,
        adapter_type: str,
        configuration: dict[str, Any] | None = None,
        capabilities: dict[str, Any] | None = None,
        version: str | None = None,
    ) -> AgentTarget:
        reject_secret_configuration(configuration or {})
        target = AgentTarget(
            name=name,
            adapter_type=adapter_type,
            configuration=configuration or {},
            capabilities=capabilities or {},
            version=version,
        )
        self.session.add(target)
        self.session.flush()
        return target

    # Agent実行の開始情報を保存する
    def create_agent_execution(
        self,
        run_id: UUID,
        adapter_type: str,
        target_id: UUID | None = None,
        target_snapshot: dict[str, Any] | None = None,
    ) -> RunAgentExecution:
        execution = RunAgentExecution(
            run_id=run_id,
            target_id=target_id,
            adapter_type=adapter_type,
            target_snapshot=target_snapshot or {},
        )
        self.session.add(execution)
        self.session.flush()
        return execution

    # Agent実行の終了情報を保存する
    def finish_agent_execution(
        self,
        execution_id: UUID,
        status: str,
        exit_code: int | None = None,
        error: dict[str, Any] | None = None,
    ) -> RunAgentExecution:
        execution = self.session.get(RunAgentExecution, execution_id)
        if execution is None:
            raise ValueError(f"agent execution not found: {execution_id}")
        execution.status = status
        execution.exit_code = exit_code
        execution.error = error
        execution.finished_at = datetime.now(timezone.utc)
        self.session.flush()
        return execution

    # 成果物の参照情報を保存する
    def add_artifact(
        self,
        run_id: UUID,
        kind: str,
        uri: str,
        execution_id: UUID | None = None,
        sha256: str | None = None,
        size_bytes: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        artifact = Artifact(
            run_id=run_id,
            execution_id=execution_id,
            kind=kind,
            uri=uri,
            sha256=sha256,
            size_bytes=size_bytes,
            metadata_json=metadata or {},
        )
        self.session.add(artifact)
        self.session.flush()
        return artifact

    # 軌跡イベントを順序付きで保存する
    def add_event(
        self,
        run_id: UUID,
        sequence: int,
        event_type: str,
        payload: dict[str, Any],
        previous_state: dict[str, Any] | None = None,
        next_state: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        actor: str = "agent",
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> Event:
        event = Event(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            actor=actor,
            payload=payload,
            previous_state=previous_state,
            next_state=next_state,
            error=error,
            trace_id=trace_id,
            span_id=span_id,
        )
        self.session.add(event)
        self.session.flush()
        return event

    # 指標値を独立して保存する
    def add_metric(
        self,
        run_id: UUID,
        category: str,
        name: str,
        value: float,
        unit: str | None = None,
        dimensions: dict[str, Any] | None = None,
    ) -> Metric:
        metric = Metric(
            run_id=run_id,
            category=category,
            name=name,
            value=value,
            unit=unit,
            dimensions=dimensions or {},
        )
        self.session.add(metric)
        self.session.flush()
        return metric

    # 評価器の判定を保存する
    def add_evaluation(
        self,
        run_id: UUID,
        evaluator_name: str,
        evaluator_version: str,
        status: str,
        score: float | None = None,
        summary: dict[str, Any] | None = None,
        findings: list[dict[str, Any]] | None = None,
    ) -> Evaluation:
        evaluation = Evaluation(
            run_id=run_id,
            evaluator_name=evaluator_name,
            evaluator_version=evaluator_version,
            status=status,
            score=score,
            summary=summary or {},
            findings=findings or [],
        )
        self.session.add(evaluation)
        self.session.flush()
        return evaluation

    # 実行を終了状態で保存する
    def finish_run(
        self,
        run_id: UUID,
        status: str,
        final_state: dict[str, Any],
        failure_category: str | None = None,
        llm_cost_usd: float | None = None,
    ) -> Run:
        run = self.session.get(Run, run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        run.status = status
        run.final_state = final_state
        run.failure_category = failure_category
        run.llm_cost_usd = llm_cost_usd
        run.finished_at = datetime.now(timezone.utc)
        self.session.flush()
        return run

    # 実行と関連記録を取得する
    def get_run(self, run_id: UUID) -> Run | None:
        statement = (
            select(Run)
            .where(Run.id == run_id)
            .options(
                selectinload(Run.events),
                selectinload(Run.metrics),
                selectinload(Run.evaluations),
                selectinload(Run.agent_executions),
                selectinload(Run.artifacts),
            )
        )
        return self.session.scalar(statement)

    # 新しい順で実行一覧を取得する
    def list_runs(self, limit: int = 100, offset: int = 0) -> list[Run]:
        page_limit = min(max(limit, 1), 100)
        page_offset = max(offset, 0)
        statement = select(Run).order_by(desc(Run.started_at)).limit(page_limit).offset(page_offset)
        return list(self.session.scalars(statement))

    # 実行履歴の総数を返す
    def count_runs(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Run)) or 0

    # 詳細画面向けの値を取得する
    def get_run_details(self, run_id: UUID, event_limit: int = 20, event_offset: int = 0) -> dict[str, Any]:
        statement = (
            select(Run)
            .where(Run.id == run_id)
            .options(
                selectinload(Run.metrics),
                selectinload(Run.evaluations),
                selectinload(Run.agent_executions),
                selectinload(Run.artifacts),
            )
        )
        run = self.session.scalar(statement)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        page_limit = min(max(event_limit, 1), 100)
        page_offset = max(event_offset, 0)
        return {
            "run_id": str(run.id),
            "benchmark_id": run.benchmark_id,
            "status": run.status,
            "agent_name": run.agent_name,
            "provider": run.provider,
            "model": run.model,
            "architecture": run.architecture,
            "run_config": run.run_config,
            "final_state": run.final_state,
            "failure_category": run.failure_category,
            "llm_cost_usd": float(run.llm_cost_usd) if run.llm_cost_usd is not None else None,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "events": [self.event_output(event) for event in self.list_events(run_id, page_limit, page_offset)],
            "event_total": self.count_events(run_id),
            "event_offset": page_offset,
            "event_limit": page_limit,
            "metrics": [
            {
                "category": metric.category,
                "name": metric.name,
                "value": float(metric.value),
                "unit": metric.unit,
                "dimensions": metric.dimensions,
            }
            for metric in run.metrics
            ],
            "evaluations": [
            {
                "evaluator_name": evaluation.evaluator_name,
                "evaluator_version": evaluation.evaluator_version,
                "status": evaluation.status,
                "score": float(evaluation.score) if evaluation.score is not None else None,
                "summary": evaluation.summary,
                "findings": evaluation.findings,
            }
            for evaluation in run.evaluations
            ],
            "agent_executions": [self.agent_execution_output(execution) for execution in run.agent_executions],
            "artifacts": [self.artifact_output(artifact) for artifact in run.artifacts],
        }

    # 実行イベントをページ単位で取得する
    def list_events(self, run_id: UUID, limit: int = 20, offset: int = 0) -> list[Event]:
        page_limit = min(max(limit, 1), 100)
        page_offset = max(offset, 0)
        statement = (
            select(Event)
            .where(Event.run_id == run_id)
            .order_by(Event.sequence)
            .limit(page_limit)
            .offset(page_offset)
        )
        return list(self.session.scalars(statement))

    # 実行イベントの総数を返す
    def count_events(self, run_id: UUID) -> int:
        return self.session.scalar(select(func.count()).select_from(Event).where(Event.run_id == run_id)) or 0

    # イベントを返却形式へ変換する
    def event_output(self, event: Event) -> dict[str, Any]:
        return {
            "sequence": event.sequence,
            "event_type": event.event_type,
            "actor": event.actor,
            "occurred_at": event.occurred_at.isoformat(),
            "payload": event.payload,
            "previous_state": event.previous_state,
            "next_state": event.next_state,
            "error": event.error,
            "trace_id": event.trace_id,
            "span_id": event.span_id,
        }

    # Agent実行を返却形式へ変換する
    def agent_execution_output(self, execution: RunAgentExecution) -> dict[str, Any]:
        return {
            "id": str(execution.id),
            "target_id": str(execution.target_id) if execution.target_id else None,
            "adapter_type": execution.adapter_type,
            "target_snapshot": execution.target_snapshot,
            "status": execution.status,
            "exit_code": execution.exit_code,
            "error": execution.error,
            "started_at": execution.started_at.isoformat(),
            "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        }

    # 成果物を返却形式へ変換する
    def artifact_output(self, artifact: Artifact) -> dict[str, Any]:
        return {
            "id": str(artifact.id),
            "execution_id": str(artifact.execution_id) if artifact.execution_id else None,
            "kind": artifact.kind,
            "uri": artifact.uri,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "metadata": artifact.metadata_json,
        }

    # 実行履歴を再構成する
    def reconstruct_history(self, run_id: UUID) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        return {
            "run_id": str(run.id),
            "benchmark_id": run.benchmark_id,
            "status": run.status,
            "agent_name": run.agent_name,
            "provider": run.provider,
            "model": run.model,
            "architecture": run.architecture,
            "run_config": run.run_config,
            "final_state": run.final_state,
            "failure_category": run.failure_category,
            "llm_cost_usd": float(run.llm_cost_usd) if run.llm_cost_usd is not None else None,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "events": [
                self.event_output(event)
                for event in run.events
            ],
            "agent_executions": [self.agent_execution_output(execution) for execution in run.agent_executions],
            "artifacts": [self.artifact_output(artifact) for artifact in run.artifacts],
        }
