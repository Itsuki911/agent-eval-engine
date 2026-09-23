# Phase 3評価指標の手動単体テスト

## UT-METRIC-001 成功実行から主要指標を計算できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_metrics.py -k successful_run
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_calculate_metrics_for_successful_run PASSED`と表示され、成功率、ツール成功率、コスト、遅延を算出できる。

## UT-METRIC-002 安全違反を検出して成功判定を拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_metrics.py -k safety_violation
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_safety_violation_rejects_task_success PASSED`と表示され、安全違反がある実行は成功と判定されない。

## UT-METRIC-003 重複ツールと回復を計測できる（境界値）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_metrics.py -k duplicate_tools
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_duplicate_tools_and_recovery_are_measured PASSED`と表示され、重複操作1件と回復成功を計測できる。
