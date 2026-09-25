"""自作datasetの保存・識別・再利用をテストする。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agent_eval.benchmark import get_benchmark_template, save_custom_benchmark
from scripts import tui_backend


SCHEMA_PATH = Path("schemas") / "benchmark.schema.json"


# 自作datasetを外部保存先へ保存する
def test_user_dataset_saves_limits_and_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path))
    data = get_benchmark_template("generic")
    data["id"] = "GEN-LOCAL-001"
    data["title"] = "ローカル保存確認"
    data["metadata"]["source"] = "user-created"
    data["limits"] = {"max_steps": 9, "timeout_seconds": 45, "max_estimated_cost_usd": 0.25}

    target = save_custom_benchmark(data, SCHEMA_PATH, tui_backend.user_dataset_root())
    saved = yaml.safe_load(target.read_text(encoding="utf-8"))

    assert target == tmp_path / "datasets" / "user" / "generic" / "GEN-LOCAL-001.yaml"
    assert saved["limits"]["max_steps"] == 9
    assert saved["metadata"]["source"] == "user-created"
    print(json.dumps({"test": "user_dataset_save", "path": str(target), "max_steps": 9}))


# 重複IDによる上書きを拒否する
def test_user_dataset_rejects_duplicate_id(tmp_path: Path) -> None:
    data = get_benchmark_template("generic")
    data["id"] = "GEN-DUPLICATE-001"
    save_custom_benchmark(data, SCHEMA_PATH, tmp_path)

    with pytest.raises(FileExistsError, match="既に保存"):
        save_custom_benchmark(data, SCHEMA_PATH, tmp_path)
    print(json.dumps({"test": "user_dataset_duplicate", "rejected": True}))


# 自作datasetだけを一覧から選別する
def test_user_dataset_filters_by_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_DATA_DIR", str(tmp_path))
    data = get_benchmark_template("generic")
    data["id"] = "GEN-FILTER-001"
    data["title"] = "自作フィルタ確認"
    save_custom_benchmark(data, SCHEMA_PATH, tui_backend.user_dataset_root())

    output = tui_backend.list_benchmarks(source="user-created", query="GEN-FILTER")

    assert output["total"] == 1
    assert output["benchmarks"][0]["source"] == "user-created"
    assert output["benchmarks"][0]["id"] == "GEN-FILTER-001"
    print(json.dumps({"test": "user_dataset_filter", "count": output["total"]}))
