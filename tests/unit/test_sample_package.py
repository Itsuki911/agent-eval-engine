"""sample ZIPの作成・検証・展開をテストする。"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from agent_eval.sample_package import build_sample_package, download_sample_package, install_sample_package, validate_sample_package


# sample ZIPの作成と展開を確認する
def test_sample_package_build_validate_and_install(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    package = build_sample_package(root, tmp_path / "samples.zip")

    manifest = validate_sample_package(package)
    installed = install_sample_package(package, tmp_path / "local-data")

    assert manifest["package_id"] == "phase1-samples-v1"
    assert (installed / "benchmarks" / "coding" / "COD-BASH-001.yaml").is_file()
    assert (installed / "fixtures" / "coding" / "bash-workspace-v1" / "fixture.yaml").is_file()
    print(json.dumps({"test": "sample_install", "package_id": manifest["package_id"], "installed": str(installed)}))


# 重複sampleの上書きを拒否する
def test_sample_package_rejects_duplicate_install(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    package = build_sample_package(root, tmp_path / "samples.zip")
    install_sample_package(package, tmp_path / "local-data")

    with pytest.raises(FileExistsError, match="既に利用可能"):
        install_sample_package(package, tmp_path / "local-data")
    print(json.dumps({"test": "sample_duplicate", "rejected": True}))


# 危険なZIPパスを拒否する
def test_sample_package_rejects_path_traversal(tmp_path: Path) -> None:
    package = tmp_path / "unsafe.zip"
    content = b"unsafe"
    manifest = {"package_id": "unsafe", "version": 1, "files": {"../outside.txt": hashlib.sha256(content).hexdigest()}}
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("../outside.txt", content)

    with pytest.raises(ValueError, match="危険なZIPパス"):
        validate_sample_package(package)
    print(json.dumps({"test": "sample_zip_slip", "rejected": True}))


# 改ざんされたsampleを拒否する
def test_sample_package_rejects_tampered_file(tmp_path: Path) -> None:
    package = tmp_path / "tampered.zip"
    manifest = {"package_id": "tampered", "version": 1, "files": {"benchmarks/generic/GEN-X-001.yaml": "0" * 64}}
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("benchmarks/generic/GEN-X-001.yaml", "id: GEN-X-001")

    with pytest.raises(ValueError, match="整合性"):
        validate_sample_package(package)
    print(json.dumps({"test": "sample_hash", "rejected": True}))


# GitHub Releases以外のURLを拒否する
def test_sample_package_rejects_non_release_url(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="GitHub Releases"):
        download_sample_package("https://example.invalid/sample.zip", tmp_path / "sample.zip", "0" * 64)
    print(json.dumps({"test": "sample_url", "rejected": True}))
