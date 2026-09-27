"""実Agent記録AdapterとDB連携を確認する。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from agent_eval.real_agent_adapter import import_agent_transcript
from database.repositories import RunRepository
from database.session import create_db_engine
from tests.output import print_test_result


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "fixtures" / "agent-traces" / "codex-success.jsonl"


# Adapter用テストDBを準備する
@pytest.fixture(scope="module")
def db_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL を設定してください")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous
    yield create_db_engine(url)


# 記録から実行履歴を再構成する
def test_import_agent_transcript_persists_complete_history(db_engine) -> None:
    with Session(db_engine) as session:
        result = import_agent_transcript(RunRepository(session), FIXTURE)
        history = RunRepository(session).reconstruct_history(result["run_id"])

    assert result["adapter_type"] == "codex"
    assert result["event_count"] == 3
    assert history["status"] == "completed"
    assert [event["event_type"] for event in history["events"]] == ["user_prompt", "tool_call", "tool_result"]
    assert history["agent_executions"][0]["adapter_type"] == "codex"
    assert history["artifacts"][0]["uri"] == "local://agent-traces/codex-success.jsonl"
    print_test_result("real_agent_import_history", "passed", run_id=result["run_id"], event_count=result["event_count"])


# 同一Agent接続先を再利用する
def test_import_agent_transcript_reuses_agent_target(db_engine) -> None:
    with Session(db_engine) as session:
        first = import_agent_transcript(RunRepository(session), FIXTURE)
        second = import_agent_transcript(RunRepository(session), FIXTURE)
        targets = session.execute(text("SELECT name FROM agent_targets WHERE name = 'codex:codex-cli'"))

        assert len(targets.all()) == 1

    assert first["run_id"] != second["run_id"]
    print_test_result("real_agent_target_reuse", "passed", target_count=1, imported_runs=2)
