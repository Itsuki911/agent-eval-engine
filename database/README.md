# PostgreSQL永続化基盤

評価エンジンの実行記録をPostgreSQLへ保存します。アプリケーションからのDB操作は、Pythonの`database`パッケージを通して行います。

## テーブル

| テーブル | 役割 |
| --- | --- |
| `runs` | 評価実行の設定、状態、最終結果を保存する。 |
| `events` | 実行中の入力・ツール呼び出し・応答などを順序付きで保存する。 |
| `metrics` | 成功率、遅延、コストなどの数値指標を保存する。 |
| `evaluations` | 評価器ごとの判定、点数、所見を保存する。 |

`events`には順序、時刻、前後の状態、trace/span ID、原文payloadを保存します。これにより、1回の実行ログから処理の流れを再現できます。実行時の入力・出力に秘密情報が含まれ得るため、ローカル開発DB以外へ保存する前にはマスキング方針を決めてください。

## 実行方法

```bash
docker compose up -d db
docker compose run --rm db-tools alembic upgrade head
docker compose run --rm db-tools
```

期待結果: マイグレーションが成功し、統合テストで1件の実行ログから順序付きイベントと最終状態を再現できることを確認します。

## ターミナルでの確認

```bash
docker compose exec db psql -U agent_eval -d agent_eval
```

psql内で`\dt`を実行すると、4つの評価テーブルと`alembic_version`を確認できます。
