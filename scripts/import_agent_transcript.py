"""外部Coding Agentの標準記録をDBへ取り込む。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_eval.real_agent_adapter import TranscriptError, import_agent_transcript
from database.migration import upgrade_database
from database.repositories import RunRepository
from database.session import create_session_factory


# コマンド引数を読み取り取込結果を出力する
def main() -> int:
    parser = argparse.ArgumentParser(description="外部AgentのJSONL記録を取り込みます")
    parser.add_argument("--file", required=True, type=Path, help="agent-eval.trace.v1 JSONLファイル")
    args = parser.parse_args()
    try:
        upgrade_database()
        with create_session_factory()() as session:
            result = import_agent_transcript(RunRepository(session), args.file.resolve())
    except TranscriptError as error:
        print(json.dumps({"status": "rejected", "reason": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
