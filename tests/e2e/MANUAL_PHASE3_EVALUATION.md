# Phase 3評価エンジンの手動E2Eテスト

## E2E-ENGINE-001 dry-runを端末から実行して結果を表示できる（正常系）

実行コマンド:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\phase3.ps1 dry-run
```

1. 実行コマンドを実行する。
2. 最後に表示されるJSONを確認する。

期待結果: `status`が`simulated`であり、`run_id`、`event_count`、`metrics`が表示される。OpenTelemetryの`agent.run`と各ワークフローノードのtraceも表示される。

## E2E-ENGINE-002 APIキー未設定の実行を開始しない（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_openrouter.py -k placeholder_key
```

1. 実行コマンドを実行する。
2. エラー内容を確認する。

期待結果: `OPENROUTER_API_KEY を設定してください`を含むエラーで終了し、OpenRouterへ通信しない。
