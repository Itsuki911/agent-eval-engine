# generic ベンチマーク

汎用エージェントのツール利用、回復性、安全性、攻撃耐性を評価します。

| ID領域 | 対象 | fixture |
| --- | --- | --- |
| `GEN-TOOL` | ツール選択・引数・複数ツール | `generic/tool-selection-v1` |
| `GEN-REC` | timeout、rate limit、再試行・回復 | `generic/tool-recovery-v1` |
| `GEN-SAFE` | 安全制約・確認・情報保護 | `generic/safety-policy-v1` |
| `GEN-INJ` | prompt injectionと非信頼コンテンツ | `generic/prompt-injection-v1` |
| `GEN-SEC` | 権限、隔離、外部送信、資源枯渇 | `generic/security-boundary-v1` |

各タスクは最終状態、禁止操作、上限値で判定します。固定された思考過程や操作順を要求せず、安全に同じ結果へ到達できるかを評価します。
