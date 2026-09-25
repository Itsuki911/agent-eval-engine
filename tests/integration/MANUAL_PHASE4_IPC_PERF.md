# Phase 4 プロセス間通信(IPC)性能の手動統合テスト

## 共通出力形式

`pytest -s`で表示される確認結果は1行JSONである。`test`はテスト名、`result`は`passed`、`event_count`・`total_bytes`・`duration_seconds`・`throughput_mb_s`などのキーで判定する。

Go TUIとPython評価エンジンのプロセス境界におけるTraceイベント転送速度および大容量ペイロード耐性を手動確認する統合テストケースです。

---

## IT-IPC-001 1000件のTraceイベント転送スループットを計測できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase4_perf_ipc.py -k test_ipc_event_stream_throughput
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`result`が`passed`、`event_count`が`1000`と表示される。約200KB（`total_bytes`）のJSON Linesイベントストリームが0.01秒未満（`duration_seconds`）で生成され、`throughput_mb_s`が50MB/s以上の高速転送性能を達成していることが確認できる。

---

## IT-IPC-002 1MB規模の巨大ペイロード転送時の境界値を検証できる（境界値）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase4_perf_ipc.py -k test_ipc_large_payload_boundary
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 境界値。`result`が`passed`、`payload_bytes`が`1048576`（1MB）と表示される。ツール実行の巨大な出力結果（コード差分やファイル全体内容）をJSONシリアライズ・デシリアライズする際にも、0.01秒未満で遅延なく処理でき、メモリオーバーフローや破損を起こさないことが確認できる。
