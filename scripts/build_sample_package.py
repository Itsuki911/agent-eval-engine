"""GitHub Releases用sample ZIPを作成する。"""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_eval.sample_package import build_sample_package


# パッケージ作成引数を読む
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="sample package builder")
    parser.add_argument("--output", default="dist/phase1-samples-v1.zip")
    parser.add_argument("--package-id", default="phase1-samples-v1")
    return parser.parse_args()


# sample ZIPを生成する
def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    output = build_sample_package(root, root / args.output, args.package_id)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
