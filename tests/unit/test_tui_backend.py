"""TUI backend境界を単体テストする。"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml

from agent_eval.events import CollectedEvent
from agent_eval.workflow import EvaluationResult
from scripts import tui_backend
from agent_eval.benchmark import get_benchmark_template
from agent_eval.sample_package import build_sample_package


# 進捗イベントをJSON Linesへ変換する
def test_print_progress_outputs_safe_json(capsys) -> None:
    event = CollectedEvent(
        sequence=3,
        event_type="llm_call",
        payload={"secret": "not-emitted"},
        actor="model",
    )

    tui_backend.print_progress(event)

    output = json.loads(capsys.readouterr().err)
    assert output == {
        "type": "progress",
        "sequence": 3,
        "event_type": "llm_call",
        "actor": "model",
        "status": "recorded",
    }
    print(json.dumps({"test": "progress", "event_type": output["event_type"], "secret_included": False}))


# 最終結果をGo向けJSONへ変換する
def test_result_output_contains_run_summary() -> None:
    result = EvaluationResult(
        run_id=uuid4(),
        status="simulated",
        benchmark_id="GEN-TOOL-001",
        final_state={"success": True, "dry_run": True},
        metrics=[],
        event_count=6,
        llm_cost_usd=None,
    )

    output = tui_backend.result_output(result)

    assert output["status"] == "simulated"
    assert output["benchmark_id"] == "GEN-TOOL-001"
    assert output["event_count"] == 6
    assert output["llm_cost_usd"] is None
    print(json.dumps({"test": "result", "status": output["status"], "event_count": output["event_count"]}))


# genericとcoding候補だけを取得する
def test_list_benchmarks_returns_supported_families() -> None:
    output = tui_backend.list_benchmarks()

    assert output["benchmarks"]
    assert output["limit"] == 12
    assert output["total"] >= len(output["benchmarks"])
    assert {row["family"] for row in output["benchmarks"]} <= {"generic", "coding"}
    assert all(row["path"].startswith("benchmarks/") for row in output["benchmarks"])
    assert all(not row["path"].endswith("/index.yaml") for row in output["benchmarks"])
    print(json.dumps({"test": "benchmarks", "count": len(output["benchmarks"]), "families": ["generic", "coding"]}))


# benchmark候補をページ単位で取得する
def test_list_benchmarks_returns_requested_page() -> None:
    first_page = tui_backend.list_benchmarks(limit=3, offset=0)
    second_page = tui_backend.list_benchmarks(limit=3, offset=3)

    assert len(first_page["benchmarks"]) == 3
    assert len(second_page["benchmarks"]) == 3
    assert first_page["offset"] == 0
    assert second_page["offset"] == 3
    assert {row["id"] for row in first_page["benchmarks"]}.isdisjoint(
        {row["id"] for row in second_page["benchmarks"]}
    )
    print(json.dumps({"test": "benchmark_page", "first_count": 3, "second_offset": 3}))


# TUIキャッシュ用に全候補を取得する
def test_list_benchmarks_accepts_cache_limit() -> None:
    output = tui_backend.list_benchmarks(limit=10_000)

    assert output["limit"] == 10_000
    assert len(output["benchmarks"]) == output["total"]
    print(json.dumps({"test": "benchmark_cache", "count": output["total"]}))


# ID検索で候補を絞り込む
def test_list_benchmarks_filters_by_id() -> None:
    output = tui_backend.list_benchmarks(query="GEN-TOOL", limit=50)

    assert output["benchmarks"]
    assert all(row["id"].startswith("GEN-TOOL") for row in output["benchmarks"])
    print(json.dumps({"test": "benchmark_filter", "total": output["total"], "query": "GEN-TOOL"}))


# TUI入力値を自作benchmarkとして保存する
def test_execute_create_benchmark_saves_complete_form(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path))
    data = get_benchmark_template("generic")
    data["id"] = "GEN-TUI-001"
    data["title"] = "TUI入力保存"
    data["limits"] = {"max_steps": 7, "timeout_seconds": 12.5, "max_estimated_cost_usd": 0.0}
    data["metadata"]["source"] = "user-created"

    output = tui_backend.execute_create_benchmark(SimpleNamespace(data=json.dumps(data)))
    saved = yaml.safe_load((tmp_path / "datasets" / "user" / "generic" / "GEN-TUI-001.yaml").read_text(encoding="utf-8"))

    assert output["source"] == "user-created"
    assert output["fixture"] == "generic/data-processing-v1"
    assert saved["limits"]["max_steps"] == 7
    assert saved["limits"]["max_estimated_cost_usd"] == 0.0
    print(json.dumps({"test": "tui_create", "id": output["id"], "max_steps": 7}))


# 自作benchmarkのYAML原文を取得する
def test_execute_show_user_benchmark_returns_saved_yaml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path))
    data = get_benchmark_template("generic")
    data["id"] = "GEN-VIEW-001"
    data["title"] = "YAML確認"
    tui_backend.execute_create_benchmark(SimpleNamespace(data=json.dumps(data)))

    output = tui_backend.execute_show_user_benchmark(SimpleNamespace(benchmark_id="GEN-VIEW-001"))

    assert output["id"] == "GEN-VIEW-001"
    assert "title: YAML確認" in output["yaml"]
    assert output["path"].endswith("datasets/user/generic/GEN-VIEW-001.yaml")
    print(json.dumps({"test": "user_benchmark_yaml", "id": output["id"]}))


# 存在しない自作benchmarkを拒否する
def test_execute_show_user_benchmark_rejects_unknown_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="自作benchmarkが見つかりません"):
        tui_backend.execute_show_user_benchmark(SimpleNamespace(benchmark_id="GEN-UNKNOWN-001"))
    print(json.dumps({"test": "user_benchmark_yaml", "rejected": True}))


# 存在しないfixtureを保存前に拒否する
def test_execute_create_benchmark_rejects_unknown_fixture(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path))
    data = get_benchmark_template("generic")
    data["id"] = "GEN-TUI-002"
    data["fixture"] = "generic/unknown-v1"

    with pytest.raises(ValueError, match="fixtureが見つかりません"):
        tui_backend.execute_create_benchmark(SimpleNamespace(data=json.dumps(data)))
    print(json.dumps({"test": "tui_fixture", "rejected": True}))


# TUI境界からsampleを導入する
def test_execute_install_sample_uses_local_data_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path / "data"))
    package = build_sample_package(Path(__file__).resolve().parents[2], tmp_path / "samples.zip")

    output = tui_backend.execute_install_sample(SimpleNamespace(package=str(package)))

    assert output["status"] == "installed"
    assert (tmp_path / "data" / "datasets" / "samples" / "phase1-samples-v1" / "manifest.json").is_file()
    print(json.dumps({"test": "tui_sample_install", "status": output["status"]}))


# 比較指標の差分を作る
def test_metric_map_uses_category_and_name() -> None:
    details = SimpleNamespace(
        metrics=[
            {"category": "success", "name": "task_success", "value": 1.0},
            {"category": "cost", "name": "total", "value": 0.02},
        ]
    )

    output = tui_backend.metric_map({"metrics": details.metrics})

    assert output == {"success.task_success": 1.0, "cost.total": 0.02}
    print(json.dumps({"test": "metric_map", "metric_count": len(output)}))
