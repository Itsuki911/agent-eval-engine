# DB永続化の手動単体テスト

## UT-DB-001 実行情報を保存して取得できる（正常系）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools pytest -q tests/integration/test_postgresql_persistence.py -k reconstruct_complete_history
```

1. `RunRepository.create_run` を呼び出す。
2. 返却されたIDで `RunRepository.get_run` を呼び出す。

期待結果: 同じID、benchmark ID、agent名を持つ実行情報が取得できる。

## UT-DB-002 同一実行の重複順序イベントを拒否できる（異常系）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools pytest -q tests/integration/test_postgresql_persistence.py -k duplicate_event_sequence
```

1. 同じ実行IDと`sequence=0`でイベントを1件保存する。
2. 同じ実行IDと`sequence=0`で別のイベントを保存する。

期待結果: 保存は失敗し、`runs`のイベントは1件のままである。

## UT-DB-003 未登録の実行を終了できない（異常系）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools pytest -q tests/integration/test_postgresql_persistence.py -k unknown_run
```

1. 未登録のUUIDで `RunRepository.finish_run` を呼び出す。

期待結果: `ValueError`が発生し、実行情報は作成されない。
