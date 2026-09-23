# PostgreSQL永続化の手動統合テスト

## IT-DB-001 マイグレーションで評価テーブルを作成できる（正常系）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools alembic upgrade head
docker compose exec db psql -U agent_eval -d agent_eval -c '\dt'
```

1. `.env.example`を`.env`へコピーしてパスワードを変更する。
2. `docker compose up -d db`を実行する。
3. `docker compose run --rm db-tools alembic upgrade head`を実行する。
4. `docker compose exec db psql -U agent_eval -d agent_eval -c '\dt'`を実行する。

期待結果: コマンドが成功し、`runs`、`events`、`metrics`、`evaluations`、`alembic_version`が表示される。

## IT-DB-002 イベントから実行履歴を復元できる（正常系）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools pytest -v tests/integration/test_postgresql_persistence.py -k reconstruct_complete_history
```

テストファイル名だけをPowerShellで実行せず、上記の`docker compose run`行をそのまま実行する。

1. 実行コマンドを実行する。
2. テスト出力を確認する。

期待結果: すべてのテストが成功し、イベントの順序、生payload、最終状態、指標、評価結果を取得できる。

## IT-DB-003 接続先が存在しない場合に保存できない（異常系）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm -e DATABASE_URL=postgresql+psycopg://agent_eval:wrong-password@db:5432/agent_eval db-tools alembic upgrade head
```

1. 実行コマンドを実行する。

期待結果: 接続エラーで終了し、マイグレーション成功とは表示されない。

## IT-DB-004 イベント順序の境界値を保存できる（境界値）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools pytest -v tests/integration/test_postgresql_persistence.py -k duplicate_event_sequence
```

1. 実行コマンドを実行する。
2. テスト出力を確認する。

期待結果: 0と1は保存でき、重複した0は一意制約違反で保存できない。
