# 注意点: tracemallocはPythonの内部割当のみ計測するためOS全体常駐メモリ(RSS)とは差分がある
# 代替案: psutilを使用してOSレベルのRSS/VMSメモリやCPU時間を直接監視する選択肢がある
"""データセット読み込み性能とメモリ消費を検証する。"""

from __future__ import annotations

import gc
import json
import time
import tracemalloc
from pathlib import Path

import pytest
import yaml
from agent_eval.benchmark import load_benchmark, load_schema

ROOT = Path(__file__).resolve().parents[2]


# 計測結果を1行JSONで出力する
def print_perf_result(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


# 全ベンチマーク読込の性能を測る
def test_load_all_benchmarks_memory_and_time() -> None:
    schema_path = ROOT / "schemas" / "benchmark.schema.json"
    benchmark_paths = sorted((ROOT / "benchmarks" / "generic").glob("*.yaml"))
    valid_paths = [p for p in benchmark_paths if p.name != "index.yaml"]

    gc.collect()
    tracemalloc.start()
    start_time = time.perf_counter()

    loaded_count = 0
    for path in valid_paths:
        _ = load_benchmark(path, schema_path)
        loaded_count += 1

    duration = time.perf_counter() - start_time
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_mem / (1024 * 1024)
    avg_ms = (duration / loaded_count) * 1000 if loaded_count else 0.0

    print_perf_result({
        "test": "test_load_all_benchmarks_memory_and_time",
        "result": "passed",
        "benchmark_count": loaded_count,
        "duration_seconds": round(duration, 3),
        "avg_ms_per_file": round(avg_ms, 2),
        "peak_memory_mb": round(peak_mb, 2),
    })

    assert loaded_count == len(valid_paths)
    assert duration > 0.0


# スキーマキャッシュの差分を測る
def test_schema_cache_vs_uncached_comparison() -> None:
    schema_path = ROOT / "schemas" / "benchmark.schema.json"
    sample_file = ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml"

    iterations = 50

    start_uncached = time.perf_counter()
    for _ in range(iterations):
        _ = load_benchmark(sample_file, schema_path)
    uncached_duration = time.perf_counter() - start_uncached

    cached_schema = load_schema(schema_path)
    import jsonschema
    validator = jsonschema.Draft202012Validator(cached_schema)

    with sample_file.open(encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    start_cached = time.perf_counter()
    for _ in range(iterations):
        validator.validate(raw_data)
    cached_duration = time.perf_counter() - start_cached

    speedup = uncached_duration / cached_duration if cached_duration > 0 else 1.0

    print_perf_result({
        "test": "test_schema_cache_vs_uncached_comparison",
        "result": "passed",
        "iterations": iterations,
        "uncached_seconds": round(uncached_duration, 4),
        "cached_seconds": round(cached_duration, 4),
        "speedup_ratio": round(speedup, 1),
    })

    assert uncached_duration > 0.0
    assert cached_duration > 0.0


# 不正形式時のメモリ解放を検証する
def test_malformed_yaml_memory_cleanup(tmp_path: Path) -> None:
    schema_path = ROOT / "schemas" / "benchmark.schema.json"
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("invalid_yaml: [unclosed list", encoding="utf-8")

    tracemalloc.start()
    with pytest.raises(yaml.YAMLError):
        _ = load_benchmark(invalid_file, schema_path)

    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print_perf_result({
        "test": "test_malformed_yaml_memory_cleanup",
        "result": "passed",
        "peak_memory_bytes": peak_mem,
    })

    assert peak_mem < 500_000
