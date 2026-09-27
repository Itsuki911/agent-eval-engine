"""Phase 7 MCP処理を単体確認する。"""

from __future__ import annotations

import pytest

from apps.mcp.server import EvaluationMCPService, redact_secrets


# 秘密情報を再帰的に伏せる
def test_redact_secrets_masks_nested_values() -> None:
    result = redact_secrets({"token": "hidden", "nested": {"api_key": "hidden", "ok": "visible"}})

    assert result == {"token": "[REDACTED]", "nested": {"api_key": "[REDACTED]", "ok": "visible"}}
    print('{"test":"mcp_redaction","secret_stored":false}')


# live実行を明示許可なしで拒否する
def test_mcp_rejects_live_llm_without_explicit_permission(monkeypatch) -> None:
    # live設定を再現する
    class Settings:
        # エンジン設定を再現する
        class Engine:
            dry_run = False

        engine = Engine()

    service = EvaluationMCPService(load_phase_settings=lambda _: Settings(), migrate_on_first_use=False)
    monkeypatch.delenv("AGENT_EVAL_MCP_ALLOW_LIVE", raising=False)

    with pytest.raises(PermissionError, match="AGENT_EVAL_MCP_ALLOW_LIVE"):
        service._settings()

    print('{"test":"mcp_live_guard","permission":"required"}')


# 回帰評価件数の上限を拒否する
def test_regression_rejects_more_than_ten_benchmarks() -> None:
    service = EvaluationMCPService(migrate_on_first_use=False)

    with pytest.raises(ValueError, match="1件から10件"):
        service.run_regression([f"GEN-{index}" for index in range(11)])

    print('{"test":"mcp_regression_limit","rejected_count":11}')
