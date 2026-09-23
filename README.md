
# Agent Evaluation Framework

AIエージェントのタスク成功だけでなく、ツール利用、回復性、安全性、コスト、遅延、
coding品質を評価するためのフレームワークです。

現在はPhase 1のbenchmark・fixture・Docker検証環境と、Phase 2のPostgreSQL永続化基盤を提供します。
エージェント実行、REST API、MCPは後続Phaseの対象です。

## Phase 1の内容

- generic benchmark: ツール利用、回復、安全性、prompt injection、境界保護。
- coding benchmark: Python、Go、C、Bash、PowerShell、TypeScript。
- fixture: 環境初期化、ツール応答、workspace、保護された検証領域。
- Docker validator: YAML schema、命名規則、fixture参照、必須ディレクトリを検証。

## 将来対応項目

- 対象言語を段階的に拡大する。現在のPython、Go、C、Bash、PowerShell、TypeScriptに加え、評価対象となるagentや利用環境に応じて言語・実行環境を追加する。
- 各言語のworkspaceタスクレベルを段階的に向上する。Phase 1の自己完結した小規模タスクを基準に、複数ファイル、設定、依存関係、API互換性、並行処理、実リポジトリ由来のissue解決へ拡張する。

## Phase 2: PostgreSQL永続化基盤

評価の1回の実行を、実行情報（`runs`）、順序付きイベント（`events`）、数値指標（`metrics`）、評価結果（`evaluations`）へ分けて保存します。`events`には入力やツール応答の原文をJSONBで保存するため、実行履歴を順序どおりに再現できます。

### 初回設定

1. `.env.example`を`.env`へコピーし、`POSTGRES_PASSWORD`をローカル用の値へ変更する。
2. `docker compose up -d db`を実行する。
3. `docker compose run --rm db-tools alembic upgrade head`を実行する。
4. `docker compose run --rm db-tools`を実行する。

期待結果: マイグレーションが成功し、テストが`runs`、`events`、`metrics`、`evaluations`を作成して、1件の実行ログからイベントと最終状態を完全に復元できることを確認します。

ターミナルから確認する場合は、次を実行します。

```bash
docker compose exec db psql -U agent_eval -d agent_eval
```

psql内の`\dt`でテーブル一覧を、`SELECT * FROM events;`で保存済みイベントを確認できます。原文には秘密情報が含まれる可能性があるため、ローカル開発環境以外で利用する前にマスキング方針を決めてください。

## はじめ方

```bash
python scripts/generate_phase1_benchmarks.py
python scripts/validate_phase1.py --check-fixtures
```

Dockerを利用できる環境では、次も実行できます。

```bash
docker compose build evaluator
docker compose run --rm evaluator
```

詳細は、[benchmarks/README.md](benchmarks/README.md)、[fixtures/README.md](fixtures/README.md)、
[database/README.md](database/README.md)、[docker/README.md](docker/README.md)、[docs/PHASE1_WORK_REPORT.md](docs/PHASE1_WORK_REPORT.md)を参照してください。
