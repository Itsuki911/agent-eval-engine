# Phase 1 作業報告

## 作業報告の要約

評価用データセット、benchmark、fixture、Docker検証環境を作成しました。
benchmarkはタイトル一覧を正本とする生成方式とし、generic 128件、coding 153件、
合計281件を個別YAMLとして生成しています。全定義はJSON Schema、命名規則、fixture参照、
必須ディレクトリの検査に合格しました。

## 作成した環境構築の内容

- `docker/Dockerfile.evaluator`: Python 3.12、PyYAML、jsonschemaを固定した検証イメージ。
- `docker-compose.yml`: 読み取り専用マウント、read-only filesystem、`network_mode: none` を使うvalidatorサービス。
- `scripts/validate_phase1.py`: 全benchmark YAMLとfixture YAMLを検証するvalidator。
- `scripts/generate_phase1_benchmarks.py`: タイトル一覧から個別YAMLとcatalogを生成するスクリプト。
- `requirements-evaluator.txt`: Docker内validatorが使用するPython依存バージョン。
- `Makefile`: generate、validate、Docker validate用のショートカット。

## 実行したコマンド

- `python scripts/generate_phase1_benchmarks.py`
- `python scripts/validate_phase1.py --check-fixtures`
- `docker compose config`
- `docker compose build evaluator`
- `git diff --check`

## 検証結果

- YAML validator: 成功（172 benchmarks、11 fixtures）。
- Docker Compose構文展開: 成功。
- Dockerイメージbuild: 成功（Python 3.12、PyYAML、jsonschemaを含む`evaluator`イメージ）。
- Docker内validator: 成功（読み取り専用・実行時ネットワークなしで281 benchmarks、15 fixtures）。

## ワンポイント解説

**benchmarkとfixtureの分離**は、テスト問題と実行環境を別々に管理するパターンです。
benchmarkは「何を達成すれば成功か」、fixtureは「どの状態から始めるか」を担当します。
同じfixtureを複数の問題で共有でき、初期状態を変更する場合もfixtureのversionだけを増やせます。
これは、再現性と比較可能性を保つための基本です。

## 次に調べる推奨キーワード

- `JSON Schema Draft 2020-12` - Phase 1のデータ契約を厳密化するため。
- `Docker Compose security read-only network none` - Phase 1からPhase 3の安全な実行環境へ進むため。
- `OpenTelemetry trace semantic conventions` - Phase 3のtrajectory・イベント収集を設計するため。

## 確認・質問点

- 281件はすべて `human_review: pending` のタイトルベース定義です。完成形では、各タスクの具体的な入力、期待最終状態、攻撃ペイロード、故障したworkspace、検証テストを人間レビューしてから `approved` に変更する必要があります。
- Windowsを正式サポートする方針に決定しました。PowerShell fixture用に `docker-compose.windows.yml` を追加しています。Linux ContainersモードとWindows Containersモードは同時利用できないため、実行対象に応じてDocker Desktopのコンテナモードを切り替えます。
