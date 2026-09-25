# Phase 4 TUI描画フレーム性能・キー入力遅延の手動E2Eテスト

## 共通出力形式

`go test -v`で表示される確認結果は1行JSONである。`test`はテスト名、`avg_frame_us`・`avg_key_ns`・`alloc_kb`などのキーで判定する。

TUI画面の1フレーム描画時間（FPS維持）、キー入力連打時のイベントループ応答遅延、メモリアロケーションを手動確認するE2Eテストケースです。

---

## E2E-TUI-009 連続画面再描画時の1フレーム描画時間を計測できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --entrypoint "go test -v -run TestTUIFrameRenderLatency ./..." cli
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 正常系。`TestTUIFrameRenderLatency`が`PASS`と表示される。100回の連続画面描画において、1フレームあたりの平均描画時間`avg_frame_us`が16,000マイクロ秒（16ms＝60FPS水準）を大幅に下回る100マイクロ秒未満（約30〜50μs）で完了し、画面のちらつきや引っかかりなく極めて滑らかな描画性能が維持されていることを確認できる。

---

## E2E-TUI-010 高速キー連打時のイベントループ処理遅延を検証できる（境界値）

実行コマンド:

```powershell
docker compose --profile cli run --rm --entrypoint "go test -v -run TestTUIEventLoopKeyLatency ./..." cli
```

1. 実行コマンドを実行する。
2. 標準出力のJSON表示を確認する。

期待結果: 境界値。`TestTUIEventLoopKeyLatency`が`PASS`と表示される。1,000回の連続上下キー入力操作において、1操作あたりの平均処理遅延`avg_key_ns`が1,000,000ナノ秒（1ms）未満のナノ秒単位（約20〜50ns）で完了し、キー連打や連続操作に対してもイベントループが詰まることなく即時応答できることを確認できる。
