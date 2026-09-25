# Phase 4 評価データセット読み込み性能の手動単体テスト

## 共通出力形式

`pytest -s`で表示される確認結果は1行JSONである。`test`はテスト名、`result`は`passed`、`duration_seconds`・`avg_ms_per_file`・`peak_memory_mb`・`speedup_ratio`などのキーで判定する。下記の期待結果にある表示文は、対応するJSONのキー・値で確認する。

データセット読み込み時間、メモリ消費、スキーマキャッシュによる最適化効果を手動確認する単体テストケースです。

---

## UT-PERF-001 全ベンチマーク読み込み時間とメモリ消費を計測できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase4_perf_dataset.py -k test_load_all_benchmarks_memory_and_time
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`result`が`passed`、`benchmark_count`が`128`と表示される。全件読込の`duration_seconds`（約6秒台）、1ファイルあたりの平均処理時間`avg_ms_per_file`（約40〜60ms）、Pythonプロセスのピークメモリ`peak_memory_mb`（1MB未満）が計測され、I/Oおよびパースのボトルネックが数値で確認できる。

---

## UT-PERF-002 スキーマ事前キャッシュによる高速化倍率を検証できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase4_perf_dataset.py -k test_schema_cache_vs_uncached_comparison
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`result`が`passed`、`iterations`が`50`と表示される。同一スキーマの再読み込みを行う未キャッシュ時（`uncached_seconds`）と、事前コンパイルキャッシュ適用時（`cached_seconds`）の所要時間が比較され、`speedup_ratio`が50倍以上の高速化を達成していることが確認できる。

---

## UT-PERF-003 不正YAML読み込み失敗時にメモリが正常解放される（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase4_perf_dataset.py -k test_malformed_yaml_memory_cleanup
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 異常系。`result`が`passed`と表示される。不正なYAML構文（括弧閉じ忘れ等）を読み込んだ際に`yaml.YAMLError`が適切に発生し、処理失敗後も不要なメモリリークを起こさず`peak_memory_bytes`が500KB未満に抑制される。
