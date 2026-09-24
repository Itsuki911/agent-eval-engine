"""Phase 3の設定とデータ検証を確認する。"""

from pathlib import Path

import pytest
from jsonschema import ValidationError

from agent_eval.benchmark import load_benchmark
from agent_eval.config import Phase3Settings, load_api_key, load_settings
from tests.output import print_test_result


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# YAML設定の読込を確認する
def test_load_phase3_settings() -> None:
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")

    assert settings.engine.dry_run is True
    assert settings.model.provider == "openrouter"
    assert settings.model.api_key_env == "OPENROUTER_API_KEY"
    assert settings.model.max_retries == 1
    assert settings.model.connect_timeout_seconds == 10
    assert settings.model.read_timeout_seconds == 60
    assert settings.model.retryable_status_codes == [408, 429, 500, 502, 503, 504]
    assert settings.model.retry_backoff_initial_seconds == 1.0
    assert settings.model.retry_backoff_max_seconds == 10.0
    assert settings.model.retry_jitter == 0.2
    assert settings.model.max_input_tokens == 4096
    assert settings.model.max_prompt_chars == 16000
    assert settings.model.max_output_tokens == 1024
    assert settings.model.max_estimated_cost_usd == 0.10
    assert settings.model.max_cost_per_run_usd == 1.00
    assert settings.model.validate_structured_output is True
    assert settings.model.response_format == "json_object"
    assert settings.model.response_schema is None
    assert settings.model.idempotency_key_mode == "per_request"
    print_test_result(
        "load_phase3_settings",
        "passed",
        model=settings.model.model,
        dry_run=settings.engine.dry_run,
        provider=settings.model.provider,
        api_key_env=settings.model.api_key_env,
        max_retries=settings.model.max_retries,
    )


# プレースホルダーを拒否する
def test_placeholder_api_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    monkeypatch.setenv("OPENROUTER_API_KEY", "replace-with-your-openrouter-api-key")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        load_api_key(settings.model)
    print_test_result(
        "placeholder_api_key_is_rejected",
        "passed",
        model=settings.model.model,
        rejected_reason="placeholder_api_key",
        external_request_started=False,
    )


# benchmark検証の読込を確認する
def test_load_phase1_benchmark() -> None:
    benchmark = load_benchmark(
        PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml",
        PROJECT_ROOT / "schemas" / "benchmark.schema.json",
    )

    assert benchmark.id == "GEN-TOOL-001"
    assert "task_success" in benchmark.evaluation.required_metrics
    print_test_result(
        "load_phase1_benchmark",
        "passed",
        benchmark_id=benchmark.id,
        required_metric="task_success",
    )


# 未対応の観測設定を拒否する
def test_unknown_telemetry_exporter_is_rejected() -> None:
    raw_settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml").model_dump(mode="json")
    raw_settings["telemetry"]["exporter"] = "unknown"

    with pytest.raises(ValueError, match="exporter"):
        Phase3Settings.model_validate(raw_settings)
    print_test_result(
        "unknown_telemetry_exporter_is_rejected",
        "passed",
        rejected_exporter="unknown",
    )


# 不正なbenchmarkを拒否する
def test_invalid_benchmark_is_rejected(tmp_path: Path) -> None:
    original = PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml"
    invalid = tmp_path / "invalid-benchmark.yaml"
    invalid.write_text(original.read_text(encoding="utf-8").replace('schema_version: "0.1"', 'schema_version: "invalid"'), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_benchmark(invalid, PROJECT_ROOT / "schemas" / "benchmark.schema.json")
    print_test_result(
        "invalid_benchmark_is_rejected",
        "passed",
        rejected_schema_version="invalid",
        evaluation_started=False,
    )
