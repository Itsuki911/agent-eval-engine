"""ベンチマーク作成・検証・保存・再利用・評価実行をテストする。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from agent_eval.benchmark import (
    BenchmarkDefinition,
    get_benchmark_template,
    get_validator,
    load_benchmark,
    save_custom_benchmark,
)
from agent_eval.config import load_settings
from agent_eval.workflow import EvaluationService
from database.session import create_session_factory
from scripts import tui_backend


SCHEMA_PATH = Path("schemas") / "benchmark.schema.json"


def test_get_benchmark_template_conforms_to_schema() -> None:
    validator = get_validator(SCHEMA_PATH)

    for family in ("generic", "coding"):
        template = get_benchmark_template(family)
        assert template["family"] == family
        assert "schema_version" in template
        assert "id" in template
        assert "title" in template
        assert "task" in template
        assert "prompt" in template["task"]
        assert "expected" in template
        assert "evaluation" in template
        assert "limits" in template

        # スキーマ検証
        validator.validate(template)

        # Pydantic モデル検証
        model = BenchmarkDefinition.model_validate(template)
        assert model.family == family
        assert model.id == template["id"]


def test_save_custom_benchmark_success(tmp_path: Path) -> None:
    template = get_benchmark_template("generic")
    template["id"] = "GEN-CUSTOM-001"
    template["title"] = "テスト用カスタムベンチマーク"
    template["task"]["prompt"] = "カスタム指示：テストを実行してください。"

    saved_path = save_custom_benchmark(template, SCHEMA_PATH, output_dir=tmp_path)

    expected_path = tmp_path / "generic" / "GEN-CUSTOM-001.yaml"
    assert saved_path == expected_path
    assert saved_path.exists()

    # YAML内容の整合性を確認
    with saved_path.open("r", encoding="utf-8") as f:
        loaded_data = yaml.safe_load(f)
    assert loaded_data["id"] == "GEN-CUSTOM-001"
    assert loaded_data["title"] == "テスト用カスタムベンチマーク"
    assert loaded_data["task"]["prompt"] == "カスタム指示：テストを実行してください。"

    # load_benchmarkでスキーマ検証＆モデル化できるか確認
    loaded_benchmark = load_benchmark(saved_path, SCHEMA_PATH)
    assert loaded_benchmark.id == "GEN-CUSTOM-001"
    assert loaded_benchmark.family == "generic"


def test_save_custom_benchmark_validation_failure(tmp_path: Path) -> None:
    template = get_benchmark_template("generic")

    # 1. promptが空文字（min_length違反）
    invalid_data = dict(template)
    invalid_data["task"] = {"prompt": ""}
    with pytest.raises(jsonschema.ValidationError):
        save_custom_benchmark(invalid_data, SCHEMA_PATH, output_dir=tmp_path)

    # 2. 必須フィールド id の欠落
    invalid_data_no_id = dict(template)
    del invalid_data_no_id["id"]
    with pytest.raises((jsonschema.ValidationError, KeyError)):
        save_custom_benchmark(invalid_data_no_id, SCHEMA_PATH, output_dir=tmp_path)

    # 3. 未対応の family
    invalid_data_family = dict(template)
    invalid_data_family["family"] = "multimodal"
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        save_custom_benchmark(invalid_data_family, SCHEMA_PATH, output_dir=tmp_path)

    # 4. パターンに適合しない id フォーマット
    invalid_data_pattern = dict(template)
    invalid_data_pattern["id"] = "INVALID-ID-PATTERN-TOO-MANY-DASHES"
    with pytest.raises(jsonschema.ValidationError):
        save_custom_benchmark(invalid_data_pattern, SCHEMA_PATH, output_dir=tmp_path)


def test_tui_backend_create_and_list_reuse() -> None:
    user_benchmark_id = "GEN-REUSE-999"
    template = get_benchmark_template("generic")
    template["id"] = user_benchmark_id
    template["title"] = "再利用テスト用ベンチマーク"

    user_dir = Path("benchmarks") / "user" / "generic"
    user_dir.mkdir(parents=True, exist_ok=True)
    target_yaml = user_dir / f"{user_benchmark_id}.yaml"

    try:
        save_custom_benchmark(template, SCHEMA_PATH, output_dir=Path("benchmarks") / "user")
        assert target_yaml.exists()

        # list_benchmarks で検索できることを確認（再利用性の検証）
        result = tui_backend.list_benchmarks(family="generic", query=user_benchmark_id)
        assert result["total"] >= 1
        ids = [b["id"] for b in result["benchmarks"]]
        assert user_benchmark_id in ids

        matched = next(b for b in result["benchmarks"] if b["id"] == user_benchmark_id)
        assert matched["title"] == "再利用テスト用ベンチマーク"
        assert matched["family"] == "generic"
    finally:
        if target_yaml.exists():
            target_yaml.unlink()


def test_custom_benchmark_execution_dry_run(tmp_path: Path) -> None:
    template = get_benchmark_template("generic")
    template["id"] = "GEN-EXEC-001"
    template["title"] = "実行テスト用ベンチマーク"

    saved_path = save_custom_benchmark(template, SCHEMA_PATH, output_dir=tmp_path)

    settings = load_settings("configs/phase3-local.yaml")
    session_factory = create_session_factory()
    with session_factory() as session:
        # 同期実行
        service = EvaluationService(settings, session)
        result = service.run(str(saved_path))
        assert result.status == "simulated"
        assert result.benchmark_id == "GEN-EXEC-001"
        assert result.event_count > 0

        # 非同期実行
        async def _run_async():
            return await service.run_async(str(saved_path))

        result_async = asyncio.run(_run_async())
        assert result_async.status == "simulated"
        assert result_async.benchmark_id == "GEN-EXEC-001"
        assert result_async.event_count > 0
