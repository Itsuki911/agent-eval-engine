# 設定

`phase1-local.yaml` は、Phase 1のデータ検証・ローカル実行に使う共通設定です。

- benchmarkとfixtureのルートディレクトリ
- 外部ネットワークの既定値
- 並列数
- 軌跡の保存方針
- 選択するbenchmarkの状態

Phase 1では `draft` の定義を検証対象にしています。実エージェントの実行を導入するPhase 3で、`active` のみを通常実行対象に切り替えます。
