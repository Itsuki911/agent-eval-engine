"""Go TUI向けのPython実行境界。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from agent_eval.benchmark import load_benchmark
from agent_eval.config import load_settings
from agent_eval.events import CollectedEvent
from agent_eval.workflow import EvaluationResult, EvaluationService
from database.migration import upgrade_database
from database.models import Run
from database.repositories import RunRepository
from database.session import create_session_factory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# TUI用コマンド引数を読む
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TUI backend")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--benchmark", required=True)
    run_parser.add_argument("--config", default="configs/phase3-local.yaml")
    list_parser = subparsers.add_parser("list-runs")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--offset", type=int, default=0)
    show_parser = subparsers.add_parser("show-run")
    show_parser.add_argument("--run-id", required=True)
    show_parser.add_argument("--event-limit", type=int, default=20)
    show_parser.add_argument("--event-offset", type=int, default=0)
    trace_parser = subparsers.add_parser("trace")
    trace_parser.add_argument("--run-id", required=True)
    trace_parser.add_argument("--limit", type=int, default=20)
    trace_parser.add_argument("--offset", type=int, default=0)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--left", required=True)
    compare_parser.add_argument("--right", required=True)
    compare_parser.add_argument("--limit", type=int, default=20)
    compare_parser.add_argument("--offset", type=int, default=0)
    benchmark_parser = subparsers.add_parser("list-benchmarks")
    benchmark_parser.add_argument("--family", choices=("all", "generic", "coding"), default="all")
    benchmark_parser.add_argument("--query", default="")
    benchmark_parser.add_argument("--limit", type=int, default=12)
    benchmark_parser.add_argument("--offset", type=int, default=0)
    return parser.parse_args()


# JSONを標準出力へ1件出す
def print_json(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


# 進捗イベントを標準エラーへ出す
def print_progress(event: CollectedEvent) -> None:
    output = {
        "type": "progress",
        "sequence": event.sequence,
        "event_type": event.event_type,
        "actor": event.actor,
        "status": "recorded",
    }
    if event.error is not None:
        output["error_type"] = event.error.get("type")
    print(json.dumps(output, ensure_ascii=False), file=sys.stderr, flush=True)


# 評価結果をTUI形式へ変換する
def result_output(result: EvaluationResult) -> dict[str, Any]:
    return {
        "run_id": str(result.run_id),
        "status": result.status,
        "benchmark_id": result.benchmark_id,
        "final_state": result.final_state,
        "event_count": result.event_count,
        "llm_cost_usd": result.llm_cost_usd,
        "metrics": [metric.__dict__ for metric in result.metrics],
    }


# 実行一覧の行を作る
def run_summary(run: Run) -> dict[str, Any]:
    return {
        "run_id": str(run.id),
        "benchmark_id": run.benchmark_id,
        "status": run.status,
        "provider": run.provider,
        "model": run.model,
        "llm_cost_usd": float(run.llm_cost_usd) if run.llm_cost_usd is not None else None,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


# 指標を比較用の辞書へ変える
def metric_map(details: dict[str, Any]) -> dict[str, float]:
    return {
        f"{metric['category']}.{metric['name']}": metric["value"]
        for metric in details["metrics"]
    }


# 検索対象のbenchmarkパスを返す
def benchmark_paths(family: str) -> list[Path]:
    families = ("generic", "coding") if family == "all" else (family,)
    return [
        path
        for current_family in families
        for path in sorted((PROJECT_ROOT / "benchmarks" / current_family).glob("*.yaml"))
        if path.name != "index.yaml"
    ]


# 検索語に候補が一致するか調べる
def benchmark_matches(path: Path, query: str) -> bool:
    if not query:
        return True
    if query.casefold() in path.stem.casefold():
        return True
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return query.casefold() in str(raw.get("title", "")).casefold()


# 表示用候補を検証して作る
def benchmark_row(path: Path) -> dict[str, Any]:
    benchmark = load_benchmark(path, PROJECT_ROOT / "schemas" / "benchmark.schema.json")
    return {
        "id": benchmark.id,
        "title": benchmark.title,
        "family": benchmark.family,
        "path": str(path.relative_to(PROJECT_ROOT)),
    }


# benchmark候補をページ単位で取得する
def list_benchmarks(
    family: str = "all",
    query: str = "",
    limit: int = 12,
    offset: int = 0,
) -> dict[str, Any]:
    page_limit = min(max(limit, 1), 50)
    page_offset = max(offset, 0)
    matched_paths = [path for path in benchmark_paths(family) if benchmark_matches(path, query)]
    page_paths = matched_paths[page_offset : page_offset + page_limit]
    return {
        "benchmarks": [benchmark_row(path) for path in page_paths],
        "total": len(matched_paths),
        "offset": page_offset,
        "limit": page_limit,
    }


# DB関連コマンドを実行する
def execute_database_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "migrate":
        return {"status": "upgraded", "revision": upgrade_database()}
    session_factory = create_session_factory()
    with session_factory() as session:
        repository = RunRepository(session)
        if args.command == "list-runs":
            return {
                "runs": [run_summary(run) for run in repository.list_runs(args.limit, args.offset)],
                "total": repository.count_runs(),
                "offset": max(args.offset, 0),
                "limit": min(max(args.limit, 1), 100),
            }
        if args.command == "show-run":
            return repository.get_run_details(UUID(args.run_id), args.event_limit, args.event_offset)
        if args.command == "trace":
            details = repository.get_run_details(UUID(args.run_id), args.limit, args.offset)
            return {
                "run_id": details["run_id"],
                "events": details["events"],
                "total": details["event_total"],
                "offset": details["event_offset"],
                "limit": details["event_limit"],
            }
        if args.command == "compare":
            left = repository.get_run_details(UUID(args.left))
            right = repository.get_run_details(UUID(args.right))
            left_metrics = metric_map(left)
            right_metrics = metric_map(right)
            names = sorted(set(left_metrics) | set(right_metrics))
            page_limit = min(max(args.limit, 1), 100)
            page_offset = max(args.offset, 0)
            page_names = names[page_offset : page_offset + page_limit]
            return {
                "left_run_id": left["run_id"],
                "right_run_id": right["run_id"],
                "total": len(names),
                "offset": page_offset,
                "limit": page_limit,
                "metrics": [
                    {
                        "name": name,
                        "left": left_metrics.get(name),
                        "right": right_metrics.get(name),
                        "difference": right_metrics.get(name, 0) - left_metrics.get(name, 0),
                    }
                    for name in page_names
                ],
            }
    raise ValueError(f"unsupported command: {args.command}")


# 評価実行を開始する
def execute_run(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings(args.config)
    session_factory = create_session_factory()
    with session_factory() as session:
        result = EvaluationService(settings, session, event_listener=print_progress).run(args.benchmark)
    return result_output(result)


# TUI境界を開始する
def main() -> int:
    args = parse_args()
    try:
        if args.command == "run":
            output = execute_run(args)
        elif args.command == "list-benchmarks":
            output = list_benchmarks(args.family, args.query, args.limit, args.offset)
        else:
            output = execute_database_command(args)
    except Exception as error:
        print(
            json.dumps({"type": "error", "error_type": type(error).__name__}),
            file=sys.stderr,
            flush=True,
        )
        return 1
    print_json(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
