"""評価実行の永続化操作を提供する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Evaluation, Event, Metric, Run


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
    ) -> Run:
        run = self.get_run(run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        run.status = status
        run.final_state = final_state
        run.failure_category = failure_category
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
            )
        )
        return self.session.scalar(statement)

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
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "events": [
                {
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
                for event in run.events
            ],
        }
