# Phase 3評価エンジンの手動E2Eテスト

## E2E-ENGINE-001 dry-runを端末から実行して結果を表示できる（正常系）

実行コマンド:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\phase3.ps1 dry-run
```

1. 実行コマンドを実行する。
2. 最後に表示されるJSONを確認する。

期待結果: 正常系。JSONに`status: simulated`、UUID形式の`run_id`、`event_count: 8`、16件の`metrics`、`final_state.dry_run: true`が表示される。OpenTelemetryの`agent.run`と各ワークフローノードのtraceも表示され、DBにはrun・events・metrics・evaluationが保存される。

## E2E-ENGINE-002 APIキー未設定の実行を開始しない（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k placeholder_key
```

1. 実行コマンドを実行する。
2. エラー内容を確認する。

期待結果: 異常系。`OpenRouter接続: プレースホルダーを拒否し、クライアントを生成しない` と表示される。APIキーの値を出力せず、OpenRouterへの通信前に設定値を拒否する。

## E2E-ENGINE-003 OpenRouterモデルで評価を実行して結果を表示できる（正常系）

実行コマンド:

```powershell
$env:RUN_LIVE_OPENROUTER_E2E = "1"
docker compose --profile engine run --rm -e RUN_LIVE_OPENROUTER_E2E engine pytest -v -s -m live tests/e2e/test_phase3_openrouter_live.py
```

1. `.env` に有効な `OPENROUTER_API_KEY` を設定する。
2. 実行コマンドを順に実行する。
3. `OpenRouter E2E:` から始まる結果を確認する。

期待結果: 正常系。`model`、`status`、LLMの`answer`、`events`、`metrics=16`、`evaluation=passed`または`evaluation=failed`が表示される。`dry_run=False`の実行履歴がテストDBへ保存・復元される。タスクの評価結果が`failed`でも、モデル応答・イベント・指標・評価結果を保存できればE2Eテスト自体は成功である。テスト終了時には、このテストが作成したrunだけを削除する。

備考: OpenRouterへの外部通信とモデル利用料金が発生する可能性がある。`RUN_LIVE_OPENROUTER_E2E=1`を指定しない限り、このテストはskipされる。APIキーは出力しない。
