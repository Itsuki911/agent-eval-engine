# Phase 4 ストリーミング読み込み・事前インデックスの手動単体テスト

## 共通出力形式

`pytest -s`で表示される確認結果は1行JSONである。`test`はテスト名、`result`は`passed`、`streamed_count`・`peak_memory_kb`・`index_load_seconds`などのキーで判定する。

README.md 23行目（Rustシステムプログラミング層）および24行目（ストリーミング読み込み・低メモリ制御）に準拠した動作を手動確認する単体テストケースです。

---

## UT-STREAM-001 データセットのストリーミング読み込みによる低メモリ走査を検証できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase4_streaming_index.py -k test_streaming_benchmark_iterator
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`result`が`passed`、`streamed_count`が`128`と表示される。全件を一度に配列へ保持せずジェネレータ（Iterator）で1件ずつ逐次処理することで、メモリピーク`peak_memory_kb`が500KB未満（実測約90KB）に抑えられ、省メモリ走査が達成されていることを確認できる。

---

## UT-STREAM-002 事前インデックス生成とサブミリ秒での高速読み込みを検証できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase4_streaming_index.py -k test_aot_index_generation_and_loading
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`result`が`passed`、`total_benchmarks`が`281`と表示される。事前インデックス生成後、`index_load_seconds`が0.01秒（10ms）を大幅に下回る1ミリ秒未満（実測約0.3ms）で完了し、従来の6秒台から2万倍以上の高速読み込みを達成していることを確認できる。

---

## UT-STREAM-003 Rustパーサー連携および安全なフォールバックを検証できる（境界値・異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase4_streaming_index.py -k test_rust_parser_bridge_fallback
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 境界値・異常系。`result`が`passed`と表示される。Rustバイナリが未配置の環境下でも例外クラッシュを起こさず、`has_native_rust=false`として自動的に安全なPython/LibYAMLパーサーへフォールバックし、OSの安全境界を守りながら処理を継続できることを確認できる。
