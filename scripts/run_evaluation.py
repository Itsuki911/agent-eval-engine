"""評価ワークフローを端末から実行する。"""

from __future__ import annotations

import argparse
import json

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
def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)
    session_factory = create_session_factory()
    with session_factory() as session:
        result = EvaluationService(settings, session).run(args.benchmark)
    print(
        json.dumps(
            {
                "run_id": str(result.run_id),
                "status": result.status,
                "benchmark_id": result.benchmark_id,
                "final_state": result.final_state,
                "event_count": result.event_count,
                "metrics": [metric.__dict__ for metric in result.metrics],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
