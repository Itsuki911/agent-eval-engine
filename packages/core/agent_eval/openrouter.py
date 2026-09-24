"""OpenRouter互換APIを呼び出す。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from openai import APITimeoutError, OpenAI, RateLimitError

from agent_eval.config import ModelSettings, load_api_key


# モデル応答を表す
@dataclass(frozen=True)
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    duration_ms: float


# OpenRouter応答時間超過を表す
class OpenRouterTimeoutError(RuntimeError):
    pass


# OpenRouterレート制限を表す
class OpenRouterRateLimitError(RuntimeError):
    pass


# OpenRouterへ接続する
class OpenRouterClient:
    # 接続設定を受け取る
    def __init__(self, settings: ModelSettings) -> None:
        self._settings = settings
        self._client = OpenAI(
            base_url=str(settings.base_url),
            api_key=load_api_key(settings),
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )

    # チャット応答を取得する
    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        started_at = perf_counter()
        try:
            completion = self._client.chat.completions.create(
                model=self._settings.model,
                temperature=self._settings.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except APITimeoutError as error:
            message = (
                "OpenRouterの応答がタイムアウトしました。"
                f"timeout_seconds={self._settings.timeout_seconds}, "
                f"max_retries={self._settings.max_retries}"
            )
            raise OpenRouterTimeoutError(message) from error
        except RateLimitError as error:
            message = (
                "OpenRouterのレート制限に達しました。"
                f"model={self._settings.model}, "
                f"max_retries={self._settings.max_retries}"
            )
            raise OpenRouterRateLimitError(message) from error
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
