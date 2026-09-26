# Phase 5: Benchmark Creator 手動テスト

## UT-CREATOR-001 Benchmark IDを入力して保存できる（正常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `c` を押して作成画面を開く。
2. 下矢印で `Benchmark ID` を選ぶ。
3. Enter を押して編集モードにする。
4. Backspace で既存値を消す。
5. `GEN-MANUAL-001` を入力する。
6. Enter を押して編集を確定する。

期待結果: 正常系。編集欄に `GEN-MANUAL-001` が表示され、画面下部に編集・保存の操作案内が残る。

## UT-CREATOR-002 日本語タイトルを入力できる（正常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `c` を押す。
2. `タイトル` を選ぶ。
3. Enter を押す。
4. 日本語のタイトルを入力する。
5. Enter を押す。

期待結果: 正常系。日本語が文字化けせず、1文字ずつではなく入力した文字列としてタイトル欄に表示される。

## UT-CREATOR-003 指示プロンプトを複数行で入力できる（正常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `指示プロンプト` を選ぶ。
2. Enter を押す。
3. 1行目を入力する。
4. Enter を押して改行し、編集を確定する。
5. 下矢印キーを押す。
6. `成功条件` が選択されることを確認する。
7. 上矢印キーを押して `指示プロンプト` に戻る。
8. Enter を押す。
9. 2行目を入力する。
10. Ctrl+S を押して編集を確定する。

期待結果: 正常系。Enter後に画面では改行が `↵` として表示され、編集モードが解除される。続けて上下矢印キーで他項目へ移動できる。保存時に `task.prompt` へ複数行の文字列として渡される。連続して改行を入力したい場合は `Ctrl+N` を使う。

## UT-CREATOR-004 limitsを入力してYAMLへ保存できる（境界値）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `最大ステップ` に `1` を入力する。
2. `制限時間（秒）` に `0.1` を入力する。
3. `最大料金（USD）` に `0` を入力する。
4. `保存と評価開始` を選んで Enter を押す。

期待結果: 境界値。`limits.max_steps=1`、`timeout_seconds=0.1`、`max_estimated_cost_usd=0` を含む YAML が自作保存先へ作成される。

## UT-CREATOR-005 不正な最大ステップを拒否できる（異常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `最大ステップ` に `abc` を入力する。
2. `保存と評価開始` を選んで Enter を押す。

期待結果: 異常系。`最大ステップは整数で入力してください` が表示され、YAML は作成されない。

## UT-CREATOR-006 詳細評価項目をYAMLへ保存できる（正常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `失敗条件`、`ネットワーク`、`タグ`、`必須指標`、`状態` をそれぞれ選択または入力する。
2. `保存と評価開始` を選んで Enter を押す。
3. 保存済み YAML を開く。

期待結果: 正常系。`expected.failure_conditions`、`constraints.network`、`tags`、`evaluation.required_metrics`、`status` が入力内容と一致する。初期値は安全な `network: disabled` と `draft` である。

## UT-CREATOR-007 同じBenchmark IDの上書きを拒否できる（異常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. 一度保存済みの ID を入力する。
2. `保存と評価開始` を選んで Enter を押す。

期待結果: 異常系。既存 YAML は変更されず、同じ ID が保存済みである旨のエラーが表示される。
