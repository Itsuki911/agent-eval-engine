# coding fixtures

各言語fixtureは `workspace/` と `verify/` を持ちます。実装変更はworkspaceに限定し、verifyは隠しテスト相当の保護対象です。

| fixture | 言語 | 検証コマンド |
| --- | --- | --- |
| `python-workspace-v1` | Python | `python -m unittest discover ../verify` |
| `go-workspace-v1` | Go | `go test ./...` |
| `c-workspace-v1` | C | `make check` |
| `bash-workspace-v1` | Bash | `bash ../verify/check.sh` |
| `powershell-workspace-v1` | PowerShell | `pwsh -File ../verify/check.ps1` |
| `typescript-workspace-v1` | TypeScript | `npm test` |
| `common-workspace-v1` | 言語共通 | `python ../verify/check.py` |

Phase 1のvalidatorは構成を検査します。言語別コンテナでの実行は後続Phaseで導入します。
