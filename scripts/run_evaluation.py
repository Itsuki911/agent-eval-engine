"""評価ワークフローを端末から実行する。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from agent_eval.config import load_settings
from agent_eval.workflow import EvaluationService
from database.session import create_session_factory


# コマンド引数を読み取る
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 3評価エンジン")
    parser.add_argument("--benchmark", required=True, help="評価するbenchmark YAML")
    parser.add_argument("--config", default="configs/phase3-local.yaml", help="設定YAML")
    return parser.parse_args()


# 評価結果をJSONで表示する
def build_result_output(result: Any) -> dict[str, Any]:
    output: dict[str, Any] = {
        "run_id": str(result.run_id),
        "status": result.status,
        "benchmark_id": result.benchmark_id,
        "final_state": result.final_state,
        "event_count": result.event_count,
        "metrics": [metric.__dict__ for metric in result.metrics],
    }
    if result.llm_cost_usd is not None:
        output["llm_cost_usd"] = result.llm_cost_usd
    return output


# 最終結果を標準出力へ1件だけ出す
def print_result_output(result: Any) -> None:
    print(json.dumps(build_result_output(result), ensure_ascii=False))


# 評価処理を端末から開始する
def main() -> None:
    args = parse_args()
    try:
        settings = load_settings(args.config)
        session_factory = create_session_factory()
        with session_factory() as session:
            result = EvaluationService(settings, session).run(args.benchmark)
    except Exception as error:
        error_output = {"status": "failed", "error_type": type(error).__name__}
        print(json.dumps(error_output, ensure_ascii=False), file=sys.stderr)
        raise
    print_result_output(result)


if __name__ == "__main__":
    main()
