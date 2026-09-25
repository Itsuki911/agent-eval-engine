"""CSVエクスポート機能をテストする。"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agent_eval.exporter import export_runs_to_csv, get_default_download_directory, get_display_download_path
from database.session import create_session_factory
from database.repositories import RunRepository


def test_get_default_download_directory(monkeypatch) -> None:
    with TemporaryDirectory() as temp_dir:
        monkeypatch.setenv("AGENT_EVAL_DOWNLOAD_DIR", temp_dir)
        download_dir = get_default_download_directory()
        assert download_dir == Path(temp_dir).resolve()


# Docker用の表示パスを確認する
def test_get_display_download_path_uses_host_directory(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DOWNLOAD_DISPLAY_DIR", "C:/Users/test/Downloads")

    display = get_display_download_path(Path("/exports/agent_eval_runs.csv"))

    assert display.replace("\\", "/") == "C:/Users/test/Downloads/agent_eval_runs.csv"
    print('{"test":"csv_display_path","path":"C:/Users/test/Downloads/agent_eval_runs.csv"}')


def test_export_runs_to_csv_creates_valid_utf8_bom_file() -> None:
    session_factory = create_session_factory()
    with session_factory() as session:
        repo = RunRepository(session)
        # テスト用のRunを挿入
        run = repo.create_run(
            benchmark_id="GEN-TEST-CSV-001",
            agent_name="test-agent",
            provider="test-provider",
            model="test-model",
        )
        repo.add_metric(run.id, "success", "task_success", 1.0)
        repo.add_metric(run.id, "latency", "latency_ms", 123.45)
        repo.add_evaluation(run.id, "rule-based", "0.1", "passed", 1.0)
        repo.finish_run(run.id, "completed", {"success": True}, llm_cost_usd=0.005)
        session.commit()

        with TemporaryDirectory() as temp_dir:
            out_file = Path(temp_dir) / "test_runs.csv"
            result_path = export_runs_to_csv(session, output_path=out_file, run_id=run.id)

            assert result_path.exists()
            content_bytes = result_path.read_bytes()
            # UTF-8 BOM (\xef\xbb\xbf) が先頭にあることを検証
            assert content_bytes.startswith(b"\xef\xbb\xbf")

            text = content_bytes.decode("utf-8-sig")
            lines = text.strip().split("\n")
            header = lines[0].split(",")

            assert "run_id" in header
            assert "benchmark_id" in header
            assert "family" in header
            assert "status" in header
            assert "metric_success.task_success" in header

            data_row = lines[1].split(",")
            assert str(run.id) in data_row[0]
            assert "GEN-TEST-CSV-001" in lines[1]
            assert "completed" in lines[1]
