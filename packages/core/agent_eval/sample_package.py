"""sample評価データセットの配布を扱う。"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


ALLOWED_RELEASE_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}


# ファイルのSHA-256を計算する
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# sample ZIPを作成する
def build_sample_package(project_root: Path, output_path: Path, package_id: str = "phase1-samples-v1") -> Path:
    members: dict[str, str] = {}
    include_roots = (project_root / "benchmarks" / "generic", project_root / "benchmarks" / "coding", project_root / "fixtures")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for include_root in include_roots:
            for source in sorted(path for path in include_root.rglob("*") if path.is_file()):
                relative = source.relative_to(project_root).as_posix()
                archive.write(source, relative)
                members[relative] = sha256_file(source)
        manifest = {"package_id": package_id, "version": 1, "files": members}
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return output_path


# ZIP内パスを安全に検証する
def validate_package_member(name: str) -> None:
    member = Path(name)
    if member.is_absolute() or ".." in member.parts:
        raise ValueError(f"危険なZIPパスを拒否しました: {name}")


# sample ZIPの内容を検証する
def validate_sample_package(package_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(package_path) as archive:
        if "manifest.json" not in archive.namelist():
            raise ValueError("manifest.json がありません")
        manifest = json.loads(archive.read("manifest.json"))
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("manifest の files が不正です")
        for name, expected_hash in files.items():
            validate_package_member(name)
            try:
                content = archive.read(name)
            except KeyError as error:
                raise ValueError(f"manifest にあるファイルがありません: {name}") from error
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f"ファイル整合性が一致しません: {name}")
    return manifest


# sample ZIPをローカルへ展開する
def install_sample_package(package_path: Path, data_root: Path) -> Path:
    manifest = validate_sample_package(package_path)
    package_id = manifest.get("package_id")
    if not isinstance(package_id, str) or not package_id:
        raise ValueError("package_id が不正です")
    target = data_root / "datasets" / "samples" / package_id
    if target.exists():
        raise FileExistsError(f"sample は既に利用可能です: {package_id}")
    data_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=data_root) as temporary:
        staged = Path(temporary) / package_id
        staged.mkdir(parents=True)
        with zipfile.ZipFile(package_path) as archive:
            for name in manifest["files"]:
                validate_package_member(name)
                destination = staged / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
            (staged / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged), str(target))
    return target


# GitHub Releasesからsample ZIPを取得する
def download_sample_package(url: str, output_path: Path, expected_sha256: str) -> Path:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_RELEASE_HOSTS:
        raise ValueError("GitHub Releases の HTTPS URLだけを指定してください")
    if len(expected_sha256) != 64:
        raise ValueError("SHA-256を64文字で指定してください")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as response, output_path.open("wb") as output:
        final_url = urllib.parse.urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname not in ALLOWED_RELEASE_HOSTS:
            raise ValueError("GitHub Releases 以外へのリダイレクトを拒否しました")
        shutil.copyfileobj(response, output)
    if sha256_file(output_path) != expected_sha256.lower():
        output_path.unlink(missing_ok=True)
        raise ValueError("ダウンロードしたsample ZIPのSHA-256が一致しません")
    return output_path
