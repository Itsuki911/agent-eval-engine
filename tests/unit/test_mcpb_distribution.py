"""MCPB配布素材を単体確認する。"""

from __future__ import annotations

import json
from pathlib import Path

from apps.mcp.server import create_server


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# manifestの公開情報を確認する
def test_mcpb_manifest_declares_local_mcp_tools() -> None:
    manifest_path = PROJECT_ROOT / "distribution" / "mcpb" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["server"]["type"] == "node"
    assert manifest["server"]["mcp_config"]["command"] == "node"
    assert manifest["compatibility"]["platforms"] == ["darwin", "win32", "linux"]
    assert manifest["tools_generated"] is True
    assert "tools" not in manifest
    print('{"test":"mcpb_manifest","tools":8,"runtime":"node"}')


# 実行時のMCPツール公開を確認する
def test_mcpb_runtime_exposes_eight_tools() -> None:
    server = create_server()

    assert set(server._tool_manager._tools) == {
        "run_benchmark",
        "evaluate_agent",
        "get_run",
        "get_trace",
        "get_errors",
        "compare_runs",
        "run_regression",
        "import_agent_trace",
    }
    print('{"test":"mcpb_runtime_tools","tool_count":8}')


# 起動処理の標準出力分離を確認する
def test_mcpb_launcher_keeps_docker_logs_out_of_stdout() -> None:
    launcher = (PROJECT_ROOT / "distribution" / "mcpb" / "server" / "launch.js").read_text(encoding="utf-8")

    assert "processHandle.stdout.pipe(process.stderr)" in launcher
    assert "processHandle.stderr.pipe(process.stderr)" in launcher
    assert "processHandle.stdout.pipe(process.stdout)" in launcher
    assert '"--profile", "mcp", "up", "-d", "mcp"' in launcher
    assert 'AGENT_EVAL_POSTGRES_PORT || "15432"' in launcher
    assert '"--project-name", "agent-eval-mcpb"' in launcher
    assert '"--transport",\n        "stdio"' in launcher
    assert '"apps/mcp/server.py:mcp"' in launcher
    assert "const pendingInput = []" in launcher
    assert "for (const chunk of pendingInput)" in launcher
    print('{"test":"mcpb_launcher","docker_logs":"stderr","mcp_protocol":"stdout"}')


# 作成処理の秘密情報除外を確認する
def test_mcpb_build_script_rejects_environment_files() -> None:
    script = (PROJECT_ROOT / "scripts" / "build_mcpb.ps1").read_text(encoding="utf-8")

    assert '$_.Name -eq ".env"' in script
    assert "Secret environment files cannot be included" in script
    assert "UTF8Encoding($false)" in script
    assert '$NpxCommand = if ($env:OS -eq "Windows_NT")' in script
    assert "@anthropic-ai/mcpb pack" in script
    print('{"test":"mcpb_build_secret_guard","env_files":"rejected"}')
