"""Phase 10 の CLI バックエンド拡張および配布設定を単体テストする。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# scripts/tui_backend.py validate-trace の正常系をテストする
def test_tui_backend_validate_trace_valid() -> None:
    trace_file = PROJECT_ROOT / "fixtures" / "agent-traces" / "codex-success.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "tui_backend.py"),
            "validate-trace",
            "--file",
            str(trace_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "valid"
    assert data["adapter_type"] == "codex"
    assert data["event_count"] >= 1
    assert data["task_success"] is True


# scripts/tui_backend.py validate-trace の秘密情報拒否をテストする
def test_tui_backend_validate_trace_rejects_secret(tmp_path: Path) -> None:
    bad_trace = tmp_path / "bad.jsonl"
    bad_trace.write_text(
        '{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-001","agent_name":"agent"}\n'
        '{"record_type":"event","sequence":0,"event_type":"tool_call","payload":{"api_key":"secret-token"}}\n'
        '{"record_type":"result","status":"completed","task_success":true}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "tui_backend.py"),
            "validate-trace",
            "--file",
            str(bad_trace),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "秘密情報" in result.stderr or "秘密情報" in result.stdout


# scripts/tui_backend.py doctor の診断出力をテストする
def test_tui_backend_doctor() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "tui_backend.py"),
            "doctor",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "database" in data
    assert "migrations" in data
    assert "storage" in data
