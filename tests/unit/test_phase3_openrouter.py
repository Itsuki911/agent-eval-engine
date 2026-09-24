"""Phase 3のOpenRouter接続設定を確認する。"""

import pytest
import httpx2
from openai import APITimeoutError, RateLimitError

from agent_eval.agent import OpenRouterAgent
from agent_eval.config import Phase3Settings, load_settings
from agent_eval.openrouter import (
    OpenRouterClient,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
)


# APIキー未設定の設定を作る
def _live_settings() -> Phase3Settings:
    settings = load_settings("configs/phase3-local.yaml")
    raw_settings = settings.model_dump(mode="json")
    raw_settings["engine"]["dry_run"] = False
    return Phase3Settings.model_validate(raw_settings)


# 仮のAPIキーを拒否する
def test_openrouter_agent_rejects_placeholder_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "replace-with-your-openrouter-api-key")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterAgent(_live_settings())
    print("OpenRouter接続: プレースホルダーを拒否し、クライアントを生成しない")


# OpenRouterタイムアウトを分類する
def test_openrouter_timeout_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_settings("configs/phase3-local.yaml")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = OpenRouterClient(settings.model)

    class TimeoutCompletions:
        # タイムアウトを再現する
        def create(self, **kwargs):
            raise APITimeoutError(request=None)

    client._client.chat.completions = TimeoutCompletions()

    with pytest.raises(OpenRouterTimeoutError, match="max_retries=1"):
        client.complete("system", "user")
    print("OpenRouter接続: タイムアウトを専用例外へ変換")


# OpenRouterレート制限を分類する
def test_openrouter_rate_limit_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_settings("configs/phase3-local.yaml")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = OpenRouterClient(settings.model)

    class RateLimitedCompletions:
        # レート制限を再現する
        def create(self, **kwargs):
            response = httpx2.Response(
                429,
                request=httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
            )
            raise RateLimitError("provider rate limited", response=response, body={})

    client._client.chat.completions = RateLimitedCompletions()

    with pytest.raises(OpenRouterRateLimitError, match="レート制限"):
        client.complete("system", "user")
    print("OpenRouter接続: レート制限を専用例外へ変換")
