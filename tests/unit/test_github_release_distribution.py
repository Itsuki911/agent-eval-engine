"""GitHub Releases向けMCPB配布設定を確認する。"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# tag公開用workflowを確認する
def test_release_workflow_builds_and_uploads_mcpb() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "release-mcpb.yml").read_text(encoding="utf-8")

    assert 'tags:\n      - "v*"' in workflow
    assert "scripts\\build_mcpb.ps1 -Version $version" in workflow
    assert "agent-eval-engine.mcpb.sha256" in workflow
    assert "gh release create" in workflow
    assert "contents: write" in workflow
    print('{"test":"github_release_mcpb_workflow","result":"passed","asset_count":2}')


# 配布手順に検証工程があることを確認する
def test_release_document_requires_checksum_verification() -> None:
    document = (PROJECT_ROOT / "docs" / "GITHUB_RELEASE_DISTRIBUTION.md").read_text(encoding="utf-8")

    assert "Get-FileHash -Algorithm SHA256" in document
    assert "mcpb info" in document
    assert "未署名" in document
    print('{"test":"github_release_mcpb_document","result":"passed","checksum":"required"}')
