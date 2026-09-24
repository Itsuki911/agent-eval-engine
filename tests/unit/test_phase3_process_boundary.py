"""Phase 3のプロセス境界を確認する。"""

from __future__ import annotations

import json
from types import SimpleNamespace

from agent_eval.config import TelemetrySettings
from agent_eval.telemetry import create_telemetry
from database import migration
from scripts import migrate_database, run_evaluation


# 最終結果が標準出力のJSON1件になる
def test_result_output_is_single_stdout_json(capsys) -> None:
    result = SimpleNamespace(
        run_id="run-001",
        status="completed",
        benchmark_id="GEN-TOOL-001",
        final_state={"success": True},
        event_count=8,
        metrics=[SimpleNamespace(name="task_success", value=1.0)],
        llm_cost_usd=0.001,
    )

    run_evaluation.print_result_output(result)

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert captured.err == ""
    assert captured.out.count("\n") == 1
    assert output["run_id"] == "run-001"
    assert output["llm_cost_usd"] == 0.001


# Telemetryを標準エラーへ分離する
def test_console_telemetry_uses_stderr(capsys) -> None:
    telemetry = create_telemetry(TelemetrySettings(service_name="test", exporter="console"))

    with telemetry.tracer.start_as_current_span("process_boundary"):
        pass

    telemetry.provider.force_flush()
    captured = capsys.readouterr()
    telemetry.provider.shutdown()
    assert captured.out == ""
    assert '"name": "process_boundary"' in captured.err


# 最新DBリビジョンを適用する
def test_upgrade_database_uses_alembic_head(monkeypatch) -> None:
    expected_revision = "20260924_0002"
    applied_revisions: list[str] = []
    config = migration.create_alembic_config()
    script_directory = SimpleNamespace(get_current_head=lambda: expected_revision)

    monkeypatch.setattr(migration, "create_alembic_config", lambda: config)
    monkeypatch.setattr(
        migration.ScriptDirectory,
        "from_config",
        lambda _: script_directory,
    )
    monkeypatch.setattr(
        migration.command,
        "upgrade",
        lambda _, revision: applied_revisions.append(revision),
    )

    revision = migration.upgrade_database()

    assert revision == expected_revision
    assert applied_revisions == [expected_revision]


# マイグレーション結果を標準出力へ出す
def test_migration_command_outputs_single_stdout_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(migrate_database, "upgrade_database", lambda: "20260924_0002")

    migrate_database.main()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "status": "upgraded",
        "revision": "20260924_0002",
    }
