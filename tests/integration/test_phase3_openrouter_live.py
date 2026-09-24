"""OpenRouterを含む評価ワークフローを確認する。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from agent_eval.config import load_settings
from agent_eval.workflow import EvaluationService
from database.repositories import RunRepository
from database.session import create_db_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# live統合テスト用DBを準備する
@pytest.fixture(scope="module")
def live_db_engine():
    if os.getenv("RUN_LIVE_OPENROUTER_INTEGRATION") != "1":
        pytest.skip("RUN_LIVE_OPENROUTER_INTEGRATION=1 を指定してください")
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY を設定してください")
    test_url = os.getenv("TEST_DATABASE_URL")
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


# モデル応答を評価履歴へ保存する
@pytest.mark.live
def test_openrouter_live_workflow_persists_history(live_db_engine) -> None:
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    telemetry = settings.telemetry.model_copy(update={"exporter": "none"})
    engine_settings = settings.engine.model_copy(update={"dry_run": False})
    live_settings = settings.model_copy(
        update={"engine": engine_settings, "telemetry": telemetry}
    )

    run_id = None
    try:
        with Session(live_db_engine) as session:
            result = EvaluationService(live_settings, session).run(
                PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml"
            )
            run_id = result.run_id
            history = RunRepository(session).reconstruct_history(result.run_id)
            stored_run = RunRepository(session).get_run(result.run_id)
            event_types = [event["event_type"] for event in history["events"]]
            evaluation = stored_run.evaluations[0]
            print(
                "OpenRouter Integration: "
                f"model={live_settings.model.model}, status={result.status}, "
                f"events={result.event_count}, metrics={len(stored_run.metrics)}, "
                f"evaluation={evaluation.status}, event_types={event_types}"
            )

            assert result.final_state["dry_run"] is False
            assert "llm_call" in event_types
            assert (
                "model_response" in event_types
                or "model_error" in event_types
                or "timeout_error" in event_types
                or "rate_limit_error" in event_types
            )
            assert len(stored_run.metrics) == 16
            assert evaluation.status in {"passed", "failed"}
    finally:
        if run_id is not None:
            with live_db_engine.begin() as connection:
                connection.execute(text("DELETE FROM runs WHERE id = :run_id"), {"run_id": run_id})
