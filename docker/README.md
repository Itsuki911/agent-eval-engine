# Docker評価環境

Phase 1では、Dockerを評価データの**検証環境**として使用します。Docker内のvalidatorは、YAMLのスキーマ、命名規則、fixture参照、fixtureの基本構成を検査します。
まだエージェント本体、PostgreSQL、外部LLM、ネットワーク接続は起動しません。

## 実行

```bash
docker compose build evaluator
docker compose run --rm evaluator
```

上記はコンテナ内で `python scripts/validate_phase1.py --check-fixtures` を実行します。
`network_mode: none` のため、実行中の評価データは外部通信できません。
依存パッケージの取得はイメージビルド時だけに発生します。

## 構成

- `Dockerfile.evaluator`: Python 3.12とYAML/JSON Schema検証依存を固定するイメージ。
- `docker-compose.yml`: 読み取り専用でリポジトリをマウントする検証サービス。
- `requirements-evaluator.txt`: validatorのPython依存を固定するファイル。

## 注意

coding fixtureのPython、Go、C、Bash、PowerShell、TypeScriptの実際のビルド・テストはPhase 3以降に言語別runnerとして追加します。Phase 1では、各fixtureに必要な言語、検証コマンド、保護対象パスを宣言し、データ契約を先に固定します。
