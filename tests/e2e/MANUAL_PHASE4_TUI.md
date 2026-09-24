# Phase 4 CLI/TUIモックの手動E2Eテスト

## E2E-TUI-001 実行一覧を表示して主要情報を確認できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli --screen runs --no-clear
```

1. 実行コマンドを実行する。
2. Runs画面の表見出しを確認する。
3. 操作一覧を確認する。

期待結果: 正常系。`EVALUATION RESULTS`と3件の実行履歴が表示される。各実行はbenchmark、状態、実行日時、モデル、料金、時間を2行で確認できる。`completed`、`failed`、`simulated`の3状態が、記号と文字で区別できる。選択中の実行は青い背景で表示される。下部に詳細・Trace・戻る・終了の操作が表示される。

## E2E-TUI-002 時系列traceでLLM判断情報を確認できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli --screen trace --no-clear
```

1. 実行コマンドを実行する。
2. イベントがsequence順に並ぶことを確認する。
3. 選択中イベントの詳細を確認する。

期待結果: 正常系。背景はディープミッドナイトブルー（`#1a1b26`）、構造線とタイトルはネオンシアンまたはエレクトリックブルーで表示される。`001`から始まるイベントが縦方向の時系列で表示される。選択中の`LLM call`は青い選択行で示され、詳細に`model`、`input tokens`、`output tokens`、`cost`、`retry count`、`PROMPT`、`RESPONSE`が表示される。補足情報はラベンダーまたはスレートグレーで表示される。画面下部に移動・filter・payload確認の操作が表示される。

## E2E-TUI-003 live実行確認で初期操作を中止にできる（境界値）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli --screen confirm --no-clear
```

1. 実行コマンドを実行する。
2. モデル名と料金上限を確認する。
3. 初期選択が`Cancel`であることを確認する。

期待結果: 境界値。`Benchmark`、`Model`、`Cost limit`、外部APIと課金の注意文が表示される。`Default: Cancel`が表示され、利用者が`y`を入力しない限りlive実行を開始しない。

## E2E-TUI-004 OpenRouterレート制限を原因と対処とともに表示できる（異常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli --demo-error openrouter --no-clear
```

1. 実行コマンドを実行する。
2. エラー分類を確認する。
3. 原因と対処を確認する。

期待結果: 異常系。失敗情報はクリムゾンレッド（`#f7768e`）、対処はアンバーオレンジ（`#e0af68`）で表示される。`OpenRouter rate limited`、`HTTP 429`、`Retry-After`、`change model`が表示される。`runs`へ戻る、retry、終了の操作が表示される。APIキーや秘密情報は表示されない。

## E2E-TUI-005 DBマイグレーション失敗を原因と対処とともに表示できる（異常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli --demo-error migration --no-clear
```

1. 実行コマンドを実行する。
2. エラー分類を確認する。
3. DB接続確認の対処を確認する。

期待結果: 異常系。`DB migration failed`、`Database schema is not current.`、`DATABASE_URL`、`migrate_database.py`が表示される。`runs`へ戻る、retry、終了の操作が表示される。DBを更新せず、接続文字列の秘密情報も表示しない。

## E2E-TUI-006 Python Bridge失敗を原因と対処とともに表示できる（異常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli --demo-error bridge --no-clear
```

1. 実行コマンドを実行する。
2. エラー分類を確認する。
3. 詳細確認と再試行の対処を確認する。

期待結果: 異常系。`Python bridge failed`、`non-zero exit code`、`stderr details`、`retry`が表示される。`runs`へ戻る、retry、終了の操作が表示される。Pythonの標準エラー内容は、このモック画面では要約のみを表示する。

## E2E-TUI-007 Traceで矢印キーを操作して選択イベントを移動できる（境界値）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli
```

1. 実行コマンドを実行する。
2. 下矢印キーで`Agentの動きを見る`を選択する。
3. Enterキーを押してTrace画面を開く。
4. 上矢印キーを押して選択行を1つ上へ移動する。
5. 下矢印キーを押して選択行を1つ下へ移動する。
6. 上矢印キーを連続して押し、`001`より前へ移動しないことを確認する。
7. 下矢印キーを連続して押し、`006`より後へ移動しないことを確認する。
8. `q`キーを押して終了する。

期待結果: 境界値。上矢印キーで選択行と右側詳細が前のイベントへ更新され、下矢印キーで次のイベントへ更新される。選択行はエレクトリックブルー背景で表示される。先頭の`001`と末尾の`006`では、さらに同じ矢印キーを押しても選択範囲外へ移動しない。Enterを押さずに操作できる。

## E2E-TUI-008 案内式ホームから目的の画面を開ける（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build cli
```

1. 実行コマンドを実行する。
2. 初期画面の案内項目を確認する。
3. 下矢印キーで`新しい評価を開始する`を選択する。
4. Enterキーを押す。
5. 評価開始画面を確認する。
6. `q`キーを押して終了する。

期待結果: 正常系。初期画面に`評価結果を見る`、`Agentの動きを見る`、`新しい評価を開始する`、`保存済みデータを探す`、`ヘルプ`が表示される。選択中の項目は青い背景と`▶`で表示される。Enter後は`NEW EVALUATION`、`STEP 1 / 3`、`GEN-TOOL-001`が表示される。
