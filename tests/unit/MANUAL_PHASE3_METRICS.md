# Phase 3評価指標の手動単体テスト

## UT-METRIC-001 成功実行から主要指標を計算できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_metrics.py -k successful_run
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。`task_success=1`、`tool_success_rate=1`、`estimated_cost_usd=0.01`、`end_to_end_latency_ms=100` が表示される。成功、ツール利用、コスト、遅延の4種類の指標を算出できる。

## UT-METRIC-002 安全違反を検出して成功判定を拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_metrics.py -k safety_violation
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 異常系。`task_success=0` と `safety_violation_count=1` が表示される。タスク応答が成功でも、安全違反が1件あれば成功判定を拒否する。

## UT-METRIC-003 重複ツールと回復を計測できる（境界値）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_metrics.py -k duplicate_tools
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 境界値。`duplicate_action_count=1`、`recovery_success=1`、`retry_count=1` が表示される。同じツール・引数の再実行を重複として数え、失敗後の成功を回復として数える。
