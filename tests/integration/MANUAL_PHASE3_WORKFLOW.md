# Phase 3評価ワークフローの手動統合テスト

## 共通出力形式

`pytest -s`で表示される確認結果は1行JSONである。`test`はテスト名、`result`は`passed`、`status`・`failure_category`・`event_type`・`llm_cost_usd`などのキーでDB保存結果を確認する。下記の期待結果にある表示文は、対応するJSONのキー・値で確認する。

## IT-WORKFLOW-001 dry-runで評価実行を保存できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase3_workflow.py -k dry_run_persists
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。`status=simulated`、`events=8以上`、`metrics=16`、`evaluation=simulated` が表示される。dry-runでは `llm_cost_usd` を端末出力・runs・evaluation summaryへ保存しない。実行履歴は連番で保存・復元され、レイテンシ指標を含む16件の指標と評価結果がテストDBへ保存される。

## IT-WORKFLOW-002 モデル失敗をイベントと失敗分類へ保存できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase3_workflow.py -k model_failure
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 異常系。`status=failed`、`failure_category=model`、`event_type=model_error` が表示される。モデル実行失敗は例外だけで終わらず、イベントと失敗分類として保存される。

## IT-WORKFLOW-003 OpenRouterモデルの評価履歴を保存・復元できる（正常系）

実行コマンド:

```powershell
$env:RUN_LIVE_OPENROUTER_INTEGRATION = "1"
docker compose --profile engine run --rm -e RUN_LIVE_OPENROUTER_INTEGRATION engine pytest -v -s -m live tests/integration/test_phase3_openrouter_live.py
```

1. `.env` に有効な `OPENROUTER_API_KEY` を設定する。
2. 実行コマンドを順に実行する。
3. `OpenRouter Integration:` から始まる結果を確認する。

期待結果: 正常系。`model`、`status`、`events`、`metrics=16`、`evaluation`、`event_types`が表示される。`event_types`には`llm_call`と`model_response`、またはモデル不正応答時の`model_error`が含まれる。`dry_run=False`のrun・events・metrics・evaluationをテストDBへ保存し、eventsから履歴を復元できる。

備考: OpenRouterへの外部通信とモデル利用料金が発生する可能性がある。`RUN_LIVE_OPENROUTER_INTEGRATION=1`を指定しない限り、このテストはskipされる。テスト終了時には、このテストが作成したrunだけを削除する。

## IT-WORKFLOW-004 OpenRouterのタイムアウトを失敗履歴として保存できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase3_workflow.py -k timeout_is_persisted
```

1. 実行コマンドを実行する。
2. `タイムアウト保存:` から始まる結果を確認する。

期待結果: 異常系。`status=failed`、`failure_category=timeout`、`event_type=timeout_error`、`status_code=408`、`retry_count=1` が表示される。タイムアウトは未分類の例外ではなく、HTTP状態・再試行回数とともにDBのイベント・失敗分類・評価結果として保存される。外部APIへは通信しない。

## IT-WORKFLOW-005 OpenRouterのレート制限を失敗履歴として保存できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase3_workflow.py -k rate_limit_is_persisted
```

1. 実行コマンドを実行する。
2. `レート制限保存:` から始まる結果を確認する。

期待結果: 異常系。`status=failed`、`failure_category=rate_limit`、`event_type=rate_limit_error`、`status_code=429`、`retry_count=1` が表示される。HTTP 429のレート制限は、未分類の例外ではなくHTTP状態・再試行回数とともにDBのイベント・失敗分類・評価結果として保存される。外部APIへは通信しない。

## IT-WORKFLOW-006 OpenRouter代表例外を分類して履歴へ保存できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase3_workflow.py -k openrouter_error_categories_are_persisted
```

1. 実行コマンドを実行する。
2. 各 `例外保存:` の出力を確認する。

期待結果: 異常系。`auth`、`input_limit`、`connection`、`safety_filter`、`structured_output`、`cost_limit`、`retry_limit` の各分類について、`status=failed` と対応する `{分類}_error` eventが表示される。各例外のevents・failure_category・evaluationがテストDBへ保存される。外部APIへは通信しない。

## IT-WORKFLOW-007 API LLM料金を実行履歴へ保存できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase3_workflow.py -k live_llm_cost_is_persisted
```

1. 実行コマンドを実行する。
2. `LLM料金保存:` から始まる結果を確認する。

期待結果: 正常系。`llm_cost_usd=0.01250000` が表示される。API LLM実行の料金は、runsの`llm_cost_usd`、evaluation summary、復元した実行履歴へ同じ値で保存される。外部APIへは通信しない。
