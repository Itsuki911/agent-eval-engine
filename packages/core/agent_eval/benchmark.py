"""Benchmark YAMLを検証して読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import BaseModel, ConfigDict, Field


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
def load_schema(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


# Benchmark YAMLを検証して読む
def load_benchmark(path: str | Path, schema_path: str | Path) -> BenchmarkDefinition:
    with Path(path).open(encoding="utf-8") as benchmark_file:
        raw_benchmark = yaml.safe_load(benchmark_file)
    jsonschema.validate(raw_benchmark, load_schema(schema_path))
    return BenchmarkDefinition.model_validate(raw_benchmark)
