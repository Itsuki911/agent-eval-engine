"""評価エンジンをHTTPで公開する。"""

from __future__ import annotations

import os
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agent_eval.config import Phase3Settings, load_settings
from agent_eval.workflow import EvaluationResult, EvaluationService
from apps.api.schemas import CreateEventRequest, CreateRunRequest, EvaluateRequest, FinishRunRequest, ImportTranscriptRequest
from database.migration import upgrade_database
from database.repositories import RunRepository
from database.repositories.run_repository import reject_secret_configuration
from database.session import create_session_factory
from agent_eval.real_agent_adapter import TranscriptError, import_agent_transcript, resolve_agent_transcript_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SessionFactory = Callable[[], Session]
SettingsLoader = Callable[[Path], Phase3Settings]


# API設定ファイルの場所を返す
def settings_path() -> Path:
    configured = os.environ.get("AGENT_EVAL_CONFIG")
    return Path(configured).expanduser().resolve() if configured else PROJECT_ROOT / "configs" / "phase3-local.yaml"


# 自作datasetの保存先を返す
def user_dataset_root() -> Path:
    configured = os.environ.get("AGENT_EVAL_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve() / "datasets" / "user"
    return PROJECT_ROOT / "benchmarks" / "user"


# Agent記録の許可保存先を返す
def agent_trace_root() -> Path:
    configured = os.environ.get("AGENT_EVAL_AGENT_TRACE_DIR")
    return Path(configured).expanduser().resolve() if configured else PROJECT_ROOT / "local-data" / "agent-traces"


# 指定IDのbenchmarkを安全に解決する
def resolve_benchmark(benchmark_id: str, source: str) -> Path:
    root = PROJECT_ROOT / "benchmarks" if source == "sample" else user_dataset_root()
    for family in ("generic", "coding"):
        candidate = (root / family / f"{benchmark_id}.yaml").resolve()
        family_root = (root / family).resolve()
        if candidate.is_relative_to(family_root) and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"benchmark not found: {benchmark_id}")


# 評価結果をAPI形式へ変換する
def evaluation_output(result: EvaluationResult) -> dict[str, Any]:
    return {
        "run_id": str(result.run_id),
        "status": result.status,
        "benchmark_id": result.benchmark_id,
        "final_state": result.final_state,
        "event_count": result.event_count,
        "llm_cost_usd": result.llm_cost_usd,
        "metrics": [metric.__dict__ for metric in result.metrics],
    }


# 実行一覧の表示値を作る
def run_summary(run: Any) -> dict[str, Any]:
    return {
        "run_id": str(run.id),
        "benchmark_id": run.benchmark_id,
        "status": run.status,
        "agent_name": run.agent_name,
        "provider": run.provider,
        "model": run.model,
        "llm_cost_usd": float(run.llm_cost_usd) if run.llm_cost_usd is not None else None,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


# 指標を比較用の辞書へ変換する
def metric_map(details: dict[str, Any]) -> dict[str, float]:
    return {
        f"{metric['category']}.{metric['name']}": float(metric["value"])
        for metric in details["metrics"]
    }


# APIアプリケーションを生成する
def create_app(
    session_factory: SessionFactory | None = None,
    load_phase_settings: SettingsLoader = load_settings,
    migrate_on_startup: bool = True,
) -> FastAPI:
    factory = session_factory or create_session_factory()

    # 起動時のDB準備を行う
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Generator[None, None, None]:
        if migrate_on_startup:
            upgrade_database()
        yield

    app = FastAPI(title="Agent Eval Engine API", version="0.6.0", lifespan=lifespan)

    # DBセッションをリクエスト単位で閉じる
    def get_session() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    # API稼働状態を返す
    @app.get("/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok"}

    # benchmark評価を実行する
    @app.post("/evaluate", status_code=status.HTTP_201_CREATED)
    def evaluate(request: EvaluateRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
        try:
            benchmark_path = resolve_benchmark(request.benchmark_id, request.source)
        except FileNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        result = EvaluationService(load_phase_settings(settings_path()), session).run(benchmark_path)
        return evaluation_output(result)

    # 外部Agentの実行を登録する
    @app.post("/runs", status_code=status.HTTP_201_CREATED)
    def create_run(request: CreateRunRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
        try:
            reject_secret_configuration(request.architecture)
            reject_secret_configuration(request.run_config)
            run = RunRepository(session).create_run(**request.model_dump())
            session.commit()
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        return run_summary(run)

    # 外部Agentのイベントを追加する
    @app.post("/runs/{run_id}/events", status_code=status.HTTP_201_CREATED)
    def create_event(run_id: UUID, request: CreateEventRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
        repository = RunRepository(session)
        if repository.get_run(run_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
        try:
            reject_secret_configuration(request.payload)
            reject_secret_configuration(request.previous_state)
            reject_secret_configuration(request.next_state)
            event = repository.add_event(run_id, **request.model_dump())
            session.commit()
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="event sequence already exists") from error
        return repository.event_output(event)

    # 外部Agentの実行を終了する
    @app.post("/runs/{run_id}/finish")
    def finish_run(run_id: UUID, request: FinishRunRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
        try:
            reject_secret_configuration(request.final_state)
            run = RunRepository(session).finish_run(run_id, **request.model_dump())
            session.commit()
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        return run_summary(run)

    # 外部Agentの標準記録を取り込む
    @app.post("/agent-transcripts/import", status_code=status.HTTP_201_CREATED)
    def import_transcript(request: ImportTranscriptRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
        try:
            transcript_path = resolve_agent_transcript_path(agent_trace_root(), request.transcript_file)
            return import_agent_transcript(RunRepository(session), transcript_path)
        except TranscriptError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    # 実行履歴の一覧を返す
    @app.get("/runs")
    def list_runs(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        repository = RunRepository(session)
        return {
            "runs": [run_summary(run) for run in repository.list_runs(limit, offset)],
            "total": repository.count_runs(),
            "limit": limit,
            "offset": offset,
        }

    # 指定実行の詳細を返す
    @app.get("/runs/{run_id}")
    def get_run(
        run_id: UUID,
        event_limit: int = Query(default=20, ge=1, le=100),
        event_offset: int = Query(default=0, ge=0),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        try:
            return RunRepository(session).get_run_details(run_id, event_limit, event_offset)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found") from error

    # 指定実行のtraceイベントを返す
    @app.get("/runs/{run_id}/trace")
    def get_trace(
        run_id: UUID,
        limit: int = Query(default=100, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        repository = RunRepository(session)
        if repository.get_run(run_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
        return {
            "run_id": str(run_id),
            "events": [repository.event_output(event) for event in repository.list_events(run_id, limit, offset)],
            "total": repository.count_events(run_id),
            "limit": limit,
            "offset": offset,
        }

    # 指定実行の評価指標を返す
    @app.get("/runs/{run_id}/metrics")
    def get_metrics(run_id: UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
        try:
            details = RunRepository(session).get_run_details(run_id, event_limit=1)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found") from error
        return {"run_id": str(run_id), "metrics": details["metrics"], "evaluations": details["evaluations"]}

    # 2実行の評価指標を比較する
    @app.get("/compare")
    def compare_runs(
        left_run_id: UUID,
        right_run_id: UUID,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        repository = RunRepository(session)
        try:
            left = metric_map(repository.get_run_details(left_run_id, event_limit=1))
            right = metric_map(repository.get_run_details(right_run_id, event_limit=1))
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found") from error
        keys = sorted(set(left) | set(right))
        return {
            "left_run_id": str(left_run_id),
            "right_run_id": str(right_run_id),
            "metrics": [
                {"name": key, "left": left.get(key), "right": right.get(key), "difference": right.get(key, 0) - left.get(key, 0)}
                for key in keys
            ],
        }

    return app


app = create_app()
