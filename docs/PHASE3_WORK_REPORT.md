# Phase 3 作業報告

## 概要

Python評価エンジンを追加しました。LangGraphがbenchmark読込、実行準備、モデル実行、イベント収集、評価、PostgreSQL保存を順番に実行します。

## 構成

| 要素 | 内容 |
| --- | --- |
| 設定 | `configs/phase3-local.yaml`でエンジン、OpenRouter、観測を管理する。 |
| 秘密情報 | `.env`の`OPENROUTER_API_KEY`で管理する。 |
| workflow | LangGraphの6ノードで実行を進める。 |
| 観測 | OpenTelemetryで`agent.run`と各ノードをtraceする。 |
| 永続化 | Phase 2の4テーブルへ実行、イベント、指標、評価を保存する。 |
| CLI | `scripts/run_evaluation.py`で端末から実行する。 |

## dry-run

初期設定は`dry_run: true`です。外部APIを呼ばず、決定的な模擬応答でワークフロー、観測、DB保存を確認します。出力の`status: simulated`は、実ツールを使った性能評価ではないことを表します。

## 評価指標

- 成功: task success
- 軌跡: step count、重複操作数
- ツール: 呼出数、成功率、不正引数率、retry、遅延
- 回復: エラー後の成功
- コスト: 入出力token、推定費用
- 遅延: end-to-end latency
- 堅牢性: 環境・timeoutエラーの有無
- 安全性: 違反数、safety score

## 実行方法

```powershell
docker compose up -d db
docker compose --profile engine build engine
powershell -ExecutionPolicy Bypass -File .\scripts\phase3.ps1 test
powershell -ExecutionPolicy Bypass -File .\scripts\phase3.ps1 dry-run
```

期待結果: テストが成功し、dry-runのJSONに`status: simulated`、`run_id`、`event_count`、`metrics`が表示される。

Linux/macOSでmakeを使える環境では、`make phase3-test`と`make phase3-dry-run`も利用できます。

## 実OpenRouter実行

`.env`へ有効な`OPENROUTER_API_KEY`を設定し、`configs/phase3-local.yaml`の`engine.dry_run`を`false`へ変更します。API費用が発生する可能性があります。

## テストケース適用確認

| 対象 | 自動テスト | 手動テスト |
| --- | --- | --- |
| 設定・benchmark検証 | `test_phase3_config.py` | `MANUAL_PHASE3_CONFIG.md` |
| 観測・イベント | `test_phase3_events.py` | `MANUAL_PHASE3_TELEMETRY.md` |
| 評価指標 | `test_phase3_metrics.py` | `MANUAL_PHASE3_METRICS.md` |
| OpenRouter設定 | `test_phase3_openrouter.py` | `MANUAL_PHASE3_EVALUATION.md` |
| workflow・DB保存 | `test_phase3_workflow.py` | `MANUAL_PHASE3_WORKFLOW.md` |

## 除外した内容

Phase 3では、実ツール呼び出し、coding workspace操作、ブラウザ・GUI操作を実行しません。Phase 1 fixtureにはツール定義はありますが実装がないため、これらは実行アダプターとsandboxを追加する後続Phaseで扱います。
