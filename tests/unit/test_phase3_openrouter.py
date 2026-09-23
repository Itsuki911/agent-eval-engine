"""Phase 3のOpenRouter接続設定を確認する。"""

import pytest

from agent_eval.agent import OpenRouterAgent
from agent_eval.config import Phase3Settings, load_settings


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
