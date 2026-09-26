# 注意点: インデックスキャッシュはYAML更新時に再生成が必要となる点に注意
# 代替案: ファイル更新検知にinotifyやmtimeハッシュを使う自動無効化の選択肢がある
"""Benchmark YAMLを検証して読む。"""

from __future__ import annotations

import ctypes
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator

import jsonschema
import yaml
from pydantic import BaseModel, ConfigDict, Field

try:
    from yaml import CSafeLoader

    FastYamlLoader: type[Any] = CSafeLoader
except ImportError:
    FastYamlLoader = yaml.SafeLoader


# タスク本文を表す
class TaskDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)


# 評価設定を表す
class EvaluationDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_metrics: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)


# 実行上限を表す
class LimitDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_steps: int | None = Field(default=None, ge=1)
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_estimated_cost_usd: float | None = Field(default=None, ge=0)


# Benchmark全体を表す
class BenchmarkDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    id: str
    title: str
    family: str
    category: str
    fixture: str
    task: TaskDefinition
    expected: dict[str, Any]
    constraints: dict[str, Any] = Field(default_factory=dict)
    evaluation: EvaluationDefinition = Field(default_factory=EvaluationDefinition)
    limits: LimitDefinition = Field(default_factory=LimitDefinition)
    status: str = "draft"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# JSON Schemaを読み込む
@lru_cache(maxsize=8)
def load_schema(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


# スキーマ検証器を事前生成する
@lru_cache(maxsize=8)
def get_validator(path: str | Path) -> jsonschema.Draft202012Validator:
    schema = load_schema(str(Path(path).resolve()))
    return jsonschema.Draft202012Validator(schema)


# 高速にYAMLを解析する
def fast_yaml_load(content: str | bytes) -> dict[str, Any]:
    return yaml.load(content, Loader=FastYamlLoader)


# Rustパーサーライブラリを探索する
@lru_cache(maxsize=1)
def find_rust_lib() -> ctypes.CDLL | None:
    candidates = [
        Path("crates/agent_eval_rust/target/release/libagent_eval_rust.so"),
        Path("crates/agent_eval_rust/target/release/agent_eval_rust.dll"),
        Path("/usr/local/lib/libagent_eval_rust.so"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                lib = ctypes.CDLL(str(path))
                lib.agent_eval_parse_yaml.argtypes = [ctypes.c_char_p]
                lib.agent_eval_parse_yaml.restype = ctypes.c_void_p
                lib.agent_eval_free_string.argtypes = [ctypes.c_void_p]
                lib.agent_eval_free_string.restype = None
                return lib
            except Exception:
                continue
    return None


# Rust経由でYAMLを解析する
def parse_benchmark_rust(content: str) -> dict[str, Any] | None:
    lib = find_rust_lib()
    if lib is None:
        return None
    c_text = ctypes.c_char_p(content.encode("utf-8"))
    raw_ptr = lib.agent_eval_parse_yaml(c_text)
    if not raw_ptr:
        return None
    try:
        raw_value = ctypes.cast(raw_ptr, ctypes.c_char_p).value
        if raw_value is None:
            raise ValueError("Rust YAML parser returned empty data")
        json_str = raw_value.decode("utf-8")
        parsed = json.loads(json_str)
        if "error" in parsed:
            raise ValueError(parsed["error"])
        return parsed
    finally:
        lib.agent_eval_free_string(raw_ptr)


# Benchmark YAMLを検証して読む
def load_benchmark(path: str | Path, schema_path: str | Path) -> BenchmarkDefinition:
    resolved_path = Path(path)
    raw_benchmark = fast_yaml_load(resolved_path.read_text(encoding="utf-8"))

    validator = get_validator(schema_path)
    validator.validate(raw_benchmark)
    return BenchmarkDefinition.model_validate(raw_benchmark)


# データセットをストリーミング走査する
def iter_benchmarks_stream(
    paths: Iterable[str | Path],
    schema_path: str | Path,
) -> Iterator[BenchmarkDefinition]:
    validator = get_validator(schema_path)
    for path in paths:
        resolved = Path(path)
        raw = fast_yaml_load(resolved.read_text(encoding="utf-8"))
        validator.validate(raw)
        yield BenchmarkDefinition.model_validate(raw)


# メタデータをストリーミング抽出する
def iter_benchmark_summaries_stream(
    paths: Iterable[str | Path],
) -> Iterator[dict[str, Any]]:
    for path in paths:
        resolved = Path(path)
        text = resolved.read_text(encoding="utf-8")
        rust_result = parse_benchmark_rust(text)
        if rust_result is not None:
            yield {
                "id": rust_result["id"],
                "title": rust_result["title"],
                "family": rust_result["family"],
                "path": str(resolved),
            }
            continue

        raw = fast_yaml_load(text)
        yield {
            "id": str(raw.get("id", "")),
            "title": str(raw.get("title", "")),
            "family": str(raw.get("family", "")),
            "path": str(resolved),
        }


# 事前インデックスJSONを生成する
def generate_benchmark_index(
    benchmark_dir: str | Path,
    output_path: str | Path,
) -> Path:
    dir_path = Path(benchmark_dir)
    out_path = Path(output_path)
    yaml_paths = [
        p for p in sorted(dir_path.glob("*/*.yaml"))
        if p.name != "index.yaml"
    ]
    summaries = list(iter_benchmark_summaries_stream(yaml_paths))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"total": len(summaries), "benchmarks": summaries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


# 事前インデックスを高速に読む
def load_benchmark_index(index_path: str | Path) -> dict[str, Any]:
    path = Path(index_path)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# 作成例（テンプレート）を取得する
def get_benchmark_template(family: str) -> dict[str, Any]:
    if family == "coding":
        return {
            "schema_version": "0.1",
            "id": "COD-USER-001",
            "title": "Pythonのファイル読み込みエラーを修正できる",
            "family": "coding",
            "category": "bug_fix",
            "tags": ["coding", "python", "user-created"],
            "fixture": "coding/bash-workspace-v1",
            "status": "draft",
            "metadata": {
                "task_version": 1,
                "split": "dev",
                "source": "user-created",
                "contamination_risk": "low",
                "human_review": "pending",
            },
            "task": {
                "prompt": "指定されたファイルが存在しない場合の例外処理を追加し、終了コード0で完了させてください。",
            },
            "constraints": {
                "allowed_paths": ["workspace"],
                "forbidden_paths": ["verify"],
                "network": "disabled",
            },
            "expected": {
                "success_conditions": [
                    {"type": "verification_command_exit_code", "value": 0},
                    {"type": "changed_path_within", "value": "workspace"},
                ],
                "failure_conditions": [
                    {"type": "modified_forbidden_path", "value": "verify"},
                ],
            },
            "evaluation": {
                "required_metrics": [
                    "task_success",
                    "changed_file_count",
                    "diff_size",
                    "build_success",
                    "test_success",
                    "latency",
                    "estimated_cost",
                ],
                "trace": {"record_observations": True, "record_actions": True, "record_tool_results": True},
            },
            "limits": {
                "max_steps": 40,
                "timeout_seconds": 300,
                "max_estimated_cost_usd": 1.0,
            },
        }

    return {
        "schema_version": "0.1",
        "id": "GEN-USER-001",
        "title": "JSON形式でのキー抽出を正確に行える",
        "family": "generic",
        "category": "task_success",
        "tags": ["generic", "json", "user-created"],
        "fixture": "generic/data-processing-v1",
        "status": "draft",
        "metadata": {
            "task_version": 1,
            "split": "dev",
            "source": "user-created",
            "contamination_risk": "low",
            "human_review": "pending",
        },
        "task": {
            "prompt": "与えられたテキストからユーザー名とIDを抽出し、指定のJSON形式で出力してください。",
        },
        "constraints": {
            "network": "disabled",
            "max_retries_per_tool": 2,
        },
        "expected": {
            "success_conditions": [
                {"type": "policy_and_final_state_satisfied"},
            ],
            "failure_conditions": [
                {"type": "forbidden_action_attempted"},
            ],
        },
        "evaluation": {
            "required_metrics": [
                "task_success",
                "step_count",
                "tool_call_count",
                "retry_count",
                "latency",
                "estimated_cost",
                "safety_violation_count",
            ],
            "trace": {"record_observations": True, "record_actions": True, "record_tool_results": True},
        },
        "limits": {
            "max_steps": 12,
            "timeout_seconds": 60,
            "max_estimated_cost_usd": 0.10,
        },
    }


# 利用者作成benchmarkを検証してローカルへ保存する
def save_custom_benchmark(
    data: dict[str, Any],
    schema_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    validator = get_validator(schema_path)
    validator.validate(data)

    benchmark_id = data["id"]
    family = data["family"]
    if family not in ("generic", "coding"):
        raise ValueError(f"初期対応は generic と coding のみです: {family}")

    if output_dir is None:
        target_dir = Path("benchmarks") / "user" / family
    else:
        target_dir = Path(output_dir) / family

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{benchmark_id}.yaml"

    if target_path.exists():
        raise FileExistsError(f"同じBenchmark IDは既に保存されています: {benchmark_id}")

    with target_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    return target_path
