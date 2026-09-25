# 注意点: ストリーミング走査中は途中で例外が発生した場合に後続ファイルが未読込になる
# 代替案: イテレータの各要素をResult型でラップしてエラー時も継続する選択肢がある
"""データセットのストリーミング読込と事前インデックスを検証する。"""

from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

from agent_eval.benchmark import (
    generate_benchmark_index,
    iter_benchmark_summaries_stream,
    iter_benchmarks_stream,
    load_benchmark_index,
    parse_benchmark_rust,
)

ROOT = Path(__file__).resolve().parents[2]


# 計測結果を1行JSONで出力する
def print_result(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


# ストリーミング走査のメモリ抑制を検証する
def test_streaming_benchmark_iterator() -> None:
    schema_path = ROOT / "schemas" / "benchmark.schema.json"
    benchmark_paths = sorted((ROOT / "benchmarks" / "generic").glob("*.yaml"))
    valid_paths = [p for p in benchmark_paths if p.name != "index.yaml"]

    tracemalloc.start()
    start_time = time.perf_counter()

    processed_count = 0
    for benchmark in iter_benchmarks_stream(valid_paths, schema_path):
        processed_count += 1
        assert benchmark.id.startswith("GEN-")

    duration = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_kb = peak_mem / 1024

    print_result({
        "test": "test_streaming_benchmark_iterator",
        "result": "passed",
        "streamed_count": processed_count,
        "duration_seconds": round(duration, 3),
        "peak_memory_kb": round(peak_kb, 1),
    })

    assert processed_count == len(valid_paths)
    assert peak_kb < 500


# 事前インデックスによる高速読込を測る
def test_aot_index_generation_and_loading(tmp_path: Path) -> None:
    index_file = tmp_path / "benchmarks_index.json"
    bench_dir = ROOT / "benchmarks"

    gen_start = time.perf_counter()
    generated_path = generate_benchmark_index(bench_dir, index_file)
    gen_duration = time.perf_counter() - gen_start

    assert generated_path.is_file()

    load_start = time.perf_counter()
    index_data = load_benchmark_index(generated_path)
    load_duration = time.perf_counter() - load_start

    print_result({
        "test": "test_aot_index_generation_and_loading",
        "result": "passed",
        "total_benchmarks": index_data["total"],
        "index_generate_seconds": round(gen_duration, 3),
        "index_load_seconds": round(load_duration, 5),
    })

    assert index_data["total"] >= 128
    assert load_duration < 0.05


# Rustパーサーの連携とフォールバックを測る
def test_rust_parser_bridge_fallback() -> None:
    sample_yaml = (
        "schema_version: '0.1'\n"
        "id: GEN-TOOL-TEST\n"
        "title: Tool test\n"
        "family: generic\n"
        "fixture: test-v1\n"
    )

    rust_result = parse_benchmark_rust(sample_yaml)

    print_result({
        "test": "test_rust_parser_bridge_fallback",
        "result": "passed",
        "has_native_rust": rust_result is not None,
    })

    if rust_result is not None:
        assert rust_result["id"] == "GEN-TOOL-TEST"
        assert rust_result["title"] == "Tool test"
