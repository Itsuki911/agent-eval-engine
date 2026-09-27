"""実Agent記録Adapterの単体確認を行う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_eval.agent_adapter import AgentExecutionRequest
from agent_eval.real_agent_adapter import (
    JsonlAgentAdapter,
    TranscriptError,
    load_agent_transcript,
    resolve_agent_transcript_path,
)
from tests.output import print_test_result


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "fixtures" / "agent-traces" / "codex-success.jsonl"


# Codex形式の標準記録を読み込む
def test_load_agent_transcript_reads_codex_trace() -> None:
    transcript = load_agent_transcript(FIXTURE)

    assert transcript.adapter_type == "codex"
    assert transcript.benchmark_id == "COD-PY-001"
    assert len(transcript.events) == 3
    assert transcript.task_success is True
    print_test_result("real_agent_trace_load", "passed", adapter_type=transcript.adapter_type, event_count=len(transcript.events))


# 連番でないイベントを拒否する
def test_load_agent_transcript_rejects_non_contiguous_sequence(tmp_path: Path) -> None:
    trace = tmp_path / "invalid.jsonl"
    trace.write_text(
        '\n'.join([
            '{"record_type":"run","adapter_type":"generic","benchmark_id":"GEN-001","agent_name":"agent"}',
            '{"record_type":"event","sequence":1,"event_type":"tool_call","payload":{}}',
            '{"record_type":"result","status":"failed","task_success":false,"exit_code":1,"final_state":{}}',
        ]),
        encoding="utf-8",
    )

    with pytest.raises(TranscriptError, match="sequence"):
        load_agent_transcript(trace)

    print_test_result("real_agent_trace_sequence", "passed", rejected="non_contiguous")


# 秘密情報入り記録を拒否する
def test_load_agent_transcript_rejects_secret_values() -> None:
    trace = PROJECT_ROOT / "fixtures" / "agent-traces" / "invalid-secret.jsonl"

    with pytest.raises(TranscriptError, match="秘密情報"):
        load_agent_transcript(trace)

    print_test_result("real_agent_trace_secret", "passed", secret_stored=False)


# 認証ヘッダー入り記録を拒否する
def test_load_agent_transcript_rejects_authorization_header(tmp_path: Path) -> None:
    trace = tmp_path / "authorization.jsonl"
    trace.write_text(
        '\n'.join([
            '{"record_type":"run","adapter_type":"generic","benchmark_id":"GEN-001","agent_name":"agent"}',
            '{"record_type":"event","sequence":0,"event_type":"tool_call","payload":{"headers":{"Authorization":"hidden"}}}',
            '{"record_type":"result","status":"failed","task_success":false,"exit_code":1,"final_state":{}}',
        ]),
        encoding="utf-8",
    )

    with pytest.raises(TranscriptError, match="秘密情報"):
        load_agent_transcript(trace)

    print_test_result("real_agent_trace_authorization", "passed", secret_stored=False)


# 許可外パスを拒否する
def test_resolve_agent_transcript_path_rejects_parent_path(tmp_path: Path) -> None:
    with pytest.raises(TranscriptError, match="許可フォルダ"):
        resolve_agent_transcript_path(tmp_path, "../outside.jsonl")

    print_test_result("real_agent_trace_path", "passed", rejected="path_traversal")


# Adapterが要求対象を照合する
def test_jsonl_agent_adapter_returns_trace_summary() -> None:
    result = JsonlAgentAdapter().run(
        AgentExecutionRequest("COD-PY-001", "unused", FIXTURE)
    )

    assert result.status == "completed"
    assert result.summary == {"task_success": True, "event_count": 3}
    print_test_result("real_agent_adapter", "passed", status=result.status, event_count=result.summary["event_count"])
