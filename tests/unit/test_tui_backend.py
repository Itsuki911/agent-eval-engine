"""TUI backend境界を単体テストする。"""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from agent_eval.events import CollectedEvent
from agent_eval.workflow import EvaluationResult
from scripts import tui_backend


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


# ID検索で候補を絞り込む
def test_list_benchmarks_filters_by_id() -> None:
    output = tui_backend.list_benchmarks(query="GEN-TOOL", limit=50)

    assert output["benchmarks"]
    assert all(row["id"].startswith("GEN-TOOL") for row in output["benchmarks"])
    print(json.dumps({"test": "benchmark_filter", "total": output["total"], "query": "GEN-TOOL"}))


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
