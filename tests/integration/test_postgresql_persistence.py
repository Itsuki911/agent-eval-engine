"""PostgreSQL永続化を統合確認する。"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.repositories import RunRepository
from database.session import create_db_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# テストDBへマイグレーションする
@pytest.fixture(scope="session")
def db_engine():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL を設定してください")

    # AlembicへテストDBを渡す
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    # DB構造を最新版へ揃える
    command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")
    # 呼び出し元の設定を戻す
    if previous_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_url

    engine = create_db_engine(test_url)
    yield engine
    # 接続プールを解放する
    engine.dispose()


# テスト用データを初期化する
@pytest.fixture
def session(db_engine):
    with Session(db_engine) as current_session:
        yield current_session
        # 未確定の変更を取り消す
        current_session.rollback()
    with db_engine.begin() as connection:
        # 次のテストへデータを残さない
        connection.execute(
            text("TRUNCATE TABLE evaluations, metrics, events, runs RESTART IDENTITY CASCADE")
        )


# 必須テーブルの作成を確認する
def test_migration_creates_evaluation_tables(db_engine) -> None:
    # DBから実テーブル名を取得する
    table_names = set(inspect(db_engine).get_table_names())

    assert {"runs", "events", "metrics", "evaluations", "alembic_version"} <= table_names


# 生イベントから実行履歴を復元する
def test_events_reconstruct_complete_history(session: Session) -> None:
    repository = RunRepository(session)
    # イベントの親となる実行を作る
    run = repository.create_run(
        benchmark_id="generic/tool-selection/single-record",
        agent_name="sample-agent",
        provider="sample-provider",
        model="sample-model",
        architecture={"mode": "single-agent"},
        run_config={"max_steps": 3},
    )
    # 最初の入力を生データで保存する
    repository.add_event(
        run.id,
        sequence=0,
        event_type="user_prompt",
        payload={"content": "指定レコードを取得してください"},
        next_state={"phase": "tool_selection"},
        actor="user",
        trace_id="trace-001",
    )
    # ツール結果と状態遷移を保存する
    repository.add_event(
        run.id,
        sequence=1,
        event_type="tool_result",
        payload={"tool": "record.get", "result": {"id": "rec-001"}},
        previous_state={"phase": "tool_selection"},
        next_state={"phase": "completed"},
        trace_id="trace-001",
        span_id="span-001",
    )
    # 集計値と評価器の判定を保存する
    repository.add_metric(run.id, "success", "task_success", 1.0, "ratio")
    repository.add_evaluation(
        run.id,
        "rule-evaluator",
        "1.0.0",
        "passed",
        1.0,
        summary={"reason": "expected record returned"},
    )
    # 最終状態を確定して保存する
    repository.finish_run(run.id, "completed", {"record_id": "rec-001"})
    # ここでDBへ変更を確定する
    session.commit()

    # 保存済みイベントから履歴を組み立てる
    history = repository.reconstruct_history(run.id)

    # 実行全体の状態を確認する
    assert history["status"] == "completed"
    assert history["final_state"] == {"record_id": "rec-001"}
    assert history["started_at"]
    assert history["finished_at"]
    # イベント順序と生payloadを確認する
    assert [event["sequence"] for event in history["events"]] == [0, 1]
    assert history["events"][0]["occurred_at"]
    assert history["events"][0]["payload"]["content"] == "指定レコードを取得してください"
    assert history["events"][1]["payload"]["result"] == {"id": "rec-001"}
    assert history["events"][1]["trace_id"] == "trace-001"
    assert history["events"][1]["span_id"] == "span-001"
    # 関連テーブルの保存も確認する
    assert repository.get_run(run.id).metrics[0].name == "task_success"
    assert repository.get_run(run.id).evaluations[0].status == "passed"


# 重複したイベント順序を拒否する
def test_duplicate_event_sequence_is_rejected(session: Session) -> None:
    repository = RunRepository(session)
    run = repository.create_run("generic/tool", "sample-agent")
    # 最初の順序番号は保存できる
    repository.add_event(run.id, 0, "user_prompt", {"content": "first"})

    # DBの一意制約違反を確認する
    with pytest.raises(IntegrityError):
        repository.add_event(run.id, 0, "tool_result", {"content": "duplicate"})


# 未登録実行の終了を拒否する
def test_unknown_run_is_rejected(session: Session) -> None:
    repository = RunRepository(session)

    # 存在しない主キーは更新できない
    with pytest.raises(ValueError):
        repository.finish_run(uuid4(), "completed", {"result": "none"})
