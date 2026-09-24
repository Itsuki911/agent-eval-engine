"""OpenRouterクライアントの実通信を確認する。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_eval.config import load_settings
from agent_eval.openrouter import OpenRouterClient, parse_json_response
from tests.output import print_test_result


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# OpenRouter応答と利用量を確認する
@pytest.mark.live
def test_openrouter_live_client_returns_structured_response() -> None:
    if os.getenv("RUN_LIVE_OPENROUTER_UNIT") != "1":
        pytest.skip("RUN_LIVE_OPENROUTER_UNIT=1 を指定してください")
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY を設定してください")

    settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
    print_test_result(
        "openrouter_live_client_returns_structured_response",
        "configured",
        model=settings.model.model,
    )
    response = OpenRouterClient(settings.model).complete(
        "Return only JSON with success (boolean) and final_answer (string).",
        "Return a successful short response for this connectivity test.",
    )
    parsed = parse_json_response(response.content)
    print_test_result(
        "openrouter_live_client_returns_structured_response",
        "passed",
        model=settings.model.model,
        success=parsed["success"],
        answer=parsed["final_answer"],
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        llm_cost_usd=response.estimated_cost_usd,
        duration_ms=round(response.duration_ms),
    )

    assert isinstance(parsed["success"], bool)
    assert isinstance(parsed["final_answer"], str)
    assert parsed["final_answer"]
    assert response.duration_ms > 0
