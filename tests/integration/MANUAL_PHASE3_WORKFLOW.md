# Phase 3評価ワークフローの手動統合テスト

## IT-WORKFLOW-001 dry-runで評価実行を保存できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/integration/test_phase3_workflow.py -k dry_run_persists
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_dry_run_persists_evaluation_history PASSED`と表示され、イベント・指標・評価結果がテストDBへ保存される。

## IT-WORKFLOW-002 モデル失敗をイベントと失敗分類へ保存できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/integration/test_phase3_workflow.py -k model_failure
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_model_failure_is_persisted PASSED`と表示され、`model_error`イベントと`model`失敗分類が保存される。
