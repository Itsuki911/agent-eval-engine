# Phase 3観測機能の手動単体テスト

## UT-TELEMETRY-001 イベントへtrace IDとspan IDを付与できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_events.py -k trace_context
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_event_collector_adds_trace_context PASSED`と表示され、イベントへtrace IDとspan IDを付与できる。

## UT-TELEMETRY-002 未対応の観測exporterを拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_config.py -k unknown_telemetry_exporter
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_unknown_telemetry_exporter_is_rejected PASSED`と表示され、未対応値を設定として受け入れない。
