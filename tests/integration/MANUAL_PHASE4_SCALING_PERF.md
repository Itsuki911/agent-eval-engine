# Phase 4 並列パース・スケーラビリティの手動統合テスト

## 共通出力形式

`pytest -s`で表示される確認結果は1行JSONである。`test`はテスト名、`result`は`passed`、`cpu_workers`・`serial_seconds`・`parallel_seconds`・`speedup_ratio`などのキーで判定する。

マルチプロセス並列化によるパース処理のCPUスケーリング効率および並列ワーカー障害隔離を手動確認する統合テストケースです。

---

## IT-PERF-001 マルチプロセス並列化によるCPUスケーリング効率を計測できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase4_perf_scaling.py -k test_parallel_multiprocess_speedup
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`result`が`passed`、`cpu_workers`が利用可能コア数（2〜4）と表示される。直列実行時間（`serial_seconds`）に対してマルチプロセス並列実行時間（`parallel_seconds`）が短縮され、`speedup_ratio`が2.0倍以上の並列化効率を達成していることが確認できる。

---

## IT-PERF-002 並列ワーカー異常時に他ワーカーを巻き込まず例外伝播できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase4_perf_scaling.py -k test_parallel_worker_error_propagation
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 異常系。`result`が`passed`、`error_caught`が`true`と表示される。並列実行タスク群の中に不正なYAMLが含まれていた場合でも、システム全体がデッドロックやクラッシュを起こさず、0.1秒未満で安全に構文例外（`yaml.YAMLError`）をメインプロセスへ伝播できる。
