"""REST API の入出力形式を定義する。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# 評価開始リクエストを表す
class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str = Field(min_length=1, max_length=128)
    source: Literal["sample", "user-created"] = "sample"


# 外部Agent実行の開始情報を表す
class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str = Field(min_length=1, max_length=128)
    agent_name: str = Field(min_length=1, max_length=128)
    provider: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=256)
    architecture: dict[str, Any] = Field(default_factory=dict)
    run_config: dict[str, Any] = Field(default_factory=dict)


# 実行イベントの保存内容を表す
class CreateEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=0)
    event_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_state: dict[str, Any] | None = None
    next_state: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    actor: str = Field(default="agent", min_length=1, max_length=64)
    trace_id: str | None = Field(default=None, max_length=128)
    span_id: str | None = Field(default=None, max_length=128)


# 外部Agent実行の終了情報を表す
class FinishRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed", "cancelled"]
    final_state: dict[str, Any] = Field(default_factory=dict)
    failure_category: str | None = Field(default=None, max_length=32)
    llm_cost_usd: float | None = Field(default=None, ge=0)


# 外部Agent記録の取込要求を表す
class ImportTranscriptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_file: str = Field(min_length=1, max_length=512)
