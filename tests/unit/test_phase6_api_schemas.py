"""Phase 6 API入力検証を確認する。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.api.schemas import CreateEventRequest, EvaluateRequest


# 評価開始入力の初期値を確認する
def test_evaluate_request_uses_sample_source() -> None:
    request = EvaluateRequest(benchmark_id="GEN-TOOL-001")

    assert request.source == "sample"
    print('{"test":"evaluate_request","source":"sample"}')


# イベント連番の負数を拒否する
def test_event_request_rejects_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        CreateEventRequest(sequence=-1, event_type="tool_call")

    print('{"test":"event_sequence","rejected":"negative"}')
