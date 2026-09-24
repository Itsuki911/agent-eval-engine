"""Phase 3ワークフローとDB保存を確認する。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from agent_eval.agent import AgentResult
from agent_eval.benchmark import BenchmarkDefinition
from agent_eval.config import load_settings
from agent_eval.events import EventCollector
from agent_eval.openrouter import OpenRouterTimeoutError
from agent_eval.workflow import EvaluationService
from database.repositories import RunRepository
from database.session import create_db_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# テストDBへマイグレーションする
@pytest.fixture(scope="session")
def db_engine():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL を設定してください")
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")
    if previous_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_url
    engine = create_db_engine(test_url)
    yield engine
    engine.dispose()


# テスト用セッションを作る
@pytest.fixture
def session(db_engine):
    with Session(db_engine) as current_session:
        yield current_session
        current_session.rollback()
    with db_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE evaluations, metrics, events, runs RESTART IDENTITY CASCADE"))


# テスト用の失敗実行器を表す
class FailingAgent:
    # 実行失敗を再現する
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        raise RuntimeError("simulated model failure")


# テスト用のタイムアウト実行器を表す
class TimeoutAgent:
    # OpenRouterタイムアウトを再現する
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        raise OpenRouterTimeoutError("OpenRouterの応答がタイムアウトしました")


# 出力を抑えた設定を作る
def _test_settings():
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    telemetry = settings.telemetry.model_copy(update={"exporter": "none"})
    return settings.model_copy(update={"telemetry": telemetry})


# dry-runの全処理を確認する
def test_dry_run_persists_evaluation_history(session: Session) -> None:
    service = EvaluationService(_test_settings(), session)

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)

    assert result.status == "simulated"
    assert result.event_count >= 6
    assert history["final_state"]["dry_run"] is True
    assert [event["sequence"] for event in history["events"]] == list(range(result.event_count))
    stored_run = RunRepository(session).get_run(result.run_id)
    assert stored_run.evaluations[0].status == "simulated"
    assert any(metric.name == "end_to_end_latency_ms" for metric in stored_run.metrics)
    print(
        "dry-run保存: "
        f"status={result.status}, events={result.event_count}, "
        f"metrics={len(stored_run.metrics)}, "
        f"evaluation={stored_run.evaluations[0].status}"
    )


# モデル失敗を保存できる
def test_model_failure_is_persisted(session: Session) -> None:
    service = EvaluationService(_test_settings(), session, FailingAgent())

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)

    assert result.status == "failed"
    assert history["failure_category"] == "model"
    assert any(event["event_type"] == "model_error" for event in history["events"])
    print(
        "失敗保存: "
        f"status={result.status}, failure_category={history['failure_category']}, "
        "event_type=model_error"
    )


# タイムアウトをイベントへ保存できる
def test_timeout_is_persisted(session: Session) -> None:
    service = EvaluationService(_test_settings(), session, TimeoutAgent())

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)

    assert result.status == "failed"
    assert history["failure_category"] == "timeout"
    assert any(event["event_type"] == "timeout_error" for event in history["events"])
    print(
        "タイムアウト保存: "
        f"status={result.status}, failure_category={history['failure_category']}, "
        "event_type=timeout_error"
    )
