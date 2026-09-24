# 注意点: OpenRouter固有のHTTPステータス差異がある
# 選択肢: httpxモックの代わりにrespxライブラリも利用可能
"""Phase 3のOpenRouter接続設定と例外処理を確認する。"""

from types import SimpleNamespace
from typing import Any
import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from agent_eval.agent import OpenRouterAgent
from agent_eval.benchmark import load_benchmark
from agent_eval.config import Phase3Settings, load_settings
from agent_eval.events import EventCollector
from agent_eval.openrouter import (
    OpenRouterAuthenticationError,
    OpenRouterBadRequestError,
    OpenRouterConnectionError,
    OpenRouterContentFilterError,
    OpenRouterCostLimitError,
    OpenRouterEmptyResponseError,
    OpenRouterIdempotencyError,
    OpenRouterInputLimitError,
    OpenRouterInvalidFormatError,
    OpenRouterNotFoundError,
    OpenRouterOutputLimitError,
    OpenRouterPermissionError,
    OpenRouterRateLimitError,
    OpenRouterRetryLimitError,
    OpenRouterSafetyFilterError,
    OpenRouterServerError,
    OpenRouterServiceUnavailableError,
    OpenRouterStreamDisconnectedError,
    OpenRouterStructuredOutputError,
    OpenRouterTimeoutError,
    OpenRouterToolCallError,
    OpenRouterClient,
    ModelResponse,
    parse_json_response,
)
from agent_eval.telemetry import create_telemetry
from tests.output import print_test_result


# APIキー未設定の設定を作る
def _live_settings() -> Phase3Settings:
    settings = load_settings("configs/phase3-local.yaml")
    raw_settings = settings.model_dump(mode="json")
    raw_settings["engine"]["dry_run"] = False
    return Phase3Settings.model_validate(raw_settings)


# テスト用クライアントを作る
def _make_client(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> OpenRouterClient:
    settings = load_settings("configs/phase3-local.yaml")
    raw = settings.model_dump(mode="json")
    raw["model"].update(overrides)
    valid_settings = Phase3Settings.model_validate(raw)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    return OpenRouterClient(valid_settings.model)


# OpenRouter確認結果をJSONで表示する
def _print_openrouter_result(test: str, **values: Any) -> None:
    print_test_result(test, "passed", **values)


# 仮のAPIキーを拒否する
def test_openrouter_agent_rejects_placeholder_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "replace-with-your-openrouter-api-key")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterAgent(_live_settings())
    _print_openrouter_result(
        "openrouter_agent_rejects_placeholder_key",
        rejected_reason="placeholder_api_key",
        external_request_started=False,
    )


# OpenRouterタイムアウトを分類する
def test_openrouter_timeout_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, max_retries=0)

    class TimeoutCompletions:
        # タイムアウトを再現する
        def create(self, **kwargs):
            raise APITimeoutError(request=None)

    client._client.chat.completions = TimeoutCompletions()

    with pytest.raises(OpenRouterTimeoutError, match="max_retries=0"):
        client.complete("system", "user")
    _print_openrouter_result(
        "openrouter_timeout_is_converted",
        model=client._settings.model,
        error_category="timeout",
        max_retries=0,
    )


# OpenRouterレート制限を分類する
def test_openrouter_rate_limit_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, max_retries=0)

    class RateLimitedCompletions:
        # レート制限を再現する
        def create(self, **kwargs):
            response = httpx.Response(
                429,
                request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
            )
            raise RateLimitError("provider rate limited", response=response, body={})

    client._client.chat.completions = RateLimitedCompletions()

    with pytest.raises(OpenRouterRateLimitError, match="レート制限"):
        client.complete("system", "user")
    _print_openrouter_result(
        "openrouter_rate_limit_is_converted",
        model=client._settings.model,
        error_category="rate_limit",
        status_code=429,
    )


# 認証失敗の変換を確認する
def test_openrouter_auth_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class AuthFailedCompletions:
        # 認証エラーを再現する
        def create(self, **kwargs):
            response = httpx.Response(401, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise AuthenticationError("invalid api key", response=response, body={})

    client._client.chat.completions = AuthFailedCompletions()

    with pytest.raises(OpenRouterAuthenticationError, match="認証に失敗"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_auth_error_is_converted", error_category="auth", status_code=401)


# 認可不足の変換を確認する
def test_openrouter_permission_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class ForbiddenCompletions:
        # 権限不足を再現する
        def create(self, **kwargs):
            response = httpx.Response(403, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise PermissionDeniedError("forbidden model access", response=response, body={})

    client._client.chat.completions = ForbiddenCompletions()

    with pytest.raises(OpenRouterPermissionError, match="利用権限がありません"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_permission_error_is_converted", error_category="permission", status_code=403)


# 不正リクエストの変換を確認
def test_openrouter_bad_request_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class BadRequestCompletions:
        # 不正リクエストを再現する
        def create(self, **kwargs):
            response = httpx.Response(400, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise BadRequestError("invalid messages structure", response=response, body={})

    client._client.chat.completions = BadRequestCompletions()

    with pytest.raises(OpenRouterBadRequestError, match="リクエスト形式エラー"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_bad_request_error_is_converted", error_category="bad_request", status_code=400)


# 入力文字数上限超過を確認
def test_openrouter_input_limit_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, max_prompt_chars=50)

    long_prompt = "a" * 100
    with pytest.raises(OpenRouterInputLimitError, match="上限を超過しました"):
        client.complete("system", long_prompt)
    _print_openrouter_result("openrouter_input_limit_error_is_converted", error_category="input_limit", external_request_started=False)


# 出力上限打ち切りを検出
def test_openrouter_output_limit_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class LengthFinishCompletions:
        # 出力上限打ち切りを再現
        def create(self, **kwargs):
            msg = SimpleNamespace(content="truncated answer", refusal=None)
            choice = SimpleNamespace(message=msg, finish_reason="length")
            return SimpleNamespace(choices=[choice], usage=None)

    client._client.chat.completions = LengthFinishCompletions()

    with pytest.raises(OpenRouterOutputLimitError, match="最大出力トークン数"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_output_limit_error_is_converted", error_category="output_limit", finish_reason="length")


# モデル未発見の変換を確認
def test_openrouter_not_found_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class NotFoundCompletions:
        # モデル未発見を再現する
        def create(self, **kwargs):
            response = httpx.Response(404, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise NotFoundError("model not found", response=response, body={})

    client._client.chat.completions = NotFoundCompletions()

    with pytest.raises(OpenRouterNotFoundError, match="見つからないか廃止"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_not_found_error_is_converted", error_category="not_found", status_code=404)


# プロバイダー障害の変換を確認
def test_openrouter_server_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, retryable_status_codes=[])

    class ServerErrorCompletions:
        # 内部エラーを再現する
        def create(self, **kwargs):
            response = httpx.Response(500, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise InternalServerError("internal server error", response=response, body={})

    client._client.chat.completions = ServerErrorCompletions()

    with pytest.raises(OpenRouterServerError, match="プロバイダー障害"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_server_error_is_converted", error_category="server_error", status_code=500)


# サービス停止の変換を確認
def test_openrouter_service_unavailable_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, retryable_status_codes=[])

    class ServiceUnavailableCompletions:
        # サービス停止を再現する
        def create(self, **kwargs):
            response = httpx.Response(503, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise APIStatusError("service unavailable", response=response, body={})

    client._client.chat.completions = ServiceUnavailableCompletions()

    with pytest.raises(OpenRouterServiceUnavailableError, match="一時的なサービス停止"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_service_unavailable_error_is_converted", error_category="service_unavailable", status_code=503)


# 接続障害の変換を確認する
def test_openrouter_connection_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, max_retries=0)

    class ConnectionFailCompletions:
        # 接続切断を再現する
        def create(self, **kwargs):
            raise APIConnectionError(request=None, message="dns resolution failed")

    client._client.chat.completions = ConnectionFailCompletions()

    with pytest.raises(OpenRouterConnectionError, match="接続エラー"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_connection_error_is_converted", error_category="connection")


# ストリーム切断の変換を確認
def test_openrouter_stream_disconnected_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, max_retries=0)

    class StreamInterruptedCompletions:
        # ストリーム切断を再現する
        def create(self, **kwargs):
            raise APIConnectionError(request=None, message="stream chunk interrupted")

    client._client.chat.completions = StreamInterruptedCompletions()

    with pytest.raises(OpenRouterStreamDisconnectedError, match="ストリーミング切断"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_stream_disconnected_error_is_converted", error_category="stream_disconnected")


# 不正JSON形式の変換を確認
def test_openrouter_invalid_format_error_is_converted() -> None:
    with pytest.raises(OpenRouterInvalidFormatError, match="JSON"):
        parse_json_response("This is not a JSON string")
    _print_openrouter_result("openrouter_invalid_format_error_is_converted", error_category="invalid_format")


# 空応答の検出を確認する
def test_openrouter_empty_response_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class EmptyChoiceCompletions:
        # 空のchoicesを再現する
        def create(self, **kwargs):
            return SimpleNamespace(choices=[])

    client._client.chat.completions = EmptyChoiceCompletions()

    with pytest.raises(OpenRouterEmptyResponseError, match="空のchoices"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_empty_response_error_is_converted", error_category="empty_response")


# 安全フィルタ拒否を検出
def test_openrouter_safety_filter_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class SafetyRejectCompletions:
        # 安全フィルタ拒否を再現
        def create(self, **kwargs):
            msg = SimpleNamespace(content="refused", refusal="policy_violation")
            choice = SimpleNamespace(message=msg, finish_reason="safety")
            return SimpleNamespace(choices=[choice], usage=None)

    client._client.chat.completions = SafetyRejectCompletions()

    with pytest.raises(OpenRouterSafetyFilterError, match="安全フィルタ"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_safety_filter_error_is_converted", error_category="safety_filter")


# コンテンツフィルタ停止を検出
def test_openrouter_content_filter_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class ContentFilterCompletions:
        # コンテンツフィルタを再現
        def create(self, **kwargs):
            msg = SimpleNamespace(content="partial content", refusal=None)
            choice = SimpleNamespace(message=msg, finish_reason="content_filter")
            return SimpleNamespace(choices=[choice], usage=None)

    client._client.chat.completions = ContentFilterCompletions()

    with pytest.raises(OpenRouterContentFilterError, match="コンテンツフィルタ"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_content_filter_error_is_converted", error_category="content_filter")


# ツール呼出形式不正を検出
def test_openrouter_tool_call_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class BrokenToolCallCompletions:
        # 不正な引数を再現する
        def create(self, **kwargs):
            func = SimpleNamespace(name="search", arguments="{broken-json")
            tool_call = SimpleNamespace(function=func)
            msg = SimpleNamespace(content="", refusal=None, tool_calls=[tool_call])
            choice = SimpleNamespace(message=msg, finish_reason="stop")
            return SimpleNamespace(choices=[choice], usage=None)

    client._client.chat.completions = BrokenToolCallCompletions()

    with pytest.raises(OpenRouterToolCallError, match="引数JSONが不正"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_tool_call_error_is_converted", error_category="tool_call")


# 構造化出力の検証失敗を確認
def test_openrouter_structured_output_error_is_converted() -> None:
    schema = {"required": ["success", "final_answer"]}
    invalid_data = '{"success": true}'
    with pytest.raises(OpenRouterStructuredOutputError, match="必須フィールドが欠落"):
        parse_json_response(invalid_data, schema=schema)
    _print_openrouter_result("openrouter_structured_output_error_is_converted", error_category="structured_output")


# コスト上限超過の検出を確認
def test_openrouter_cost_limit_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, max_estimated_cost_usd=0.05)

    class ExpensiveCompletions:
        # 高額課金を再現する
        def create(self, **kwargs):
            msg = SimpleNamespace(content='{"success": true, "final_answer": "ok"}', refusal=None)
            choice = SimpleNamespace(message=msg, finish_reason="stop")
            usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, cost=0.20)
            return SimpleNamespace(choices=[choice], usage=usage)

    client._client.chat.completions = ExpensiveCompletions()

    with pytest.raises(OpenRouterCostLimitError, match="推定コストが上限を超過"):
        client.complete("system", "user")
    _print_openrouter_result("openrouter_cost_limit_error_is_converted", error_category="cost_limit", estimated_cost_usd=0.20, max_estimated_cost_usd=0.05)


# 実行単位のコスト上限を確認する
def test_openrouter_run_cost_limit_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _live_settings()
    raw_settings = settings.model_dump(mode="json")
    raw_settings["model"]["max_estimated_cost_usd"] = 0.30
    raw_settings["model"]["max_cost_per_run_usd"] = 0.10
    limited_settings = Phase3Settings.model_validate(raw_settings)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    agent = OpenRouterAgent(limited_settings)
    agent._client.complete = lambda *args: ModelResponse(
        content='{"success": true, "final_answer": "done"}',
        input_tokens=100,
        output_tokens=50,
        estimated_cost_usd=0.20,
        duration_ms=10,
    )
    telemetry = create_telemetry(limited_settings.telemetry)
    collector = EventCollector(telemetry.tracer)
    benchmark = load_benchmark("benchmarks/generic/GEN-TOOL-001.yaml", "schemas/benchmark.schema.json")

    with pytest.raises(OpenRouterCostLimitError, match="実行コストが上限を超過"):
        agent.run(benchmark, collector)

    assert collector.events()[0].payload["estimated_cost_usd"] == 0.20
    _print_openrouter_result("openrouter_run_cost_limit_is_enforced", error_category="cost_limit", llm_cost_usd=0.20, max_cost_per_run_usd=0.10)


# リトライ上限超過の検出を確認
def test_openrouter_retry_limit_error_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(
        monkeypatch,
        max_retries=1,
        retryable_status_codes=[500],
        retry_backoff_initial_seconds=0,
        retry_jitter=0,
    )
    call_count = 0

    class ExhaustedRetryCompletions:
        # 再試行上限到達を再現
        def create(self, **kwargs):
            nonlocal call_count
            call_count += 1
            response = httpx.Response(500, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))
            raise InternalServerError("server error after retries", response=response, body={})

    client._client.chat.completions = ExhaustedRetryCompletions()

    with pytest.raises(OpenRouterRetryLimitError, match="再試行上限に到達"):
        client.complete("system", "user")
    assert call_count == 2
    _print_openrouter_result("openrouter_retry_limit_error_is_converted", error_category="retry_limit", status_code=500, call_count=call_count)


# Retry-Afterを優先して再試行する
def test_openrouter_rate_limit_retries_after_header(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(
        monkeypatch,
        max_retries=1,
        retryable_status_codes=[429],
        retry_backoff_initial_seconds=0,
        retry_jitter=0,
    )
    call_count = 0
    sleeps: list[float] = []

    class RecoveringCompletions:
        # 429後に正常応答を返す
        def create(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = httpx.Response(
                    429,
                    headers={"Retry-After": "2"},
                    request=httpx.Request("POST", "https://openrouter.ai/api/v1"),
                )
                raise RateLimitError("provider rate limited", response=response, body={})
            msg = SimpleNamespace(content='{"success": true, "final_answer": "done"}', refusal=None)
            choice = SimpleNamespace(message=msg, finish_reason="stop")
            return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr("agent_eval.openrouter.sleep", sleeps.append)
    client._client.chat.completions = RecoveringCompletions()

    response = client.complete("system", "user")

    assert response.retry_count == 1
    assert call_count == 2
    assert sleeps == [2.0]
    _print_openrouter_result("openrouter_rate_limit_retries_after_header", model=client._settings.model, status_code=429, retry_after_seconds=2, retry_count=response.retry_count)


# 冪等性モードの動作を確認
def test_openrouter_idempotency_key_is_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, idempotency_key_mode="per_request")
    headers = client._resolve_idempotency_headers("custom-key-123")
    assert headers["X-Idempotency-Key"] == "custom-key-123"

    invalid_client = _make_client(monkeypatch, idempotency_key_mode="none")
    assert invalid_client._resolve_idempotency_headers() == {}

    _print_openrouter_result("openrouter_idempotency_key_is_resolved", idempotency_key_mode="per_request", header_name="X-Idempotency-Key")


# 正常応答の取得を確認する
def test_openrouter_normal_response_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    class NormalCompletions:
        # 正常な応答を返す
        def create(self, **kwargs):
            assert "X-Idempotency-Key" in kwargs.get("extra_headers", {})
            msg = SimpleNamespace(content='{"success": true, "final_answer": "done"}', refusal=None)
            choice = SimpleNamespace(message=msg, finish_reason="stop")
            usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20, cost=0.001)
            return SimpleNamespace(choices=[choice], usage=usage)

    client._client.chat.completions = NormalCompletions()

    resp = client.complete("system", "user", idempotency_key="req-001")
    assert resp.content == '{"success": true, "final_answer": "done"}'
    assert resp.input_tokens == 10
    assert resp.output_tokens == 20
    assert resp.estimated_cost_usd == 0.001
    assert resp.retry_count == 0
    _print_openrouter_result(
        "openrouter_normal_response_succeeds",
        model=client._settings.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        llm_cost_usd=resp.estimated_cost_usd,
        retry_count=resp.retry_count,
    )
