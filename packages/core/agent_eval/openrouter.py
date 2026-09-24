# 注意点: OpenRouter固有のHTTPステータス差異がある
# 選択肢: tenacityライブラリによる再試行制御も可能
"""OpenRouter互換APIを呼び出す。"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from agent_eval.config import ModelSettings, load_api_key


# モデル応答を表す
@dataclass(frozen=True)
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    duration_ms: float


# OpenRouter基底例外を表す
class OpenRouterError(RuntimeError):
    pass


# 応答時間超過例外を表す
class OpenRouterTimeoutError(OpenRouterError):
    pass


# レート制限例外を表す
class OpenRouterRateLimitError(OpenRouterError):
    pass


# 認証失敗の例外を表す
class OpenRouterAuthenticationError(OpenRouterError):
    pass


# 認可不足の例外を表す
class OpenRouterPermissionError(OpenRouterError):
    pass


# 不正リクエスト例外を表す
class OpenRouterBadRequestError(OpenRouterError):
    pass


# 入力上限超過例外を表す
class OpenRouterInputLimitError(OpenRouterError):
    pass


# 出力上限超過例外を表す
class OpenRouterOutputLimitError(OpenRouterError):
    pass


# モデル未発見例外を表す
class OpenRouterNotFoundError(OpenRouterError):
    pass


# プロバイダー障害例外を表す
class OpenRouterServerError(OpenRouterError):
    pass


# サービス停止例外を表す
class OpenRouterServiceUnavailableError(OpenRouterError):
    pass


# 接続失敗の例外を表す
class OpenRouterConnectionError(OpenRouterError):
    pass


# ストリーム切断例外を表す
class OpenRouterStreamDisconnectedError(OpenRouterError):
    pass


# 応答形式不正の例外を表す
class OpenRouterInvalidFormatError(OpenRouterError):
    pass


# 空応答受信の例外を表す
class OpenRouterEmptyResponseError(OpenRouterError):
    pass


# 安全フィルタ拒否例外を表す
class OpenRouterSafetyFilterError(OpenRouterError):
    pass


# フィルタ途中停止例外を表す
class OpenRouterContentFilterError(OpenRouterError):
    pass


# ツール呼出不正例外を表す
class OpenRouterToolCallError(OpenRouterError):
    pass


# 構造化出力検証例外を表す
class OpenRouterStructuredOutputError(OpenRouterError):
    pass


# コスト上限超過例外を表す
class OpenRouterCostLimitError(OpenRouterError):
    pass


# リトライ上限超過例外を表す
class OpenRouterRetryLimitError(OpenRouterError):
    pass


# 冪等性不整合の例外を表す
class OpenRouterIdempotencyError(OpenRouterError):
    pass


# 応答要求不整合例外を表す
class OpenRouterResponseMismatchError(OpenRouterError):
    pass


# OpenRouterへ接続する
class OpenRouterClient:
    # 接続設定を受け取る
    def __init__(self, settings: ModelSettings) -> None:
        self._settings = settings
        timeout = settings.connect_timeout_seconds or settings.timeout_seconds
        self._client = OpenAI(
            base_url=str(settings.base_url),
            api_key=load_api_key(settings),
            timeout=timeout,
            max_retries=settings.max_retries,
        )

    # 冪等性ヘッダーを生成する
    def _resolve_idempotency_headers(self, key: str | None = None) -> dict[str, str]:
        mode = self._settings.idempotency_key_mode
        if mode == "none":
            return {}
        if mode in ("per_request", "per_run"):
            header_value = key or str(uuid.uuid4())
            return {"X-Idempotency-Key": header_value, "Idempotency-Key": header_value}
        raise OpenRouterIdempotencyError(f"未対応のidempotency_key_modeです: {mode}")

    # 入力上限を事前検証する
    def _validate_input_limits(self, user_prompt: str) -> None:
        if self._settings.max_prompt_chars and len(user_prompt) > self._settings.max_prompt_chars:
            raise OpenRouterInputLimitError(
                f"入力文字数が上限を超過しました: {len(user_prompt)} > {self._settings.max_prompt_chars}"
            )
        if self._settings.max_input_tokens and len(user_prompt) > self._settings.max_input_tokens * 4:
            raise OpenRouterInputLimitError(
                f"概算入力トークン数が上限を超過しました: model={self._settings.model}"
            )

    # 応答の整合性を検証する
    def _validate_response_integrity(self, completion: Any) -> None:
        if not hasattr(completion, "choices") or not completion.choices:
            raise OpenRouterEmptyResponseError("モデルから空のchoices応答を受信しました")
        choice = completion.choices[0]
        content = getattr(choice.message, "content", None)
        tool_calls = getattr(choice.message, "tool_calls", None)
        if content is None and not tool_calls:
            raise OpenRouterEmptyResponseError("モデルから空の本文を受信しました")
        if getattr(choice.message, "refusal", None) or choice.finish_reason in ("safety", "sensitive"):
            raise OpenRouterSafetyFilterError("安全フィルタによりモデル応答が拒否されました")
        if choice.finish_reason == "content_filter":
            raise OpenRouterContentFilterError("コンテンツフィルタによりモデル生成が中断されました")
        if choice.finish_reason == "length":
            raise OpenRouterOutputLimitError("最大出力トークン数に達したため生成が打ち切られました")
        if tool_calls:
            validate_tool_calls(tool_calls)

    # チャット応答を取得する
    def complete(
        self, system_prompt: str, user_prompt: str, idempotency_key: str | None = None
    ) -> ModelResponse:
        self._validate_input_limits(user_prompt)
        extra_headers = self._resolve_idempotency_headers(idempotency_key)
        started_at = perf_counter()
        try:
            kwargs: dict[str, Any] = {
                "model": self._settings.model,
                "temperature": self._settings.temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            if extra_headers:
                kwargs["extra_headers"] = extra_headers
            if self._settings.max_output_tokens:
                kwargs["max_tokens"] = self._settings.max_output_tokens
            if self._settings.response_format:
                kwargs["response_format"] = (
                    {"type": "json_object"}
                    if self._settings.response_format == "json_object"
                    else self._settings.response_format
                )

            completion = self._client.chat.completions.create(**kwargs)
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
        except AuthenticationError as error:
            message = f"OpenRouter認証に失敗しました。APIキーを確認してください: {error}"
            raise OpenRouterAuthenticationError(message) from error
        except PermissionDeniedError as error:
            message = f"OpenRouterの利用権限がありません: model={self._settings.model}, error={error}"
            raise OpenRouterPermissionError(message) from error
        except BadRequestError as error:
            err_msg = str(error).lower()
            if "context" in err_msg or "token" in err_msg or "length" in err_msg:
                raise OpenRouterInputLimitError(f"入力上限超過エラー: {error}") from error
            raise OpenRouterBadRequestError(f"リクエスト形式エラー: {error}") from error
        except NotFoundError as error:
            message = f"指定モデルが見つからないか廃止されています: model={self._settings.model}"
            raise OpenRouterNotFoundError(message) from error
        except InternalServerError as error:
            message = f"OpenRouterプロバイダー障害が発生しました: {error}"
            if 500 in self._settings.retryable_status_codes and self._settings.max_retries > 0:
                raise OpenRouterRetryLimitError(f"再試行上限に到達しました: {message}") from error
            raise OpenRouterServerError(message) from error
        except APIStatusError as error:
            if error.status_code == 413:
                raise OpenRouterInputLimitError(f"入力データ上限超過(413): {error}") from error
            if error.status_code in (502, 503, 504):
                message = f"一時的なサービス停止({error.status_code}): {error}"
                if error.status_code in self._settings.retryable_status_codes:
                    raise OpenRouterRetryLimitError(f"再試行上限に到達しました: {message}") from error
                raise OpenRouterServiceUnavailableError(message) from error
            raise OpenRouterError(f"APIステータスエラー({error.status_code}): {error}") from error
        except APIConnectionError as error:
            err_str = str(error).lower()
            if "stream" in err_str or "chunk" in err_str:
                raise OpenRouterStreamDisconnectedError(f"ストリーミング切断エラー: {error}") from error
            raise OpenRouterConnectionError(f"接続エラーが発生しました: {error}") from error

        self._validate_response_integrity(completion)

        duration_ms = (perf_counter() - started_at) * 1000
        usage = getattr(completion, "usage", None)
        cost = _usage_cost(usage)
        if self._settings.max_estimated_cost_usd and cost > self._settings.max_estimated_cost_usd:
            raise OpenRouterCostLimitError(
                f"推定コストが上限を超過しました: {cost} > {self._settings.max_estimated_cost_usd}"
            )

        content = completion.choices[0].message.content or ""
        return ModelResponse(
            content=content,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            estimated_cost_usd=cost,
            duration_ms=duration_ms,
        )


# 利用量から費用を取得する
def _usage_cost(usage: Any) -> float:
    return float(getattr(usage, "cost", 0) or 0) if usage else 0.0


# ツール呼出の形式を検証する
def validate_tool_calls(tool_calls: list[Any]) -> None:
    for call in tool_calls:
        func = getattr(call, "function", None)
        if not func or not getattr(func, "name", None):
            raise OpenRouterToolCallError("ツール呼出に関数名が定義されていません")
        raw_args = getattr(func, "arguments", "")
        try:
            json.loads(raw_args)
        except Exception as error:
            raise OpenRouterToolCallError(f"ツール呼出の引数JSONが不正です: {error}") from error


# JSON形式の応答を検証する
def parse_json_response(
    content: str, schema: dict[str, Any] | None = None
) -> dict[str, Any]:
    normalized = content.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError as error:
        raise OpenRouterInvalidFormatError(f"モデル応答はJSONで返してください: {error}") from error
    if not isinstance(decoded, dict):
        raise OpenRouterInvalidFormatError("モデル応答はJSONオブジェクトで返してください")
    if schema:
        _validate_schema_fields(decoded, schema)
    return decoded


# 期待スキーマの項目を検証する
def _validate_schema_fields(data: dict[str, Any], schema: dict[str, Any]) -> None:
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            raise OpenRouterStructuredOutputError(f"必須フィールドが欠落しています: {field}")
