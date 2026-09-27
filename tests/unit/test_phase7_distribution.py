"""Phase 7 の配布設定を単体確認する。"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# 公開資料の対応Hostを確認する
def test_mcp_client_guide_covers_local_stdio_hosts() -> None:
    guide = (PROJECT_ROOT / "docs" / "MCP_CLIENT_SETUP.md").read_text(encoding="utf-8")

    for host in ("Codex", "OpenCode", "Antigravity", "VS Code"):
        assert host in guide
    assert "stdio" in guide
    assert "AGENT_EVAL_MCP_ALLOW_LIVE=1" in guide
    print('{"test":"mcp_client_guide","hosts":4,"transport":"stdio"}')


# 公開準備資料の実行境界を確認する
def test_smithery_guide_keeps_runtime_local() -> None:
    guide = (PROJECT_ROOT / "docs" / "SMITHERY_PUBLISHING.md").read_text(encoding="utf-8")

    assert "ローカル Docker" in guide
    assert "hosted_shttp" in guide
    assert "API キー" in guide
    assert "stdio" in guide
    print('{"test":"smithery_runtime_boundary","runtime":"local","deployment":"stdio"}')


# Compose設定の外部MCP公開を防ぐ
def test_mcp_compose_service_has_no_published_port() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    start = compose.index("  mcp:\n")
    end = compose.index("\n  # Go CLI/TUIモック用", start)
    mcp_service = compose[start:end]

    assert 'profiles: ["mcp"]' in mcp_service
    assert "ports:" not in mcp_service
    assert "stdin_open: true" in mcp_service
    assert "AGENT_EVAL_MCP_ALLOW_LIVE" in mcp_service
    print('{"test":"mcp_compose_boundary","published_ports":0,"live_guard":true}')
