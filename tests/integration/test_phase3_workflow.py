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
from agent_eval.openrouter import (
    OpenRouterAuthenticationError,
    OpenRouterConnectionError,
    OpenRouterCostLimitError,
    OpenRouterInputLimitError,
    OpenRouterRateLimitError,
    OpenRouterRetryLimitError,
    OpenRouterSafetyFilterError,
    OpenRouterStructuredOutputError,
    OpenRouterTimeoutError,
)
from agent_eval.workflow import EvaluationService
from database.repositories import RunRepository
from database.session import create_db_engine
from tests.output import print_test_result


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
        raise OpenRouterTimeoutError(
            "OpenRouterの応答がタイムアウトしました",
            status_code=408,
            retry_count=1,
            retry_delays_seconds=[1.0],
        )


# テスト用のレート制限実行器を表す
class RateLimitedAgent:
    # OpenRouterレート制限を再現する
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        raise OpenRouterRateLimitError(
            "OpenRouterのレート制限に達しました",
            status_code=429,
            retry_count=1,
            retry_delays_seconds=[2.0],
        )


# テスト用のOpenRouter失敗実行器を表す
class OpenRouterFailingAgent:
    # 指定された例外を再現する
    def __init__(self, error: Exception) -> None:
        self._error = error

    # OpenRouter例外を送出する
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        raise self._error


# テスト用の課金済み実行器を表す
class ChargedAgent:
    # API料金を含む応答を再現する
    def run(self, benchmark: BenchmarkDefinition, collector: EventCollector) -> AgentResult:
        collector.record(
            "llm_call",
            {
                "provider": "openrouter",
                "model": "test-paid-model",
                "input_tokens": 100,
                "output_tokens": 50,
                "estimated_cost_usd": 0.0125,
                "duration_ms": 10,
                "dry_run": False,
            },
            actor="model",
        )
        return AgentResult({"success": True, "answer": "paid response", "dry_run": False})


# 出力を抑えた設定を作る
def _test_settings():
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    telemetry = settings.telemetry.model_copy(update={"exporter": "none"})
    return settings.model_copy(update={"telemetry": telemetry})


# live相当の設定を作る
def _live_like_settings():
    settings = _test_settings()
    engine = settings.engine.model_copy(update={"dry_run": False})
    return settings.model_copy(update={"engine": engine})


# dry-runの全処理を確認する
def test_dry_run_persists_evaluation_history(session: Session) -> None:
    service = EvaluationService(_test_settings(), session)

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)

    assert result.status == "simulated"
    assert result.event_count >= 6
    assert history["final_state"]["dry_run"] is True
    assert result.llm_cost_usd is None
    assert history["llm_cost_usd"] is None
    assert [event["sequence"] for event in history["events"]] == list(range(result.event_count))
    stored_run = RunRepository(session).get_run(result.run_id)
    assert stored_run.evaluations[0].status == "simulated"
    assert "llm_cost_usd" not in stored_run.evaluations[0].summary
    assert any(metric.name == "end_to_end_latency_ms" for metric in stored_run.metrics)
    print_test_result(
        "dry_run_persists_evaluation_history",
        "passed",
        status=result.status,
        event_count=result.event_count,
        metric_count=len(stored_run.metrics),
        evaluation_status=stored_run.evaluations[0].status,
        llm_cost_usd=None,
    )


# API LLM料金を実行単位で保存できる
def test_live_llm_cost_is_persisted(session: Session) -> None:
    service = EvaluationService(_live_like_settings(), session, ChargedAgent())

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)
    stored_run = RunRepository(session).get_run(result.run_id)
    evaluation = stored_run.evaluations[0]

    assert result.llm_cost_usd == 0.0125
    assert history["llm_cost_usd"] == 0.0125
    assert float(stored_run.llm_cost_usd) == 0.0125
    assert evaluation.summary["llm_cost_usd"] == 0.0125
    print_test_result(
        "live_llm_cost_is_persisted",
        "passed",
        llm_cost_usd=result.llm_cost_usd,
        stored_in=["runs", "evaluations.summary", "reconstructed_history"],
    )


# モデル失敗を保存できる
def test_model_failure_is_persisted(session: Session) -> None:
    service = EvaluationService(_test_settings(), session, FailingAgent())

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)

    assert result.status == "failed"
    assert history["failure_category"] == "model"
    assert any(event["event_type"] == "model_error" for event in history["events"])
    print_test_result(
        "model_failure_is_persisted",
        "passed",
        status=result.status,
        failure_category=history["failure_category"],
        event_type="model_error",
    )


# タイムアウトをイベントへ保存できる
def test_timeout_is_persisted(session: Session) -> None:
    service = EvaluationService(_test_settings(), session, TimeoutAgent())

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)
    stored_run = RunRepository(session).get_run(result.run_id)

    assert result.status == "failed"
    assert history["failure_category"] == "timeout"
    event = next(event for event in history["events"] if event["event_type"] == "timeout_error")
    assert event["payload"]["status_code"] == 408
    assert event["payload"]["retry_count"] == 1
    assert stored_run.evaluations[0].status == "failed"
    print_test_result(
        "timeout_is_persisted",
        "passed",
        status=result.status,
        failure_category=history["failure_category"],
        event_type="timeout_error",
        status_code=event["payload"]["status_code"],
        retry_count=event["payload"]["retry_count"],
    )


# レート制限をイベントへ保存できる
def test_rate_limit_is_persisted(session: Session) -> None:
    service = EvaluationService(_test_settings(), session, RateLimitedAgent())

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)
    stored_run = RunRepository(session).get_run(result.run_id)

    assert result.status == "failed"
    assert history["failure_category"] == "rate_limit"
    event = next(event for event in history["events"] if event["event_type"] == "rate_limit_error")
    assert event["payload"]["status_code"] == 429
    assert event["payload"]["retry_count"] == 1
    assert stored_run.evaluations[0].status == "failed"
    print_test_result(
        "rate_limit_is_persisted",
        "passed",
        status=result.status,
        failure_category=history["failure_category"],
        event_type="rate_limit_error",
        status_code=event["payload"]["status_code"],
        retry_count=event["payload"]["retry_count"],
    )


# 代表例外の永続化を確認する
@pytest.mark.parametrize(
    ("error", "category"),
    [
        (OpenRouterAuthenticationError("認証失敗"), "auth"),
        (OpenRouterInputLimitError("入力上限超過"), "input_limit"),
        (OpenRouterConnectionError("接続失敗"), "connection"),
        (OpenRouterSafetyFilterError("安全フィルタ拒否"), "safety_filter"),
        (OpenRouterStructuredOutputError("構造化出力不正"), "structured_output"),
        (OpenRouterCostLimitError("コスト上限超過"), "cost_limit"),
        (OpenRouterRetryLimitError("再試行上限"), "retry_limit"),
    ],
)
def test_openrouter_error_categories_are_persisted(
    session: Session, error: Exception, category: str
) -> None:
    service = EvaluationService(_test_settings(), session, OpenRouterFailingAgent(error))

    result = service.run(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
    history = RunRepository(session).reconstruct_history(result.run_id)
    stored_run = RunRepository(session).get_run(result.run_id)
    events = history["events"]

    assert result.status == "failed"
    assert history["failure_category"] == category
    assert any(event["event_type"] == f"{category}_error" for event in events)
    assert stored_run.evaluations[0].status == "failed"
    print_test_result(
        "openrouter_error_categories_are_persisted",
        "passed",
        status=result.status,
        failure_category=category,
        event_type=f"{category}_error",
    )
