# DB永続化の手動回帰テスト

## RT-DB-001 同じマイグレーションを再実行しても構造を壊さない（回帰）

実行コマンド:

```bash
docker compose up -d db
docker compose run --rm db-tools alembic upgrade head
docker compose run --rm db-tools alembic upgrade head
docker compose exec db psql -U agent_eval -d agent_eval -c "SELECT version_num FROM alembic_version;"
```

1. 実行コマンドを上から順に実行する。

期待結果: 両方のコマンドが成功し、`alembic_version`は`20260923_0001`を1件だけ返す。
