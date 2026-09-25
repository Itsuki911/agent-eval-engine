
# Agent Evaluation Framework

AIエージェントのタスク成功だけでなく、ツール利用、回復性、安全性、コスト、遅延、
coding品質を評価するためのフレームワークです。

現在はPhase 1のbenchmark・fixture、Phase 2のPostgreSQL永続化、Phase 3のPython評価エンジンを提供します。
REST APIとMCPは後続Phaseの対象です。

## Phase 1の内容

- generic benchmark: ツール利用、回復、安全性、prompt injection、境界保護。
- coding benchmark: Python、Go、C、Bash、PowerShell、TypeScript。
- fixture: 環境初期化、ツール応答、workspace、保護された検証領域。
- Docker validator: YAML schema、命名規則、fixture参照、必須ディレクトリを検証。

## 将来対応項目

- 対象言語を段階的に拡大する。現在のPython、Go、C、Bash、PowerShell、TypeScriptに加え、評価対象となるagentや利用環境に応じて言語・実行環境を追加する。
- 各言語のworkspaceタスクレベルを段階的に向上する。Phase 1の自己完結した小規模タスクを基準に、複数ファイル、設定、依存関係、API互換性、並行処理、実リポジトリ由来のissue解決へ拡張する。
- TUIの「新しい評価を開始する」から、既存benchmarkの選択に加えて、利用者がbenchmarkを入力形式で作成・保存できるようにする。初期対応は`generic`と`coding`に限定し、現在用意しているbenchmarkは作成例として扱う。作成画面は現在のYAML schemaと項目（`title`、`expected`、`evaluation`など）を変更せず、必須項目の入力・検証後に追加する。利用者が作成・利用した評価データセットはローカルへ保存し、後から選択・再利用できるようにする。分類や対応領域は後続Phaseで拡張する。
- 保存済みの評価データをCSV形式で出力し、ExcelやGoogle Sheetsで利用できるようにする。出力ファイルは利用者のローカルダウンロード先へ保存する。

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


タイムアウト・429以外では、次を含めると実運用で扱いやすくなります。
- 認証エラー（401）：APIキー未設定・無効・期限切れ
- 認可エラー（403）：モデルや機能の利用権限不足
- リクエスト形式エラー（400）：必須項目不足、型不一致、不正なmessages形式
- 入力上限超過（400 / 413）：プロンプト・添付データ・コンテキスト長が上限超過
- 出力上限超過：max_tokens などの設定が不正、または生成が途中で打ち切られた
- モデル未発見・廃止（404）：モデルID誤り、提供終了、プロバイダー側の変更
- プロバイダー障害（500）：LLM提供元の内部エラー
- 一時的なサービス停止（502 / 503 / 504）：ゲートウェイ障害、過負荷、メンテナンス
- 接続エラー：DNS解決失敗、TLS証明書エラー、ネットワーク切断
- ストリーミング切断：応答生成中に接続が途中で閉じられる
- 不正な応答形式：JSONモードなのにJSONでない、必須フィールド欠落、スキーマ不一致
- 空の応答：choicesや本文が空で、評価結果を判定できない
- 安全フィルタによる拒否：プロバイダーまたはモデルが生成を拒否した
- コンテンツフィルタによる途中停止：一部のみ生成され、完了理由が安全制約である
- ツール呼び出し形式エラー：tool callの引数JSON不正、未定義ツール指定、必須引数欠落
- 構造化出力の検証失敗：Pydantic等の期待スキーマに変換できない
- コスト上限超過：トークン数・料金の事前推定または実績が上限を超える
- リトライ上限到達：再試行可能な障害でも、指定回数以内に復旧しない
- 冪等性の問題：同じ依頼の再試行で二重課金・二重実行となる可能性
- 応答と要求の対応不整合：別リクエストの応答、会話ID不一致、壊れたキャッシュ応答
特に次に実装優先度が高いのは、401/403、400・入力上限、500/502/503/504、接続エラー、不正な応答形式、構造化出力検証失敗、リトライ上限到達です。
