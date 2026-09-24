"""OpenRouterを使うPhase 3 E2Eテスト。"""

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
from tests.output import print_test_result


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# liveテスト用DBを準備する
@pytest.fixture(scope="module")
def live_db_engine():
    if os.getenv("RUN_LIVE_OPENROUTER_E2E") != "1":
        pytest.skip("RUN_LIVE_OPENROUTER_E2E=1 を指定してください")
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


# OpenRouter実行結果をDBへ保存する
@pytest.mark.live
def test_openrouter_live_evaluation_displays_result(live_db_engine) -> None:
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
            stored_run = RunRepository(session).get_run(result.run_id)
            answer = str(result.final_state.get("answer", ""))
            evaluation = stored_run.evaluations[0]
            output = {
                "model": live_settings.model.model,
                "status": result.status,
                "answer": answer,
                "event_count": result.event_count,
                "metric_count": len(stored_run.metrics),
                "evaluation_status": evaluation.status,
            }
            if result.llm_cost_usd is not None:
                output["llm_cost_usd"] = result.llm_cost_usd
            print_test_result(
                "openrouter_live_evaluation_displays_result",
                "passed",
                **output,
            )

            assert result.final_state["dry_run"] is False
            assert answer
            assert result.event_count >= 6
            assert len(stored_run.metrics) == 16
            assert evaluation.status in {"passed", "failed"}
            assert float(stored_run.llm_cost_usd) == result.llm_cost_usd
    finally:
        if run_id is not None:
            with live_db_engine.begin() as connection:
                connection.execute(text("DELETE FROM runs WHERE id = :run_id"), {"run_id": run_id})
