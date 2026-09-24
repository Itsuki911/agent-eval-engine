# Phase 3評価エンジンの手動E2Eテスト

## 共通出力形式

`pytest -s`で表示される確認結果は1行JSONである。`test`はテスト名、`result`は`passed`、live LLM実行時は`model`・`llm_cost_usd`・`duration_ms`などで確認する。下記の期待結果にある表示文は、対応するJSONのキー・値で確認する。APIキーは出力しない。

## E2E-ENGINE-001 dry-runを端末から実行して結果を表示できる（正常系）

実行コマンド:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\phase3.ps1 dry-run
```

1. 実行コマンドを実行する。
2. `Phase 3: checking and applying DB migrations.`が表示され、正常終了することを確認する。
3. 最後に表示されるJSONを確認する。

期待結果: 正常系。評価の前に`alembic upgrade head`が実行され、未適用のマイグレーションがあれば適用される。マイグレーションに失敗した場合は、`DB migration failed. Evaluation will not start.`と表示され、評価用のrunは作成されない。成功時はJSONに`status: simulated`、UUID形式の`run_id`、`event_count: 8`、16件の`metrics`、`final_state.dry_run: true`が表示される。dry-runのため`llm_cost_usd`はJSONとDBのrunsに表示・保存されない。OpenTelemetryの`agent.run`と各ワークフローノードのtraceも表示され、DBにはrun・events・metrics・evaluationが保存される。

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

期待結果: 正常系。`model`、`status`、LLMの`answer`、`events`、`metrics=16`、`evaluation=passed`または`evaluation=failed`、`llm_cost_usd`が表示される。料金は今回のAPI LLM実行分だけを表し、runsの`llm_cost_usd`とevaluation summaryにも同じ値で保存される。`dry_run=False`の実行履歴がテストDBへ保存・復元される。タスクの評価結果が`failed`でも、モデル応答・イベント・指標・評価結果を保存できればE2Eテスト自体は成功である。OpenRouterが429を返す場合は、`rate_limit_error`と`failure_category=rate_limit`として記録され、使用量が返らなければ料金は表示されない。テスト終了時には、このテストが作成したrunだけを削除する。

備考: OpenRouterへの外部通信とモデル利用料金が発生する可能性がある。`RUN_LIVE_OPENROUTER_E2E=1`を指定しない限り、このテストはskipされる。APIキーは出力しない。
