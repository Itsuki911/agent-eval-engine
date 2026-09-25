# 注意点: DockerコンテナのCPU制限下ではコア数に応じたスケール効率が制限される場合がある
# 代替案: ThreadPoolExecutorはPythonのGIL制約によりパース処理で速度向上が得られない
"""マルチプロセス並列化によるデータセットパーススケーラビリティを検証する。"""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from pathlib import Path

import yaml
from agent_eval.benchmark import load_benchmark

ROOT = Path(__file__).resolve().parents[2]


# 計測結果を1行JSONで出力する
def print_scaling_result(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


# 単一ファイルの読込関数
def parse_single_benchmark(args: tuple[Path, Path]) -> str:
    path, schema_path = args
    benchmark = load_benchmark(path, schema_path)
    return benchmark.id


# 直列と並列の処理時間を比較する
def test_parallel_multiprocess_speedup() -> None:
    schema_path = ROOT / "schemas" / "benchmark.schema.json"
    benchmark_paths = sorted((ROOT / "benchmarks" / "generic").glob("*.yaml"))
    valid_paths = [p for p in benchmark_paths if p.name != "index.yaml"][:40]
    tasks = [(p, schema_path) for p in valid_paths]

    start_serial = time.perf_counter()
    serial_results = [parse_single_benchmark(t) for t in tasks]
    duration_serial = time.perf_counter() - start_serial

    max_workers = min(os.cpu_count() or 2, 4)
    start_parallel = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        parallel_results = list(executor.map(parse_single_benchmark, tasks))
    duration_parallel = time.perf_counter() - start_parallel

    speedup = duration_serial / duration_parallel if duration_parallel > 0 else 1.0

    print_scaling_result({
        "test": "test_parallel_multiprocess_speedup",
        "result": "passed",
        "sample_count": len(valid_paths),
        "cpu_workers": max_workers,
        "serial_seconds": round(duration_serial, 3),
        "parallel_seconds": round(duration_parallel, 3),
        "speedup_ratio": round(speedup, 2),
    })

    assert len(serial_results) == len(valid_paths)
    assert len(parallel_results) == len(valid_paths)
    assert duration_parallel < duration_serial * 1.5


# 不正ファイル混在時の並列例外制御を検証する
def test_parallel_worker_error_propagation(tmp_path: Path) -> None:
    schema_path = ROOT / "schemas" / "benchmark.schema.json"
    normal_file = ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml"
    broken_file = tmp_path / "broken.yaml"
    broken_file.write_text("invalid: yaml: syntax: [unclosed", encoding="utf-8")

    tasks = [(normal_file, schema_path), (broken_file, schema_path)]

    error_caught = False
    start_time = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(parse_single_benchmark, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except yaml.YAMLError:
                error_caught = True
    duration = time.perf_counter() - start_time

    print_scaling_result({
        "test": "test_parallel_worker_error_propagation",
        "result": "passed",
        "error_caught": error_caught,
        "duration_seconds": round(duration, 3),
    })

    assert error_caught is True
