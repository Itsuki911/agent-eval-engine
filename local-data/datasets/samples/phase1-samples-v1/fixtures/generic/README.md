# generic fixtures

generic fixtureは、決定的なツール応答と安全ポリシーを提供します。

- `tool-selection-v1`: ツール名・引数・順序の評価。
- `tool-recovery-v1`: timeout、rate limit、validation errorの回復評価。
- `safety-policy-v1`: 禁止操作と確認必須操作の評価。
- `prompt-injection-v1`: 非信頼コンテンツ中の偽命令に対する耐性評価。
- `security-boundary-v1`: 権限境界、隔離、情報流出、資源枯渇への耐性評価。
- `conversation-state-v1`: 要件確認、計画変更、複数ターン状態の評価。
- `structured-output-v1`: JSON、YAML、CSVと安全な構造化出力の評価。
- `data-processing-v1`: 時刻、単位、集計、根拠付き回答の評価。
