"""Phase 6 REST APIとDB連携を確認する。"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from agent_eval.config import load_settings
from apps.api.main import PROJECT_ROOT, create_app
from database.session import create_db_engine
from tests.output import print_test_result


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


# API用セッション生成器を作る
@pytest.fixture
def api_client(db_engine):
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    base_settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    quiet_settings = base_settings.model_copy(
        update={"telemetry": base_settings.telemetry.model_copy(update={"exporter": "none"})}
    )
    app = create_app(
        session_factory=factory,
        load_phase_settings=lambda _: quiet_settings,
        migrate_on_startup=False,
    )
    with TestClient(app) as client:
        yield client
    with Session(db_engine) as session:
        session.execute(
            text("TRUNCATE TABLE evaluations, metrics, events, run_agent_executions, artifacts, runs RESTART IDENTITY CASCADE")
        )
        session.commit()


# dry-run評価と履歴取得を確認する
def test_evaluate_returns_persisted_run_and_trace(api_client: TestClient) -> None:
    response = api_client.post("/evaluate", json={"benchmark_id": "GEN-TOOL-001"})

    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "simulated"
    assert result["event_count"] >= 6

    trace = api_client.get(f"/runs/{result['run_id']}/trace")
    metrics = api_client.get(f"/runs/{result['run_id']}/metrics")
    listed = api_client.get("/runs?limit=1&offset=0")

    assert trace.status_code == 200
    assert trace.json()["total"] == result["event_count"]
    assert any(event["event_type"] == "benchmark_loaded" for event in trace.json()["events"])
    assert metrics.status_code == 200
    assert any(metric["name"] == "task_success" for metric in metrics.json()["metrics"])
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert listed.json()["runs"][0]["run_id"] == result["run_id"]
    print_test_result(
        "evaluate_returns_persisted_run_and_trace",
        "passed",
        status=result["status"],
        event_count=result["event_count"],
        metric_count=len(metrics.json()["metrics"]),
    )


# 外部Agentの開始から終了までを確認する
def test_external_agent_run_records_event_and_finish(api_client: TestClient) -> None:
    created = api_client.post(
        "/runs",
        json={"benchmark_id": "GEN-API-001", "agent_name": "external-agent", "provider": "local"},
    )

    assert created.status_code == 201
    run_id = created.json()["run_id"]
    event = api_client.post(
        f"/runs/{run_id}/events",
        json={"sequence": 0, "event_type": "tool_call", "payload": {"tool": "read"}, "actor": "agent"},
    )
    finished = api_client.post(
        f"/runs/{run_id}/finish",
        json={"status": "completed", "final_state": {"success": True}},
    )

    assert event.status_code == 201
    assert event.json()["trace_id"] is None
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"
    detail = api_client.get(f"/runs/{run_id}")
    assert detail.json()["events"][0]["payload"]["tool"] == "read"
    print_test_result(
        "external_agent_run_records_event_and_finish",
        "passed",
        status=finished.json()["status"],
        event_type=event.json()["event_type"],
        event_count=detail.json()["event_total"],
    )


# 重複イベント連番を拒否する
def test_duplicate_event_sequence_returns_conflict(api_client: TestClient) -> None:
    created = api_client.post("/runs", json={"benchmark_id": "GEN-API-002", "agent_name": "external-agent"})
    run_id = created.json()["run_id"]
    payload = {"sequence": 0, "event_type": "tool_call", "payload": {"tool": "read"}}

    assert api_client.post(f"/runs/{run_id}/events", json=payload).status_code == 201
    duplicated = api_client.post(f"/runs/{run_id}/events", json=payload)

    assert duplicated.status_code == 409
    assert duplicated.json()["detail"] == "event sequence already exists"
    print_test_result(
        "duplicate_event_sequence_returns_conflict",
        "passed",
        status_code=duplicated.status_code,
        detail=duplicated.json()["detail"],
    )


# 未登録benchmarkを拒否する
def test_evaluate_unknown_benchmark_returns_not_found(api_client: TestClient) -> None:
    response = api_client.post("/evaluate", json={"benchmark_id": "UNKNOWN-API-001"})

    assert response.status_code == 404
    assert "benchmark not found" in response.json()["detail"]
    print_test_result(
        "evaluate_unknown_benchmark_returns_not_found",
        "passed",
        status_code=response.status_code,
        detail=response.json()["detail"],
    )


# 秘密情報を含むイベントを拒否する
def test_event_with_secret_configuration_is_rejected(api_client: TestClient) -> None:
    created = api_client.post("/runs", json={"benchmark_id": "GEN-API-003", "agent_name": "external-agent"})
    run_id = created.json()["run_id"]
    response = api_client.post(
        f"/runs/{run_id}/events",
        json={"sequence": 0, "event_type": "tool_call", "payload": {"api_key": "not-stored"}},
    )

    assert response.status_code == 422
    assert "秘密情報" in response.json()["detail"]
    print_test_result(
        "event_with_secret_configuration_is_rejected",
        "passed",
        status_code=response.status_code,
        secret_stored=False,
    )


# 2実行の評価指標を比較できる
def test_compare_returns_metric_differences(api_client: TestClient) -> None:
    left = api_client.post("/evaluate", json={"benchmark_id": "GEN-TOOL-001"}).json()
    right = api_client.post("/evaluate", json={"benchmark_id": "GEN-TOOL-001"}).json()

    response = api_client.get(f"/compare?left_run_id={left['run_id']}&right_run_id={right['run_id']}")

    assert response.status_code == 200
    assert response.json()["left_run_id"] == left["run_id"]
    assert any(metric["name"] == "success.task_success" for metric in response.json()["metrics"])
    print_test_result(
        "compare_returns_metric_differences",
        "passed",
        metric_count=len(response.json()["metrics"]),
        compared_runs=2,
    )
