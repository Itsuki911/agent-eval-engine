"""Phase 7 MCPとDB連携を確認する。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from agent_eval.config import load_settings
from apps.api.main import PROJECT_ROOT
from apps.mcp.server import EvaluationMCPService
from database.session import create_db_engine
from tests.output import print_test_result


# テストDBへmigrationを適用する
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


# MCPサービスをテスト用に作る
@pytest.fixture
def service(db_engine) -> EvaluationMCPService:
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    quiet_settings = settings.model_copy(update={"telemetry": settings.telemetry.model_copy(update={"exporter": "none"})})
    current_service = EvaluationMCPService(
        session_factory=sessionmaker(bind=db_engine, expire_on_commit=False),
        load_phase_settings=lambda _: quiet_settings,
        migrate_on_first_use=False,
    )
    yield current_service
    with Session(db_engine) as session:
        session.execute(text("TRUNCATE TABLE evaluations, metrics, events, run_agent_executions, artifacts, runs RESTART IDENTITY CASCADE"))
        session.commit()


# MCPから評価とtrace取得を行う
def test_mcp_run_benchmark_persists_trace(service: EvaluationMCPService) -> None:
    result = service.run_benchmark("GEN-TOOL-001")
    trace = service.get_trace(result["run_id"])

    assert result["status"] == "simulated"
    assert trace["total"] == result["event_count"]
    assert any(event["event_type"] == "benchmark_loaded" for event in trace["events"])
    print_test_result("mcp_run_benchmark_persists_trace", "passed", run_id=result["run_id"], event_count=trace["total"], status=result["status"])


# MCPから実行結果を比較する
def test_mcp_compare_runs_returns_metrics(service: EvaluationMCPService) -> None:
    left = service.run_benchmark("GEN-TOOL-001")
    right = service.evaluate_agent("GEN-TOOL-001")
    comparison = service.compare_runs(left["run_id"], right["run_id"])

    assert comparison["left_run_id"] == left["run_id"]
    assert any(metric["name"] == "success.task_success" for metric in comparison["metrics"])
    print_test_result("mcp_compare_runs_returns_metrics", "passed", compared_runs=2, metric_count=len(comparison["metrics"]))
