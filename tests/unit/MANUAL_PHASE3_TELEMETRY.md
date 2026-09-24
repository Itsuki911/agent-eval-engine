# Phase 3観測機能の手動単体テスト

## UT-TELEMETRY-001 イベントへtrace IDとspan IDを付与できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_events.py -k trace_context
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。`sequence=0`、`trace_id_length=32`、`span_id_length=16` が表示される。最初のイベントに順序番号と有効な追跡IDが付与される。

## UT-TELEMETRY-002 未対応の観測exporterを拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_config.py -k unknown_telemetry_exporter
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 異常系。`観測設定検証: 未対応exporter=unknownを拒否` と表示される。未対応の観測exporterは設定として保存・実行されない。
