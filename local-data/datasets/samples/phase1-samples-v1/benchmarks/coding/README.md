# coding ベンチマーク

複数言語のcoding agentを同じ評価形式で扱います。各benchmarkは変更可能な`workspace`、変更禁止の`verify`、言語別の検証コマンドを持つfixtureを参照します。

| ID領域 | 言語 | fixture |
| --- | --- | --- |
| `COD-PY` | Python | `coding/python-workspace-v1` |
| `COD-GO` | Go | `coding/go-workspace-v1` |
| `COD-C` | C | `coding/c-workspace-v1` |
| `COD-BASH` | Bash | `coding/bash-workspace-v1` |
| `COD-PS` | PowerShell | `coding/powershell-workspace-v1` |
| `COD-TS` | TypeScript | `coding/typescript-workspace-v1` |
| `COD-COMMON` | 言語共通 | `coding/common-workspace-v1` |

Phase 1ではデータ契約とfixture構造を検証します。各言語のコンパイル、lint、security scan、回帰試験を実行するrunnerはPhase 3以降に追加します。
