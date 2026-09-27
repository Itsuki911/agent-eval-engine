"""Phase 10 の CLI バックエンド統合処理を検証する。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# import-trace で外部Agent記録を取り込み、一覧・詳細で参照できることをテストする
def test_cli_backend_import_and_show() -> None:
    trace_file = PROJECT_ROOT / "fixtures" / "agent-traces" / "codex-success.jsonl"
    import_cmd = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "tui_backend.py"),
            "import-trace",
            "--file",
            str(trace_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(import_cmd.stdout)
    assert result["adapter_type"] == "codex"
    run_id = result["run_id"]
    assert run_id

    # show-run で取得できること
    show_cmd = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "tui_backend.py"),
            "show-run",
            "--run-id",
            run_id,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    run_detail = json.loads(show_cmd.stdout)
    assert run_detail["run_id"] == run_id
    assert run_detail["benchmark_id"] == "COD-PY-001"
