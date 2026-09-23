"""OpenRouter互換APIを呼び出す。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from openai import OpenAI

from agent_eval.config import ModelSettings, load_api_key


# モデル応答を表す
@dataclass(frozen=True)
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    duration_ms: float


# OpenRouterへ接続する
class OpenRouterClient:
    # 接続設定を受け取る
    def __init__(self, settings: ModelSettings) -> None:
        self._settings = settings
        self._client = OpenAI(
            base_url=str(settings.base_url),
            api_key=load_api_key(settings),
            timeout=settings.timeout_seconds,
        )

    # チャット応答を取得する
    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        started_at = perf_counter()
        completion = self._client.chat.completions.create(
            model=self._settings.model,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        duration_ms = (perf_counter() - started_at) * 1000
        usage = completion.usage
        content = completion.choices[0].message.content or ""
        return ModelResponse(
            content=content,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            estimated_cost_usd=_usage_cost(usage),
            duration_ms=duration_ms,
        )


# 利用量から費用を取得する
def _usage_cost(usage: Any) -> float:
    return float(getattr(usage, "cost", 0) or 0) if usage else 0.0


# JSON形式の応答を検証する
def parse_json_response(content: str) -> dict[str, Any]:
    normalized = content.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    decoded = json.loads(normalized)
    if not isinstance(decoded, dict):
        raise ValueError("モデル応答はJSONオブジェクトで返してください")
    return decoded
