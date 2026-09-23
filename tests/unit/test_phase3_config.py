"""Phase 3の設定とデータ検証を確認する。"""

from pathlib import Path

import pytest
from jsonschema import ValidationError

from agent_eval.benchmark import load_benchmark
from agent_eval.config import Phase3Settings, load_api_key, load_settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# YAML設定の読込を確認する
def test_load_phase3_settings() -> None:
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")

    assert settings.engine.dry_run is True
    assert settings.model.provider == "openrouter"
    assert settings.model.api_key_env == "OPENROUTER_API_KEY"


# プレースホルダーを拒否する
def test_placeholder_api_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    monkeypatch.setenv("OPENROUTER_API_KEY", "replace-with-your-openrouter-api-key")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        load_api_key(settings.model)


# benchmark検証の読込を確認する
def test_load_phase1_benchmark() -> None:
    benchmark = load_benchmark(
        PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml",
        PROJECT_ROOT / "schemas" / "benchmark.schema.json",
    )

    assert benchmark.id == "GEN-TOOL-001"
    assert "task_success" in benchmark.evaluation.required_metrics


# 未対応の観測設定を拒否する
def test_unknown_telemetry_exporter_is_rejected() -> None:
    raw_settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml").model_dump(mode="json")
    raw_settings["telemetry"]["exporter"] = "unknown"

    with pytest.raises(ValueError, match="exporter"):
        Phase3Settings.model_validate(raw_settings)


# 不正なbenchmarkを拒否する
def test_invalid_benchmark_is_rejected(tmp_path: Path) -> None:
    original = PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml"
    invalid = tmp_path / "invalid-benchmark.yaml"
    invalid.write_text(original.read_text(encoding="utf-8").replace('schema_version: "0.1"', 'schema_version: "invalid"'), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_benchmark(invalid, PROJECT_ROOT / "schemas" / "benchmark.schema.json")
