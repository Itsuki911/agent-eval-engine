"""Phase 3の設定を読み込む。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# エンジン設定を表す
class EngineSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    dry_run: bool = True
    max_steps: int = Field(ge=1)


# モデル接続設定を表す
class ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["openrouter"] = "openrouter"
    model: str = Field(min_length=1)
    base_url: HttpUrl
    api_key_env: str = Field(min_length=1)
    timeout_seconds: int = Field(gt=0)
    connect_timeout_seconds: int | float | None = Field(default=None, gt=0)
    read_timeout_seconds: int | float | None = Field(default=None, gt=0)
    max_retries: int = Field(default=1, ge=0, le=10)
    retryable_status_codes: list[int] = Field(
        default_factory=lambda: [408, 429, 500, 502, 503, 504]
    )
    retry_backoff_initial_seconds: float = Field(default=1.0, ge=0)
    retry_backoff_max_seconds: float = Field(default=10.0, ge=0)
    retry_jitter: float = Field(default=0.2, ge=0)
    temperature: float = Field(ge=0, le=2)
    max_input_tokens: int | None = Field(default=None, gt=0)
    max_prompt_chars: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    max_estimated_cost_usd: float | None = Field(default=None, ge=0)
    max_cost_per_run_usd: float | None = Field(default=None, ge=0)
    validate_structured_output: bool = True
    response_format: str | dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    idempotency_key_mode: Literal["none", "per_run", "per_request"] = "per_request"
    max_concurrency: int = Field(default=5, ge=1)
    requests_per_minute: int | None = Field(default=None, ge=1)


# 観測設定を表す
class TelemetrySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_name: str = Field(min_length=1)
    exporter: Literal["console", "none"] = "console"


# Phase 3全体の設定を表す
class Phase3Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: EngineSettings
    model: ModelSettings
    telemetry: TelemetrySettings


# YAML設定を検証して読む
def load_settings(path: str | Path) -> Phase3Settings:
    with Path(path).open(encoding="utf-8") as config_file:
        raw_settings = yaml.safe_load(config_file)
    return Phase3Settings.model_validate(raw_settings)


# モデル用トークンを取得する
def load_api_key(settings: ModelSettings) -> str:
    api_key = os.getenv(settings.api_key_env)
    if not api_key or api_key.startswith("replace-with-"):
        raise ValueError(f"{settings.api_key_env} を設定してください")
    return api_key
