"""Phase 6向けAgent実行基盤の永続化を確認する。"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database.repositories import RunRepository
from database.session import create_db_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# Agent実行用テーブルを準備する
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
    return create_db_engine(url)


# 接続先・実行・成果物を再構成する
def test_agent_execution_records_are_reconstructable(db_engine) -> None:
    inspector = inspect(db_engine)
    assert {"agent_targets", "run_agent_executions", "artifacts"} <= set(inspector.get_table_names())

    with Session(db_engine) as session:
        repository = RunRepository(session)
        run = repository.create_run("COD-BASH-001", "phase6-test")
        target = repository.create_agent_target(
            f"local-cli-{uuid4().hex[:8]}",
            "cli",
            configuration={"command": "agent-eval-adapter", "sandbox": "container"},
            capabilities={"workspace": True},
            version="test-1",
        )
        execution = repository.create_agent_execution(
            run.id,
            "cli",
            target.id,
            target_snapshot={"name": target.name, "version": target.version},
        )
        repository.finish_agent_execution(execution.id, "completed", exit_code=0)
        repository.add_artifact(run.id, "workspace_diff", "local://artifacts/diff.patch", execution.id, "a" * 64, 12)
        history = repository.reconstruct_history(run.id)
        session.commit()

    assert history["agent_executions"][0]["adapter_type"] == "cli"
    assert history["agent_executions"][0]["exit_code"] == 0
    assert history["artifacts"][0]["kind"] == "workspace_diff"
    print('{"test":"agent_execution_history","execution_status":"completed","artifact_count":1}')


# 接続先設定への秘密情報保存を拒否する
def test_agent_target_rejects_secret_configuration(db_engine) -> None:
    with Session(db_engine) as session:
        repository = RunRepository(session)
        with pytest.raises(ValueError, match="秘密情報"):
            repository.create_agent_target("unsafe-target", "http", configuration={"api_key": "never-save"})
    print('{"test":"agent_target_secret","rejected":true}')
