"""Phase 10 のインストーラー仕様およびリリース設定を単体テストする。"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# install.ps1 が存在し、安全な設計であることを確認する
def test_installer_script_structure() -> None:
    installer = PROJECT_ROOT / "scripts" / "install.ps1"
    assert installer.exists()
    content = installer.read_text(encoding="utf-8")

    # 必須パラメータ・検査ロジックの確認
    assert "SHA256" in content
    assert "AgentEval" in content
    assert "LOCALAPPDATA" in content
    assert "checksums.txt" in content
    assert "Get-FileHash" in content


# リリース成果物の命名とクロスコンパイル対象を確認する
def test_release_matrix_specification() -> None:
    workflow = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    assert workflow.exists()
    content = workflow.read_text(encoding="utf-8")

    for target in ("windows_amd64", "windows_arm64", "darwin_amd64", "darwin_arm64", "linux_amd64"):
        assert target in content
    assert "checksums.txt" in content
    assert "sbom" in content
