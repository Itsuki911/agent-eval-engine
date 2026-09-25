
# Agent Evaluation Framework

AI エージェントを評価するための開発用フレームワークです。タスク成否だけでなく、ツール利用、回復性、安全性、コスト、遅延、実行履歴を記録・評価します。

現在は、YAML benchmark・fixture、PostgreSQL 永続化、Python 評価エンジン、Go 製 TUI、利用者作成データセット、CSV 出力、および将来の Real Coding Agent 連携用 DB 基盤を提供します。

## 現在の構成

| 領域 | 主な役割 |
| --- | --- |
| `benchmarks/` | generic / coding の評価データセット（YAML） |
| `fixtures/` | ツール応答、workspace、セキュリティ境界などの再現環境 |
| `packages/core/agent_eval/` | Python 評価エンジン、LLM 接続、評価、CSV 出力 |
| `database/` | SQLAlchemy モデル、Repository、Alembic migration |
| `apps/cli/` | Go 製の対話型 TUI |
| `scripts/` | 評価実行、TUI バックエンド、sample package 作成 |
| `tests/` | 自動テストと人間向け手動テストケース |

## 評価の流れ

```text
benchmark YAML
  -> fixture / 制約の読込
  -> Python 評価エンジン
  -> events / metrics / evaluations を PostgreSQL へ保存
  -> Go TUI で run・Trace・結果を確認
  -> 必要に応じて CSV をホスト側へ出力
```

1 回の評価は `runs` を親として保存します。`events` に順序付きの原文 payload を残すため、実行履歴を時系列で再構成できます。

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

## Phase 3: Python評価エンジン

LangGraphで、benchmark読込、実行、イベント収集、評価、PostgreSQL保存を順番に実行します。モデル設定は[configs/phase3-local.yaml](configs/phase3-local.yaml)、APIキーは`.env`の`OPENROUTER_API_KEY`で管理します。

### dry-runの実行

初回は外部APIを呼ばないdry-runを使います。`.env.example`を`.env`へコピーしてDBパスワードを設定した後、次を実行します。

```bash
docker compose --profile engine build engine
docker compose --profile engine run --rm engine python scripts/run_evaluation.py --benchmark benchmarks/generic/GEN-TOOL-001.yaml
```

期待結果: 最後に表示されるJSONの`status`が`simulated`になり、`run_id`、`event_count`、評価指標が表示されます。イベント、指標、評価結果はPostgreSQLへ保存されます。

### OpenRouterを使う実行

`configs/phase3-local.yaml`の`engine.dry_run`を`false`へ変更し、`.env`の`OPENROUTER_API_KEY`に有効なキーを設定してから同じコマンドを実行します。実行時はAPI費用が発生する可能性があります。Phase 3ではツール・workspaceを実行しないため、`simulated`は実ツール評価の結果ではありません。

## Phase 4: Go TUIと評価エンジンの統合

TUIのモック表示だけを確認する場合は、次を実行します。DB、Python評価エンジン、LLM APIは使用しません。

```bash
docker compose --profile cli run --rm --build cli
```

PostgreSQLに保存された実行履歴の表示、Python評価エンジンによる評価開始、実行イベントのTimeline表示を確認する場合は、統合TUIを実行します。起動時にDB migrationを確認・適用します。

```bash
docker compose --profile tui run --rm --build tui
```

統合TUIはGoからPython subprocessを呼び出し、Pythonが評価・DB操作を担当します。初期設定ではdry-runのため外部APIを呼びません。`configs/phase3-local.yaml`の`engine.dry_run`を`false`へ変更した場合だけ、確認画面からの実行でOpenRouter APIを使用します。

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


