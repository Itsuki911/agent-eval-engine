# ベンチマーク

このフォルダには、エージェントへ与えるタスクと採点契約をYAMLで置きます。環境の初期状態やツールの応答は `fixtures/` に分離します。

## 構成

- `generic/`: ツール選択、回復性、安全性、プロンプトインジェクション、境界保護。
- `coding/`: Python、Go、C、Bash、PowerShell、TypeScriptの開発タスク。
- `catalog.json`: 生成済みタスクのID、title、category、fixtureの一覧。

## 命名規則

- `GEN-<AREA>-NNN.yaml`: 汎用エージェント評価。
- `COD-<LANGUAGE>-NNN.yaml`: coding agent評価。

IDは再利用しません。初期状態を変更する場合はbenchmark IDではなくfixtureの`-vN`を更新します。

## 利用方法

```bash
python scripts/generate_phase1_benchmarks.py
python scripts/validate_phase1.py --check-fixtures
```

詳細は `generic/README.md` と `coding/README.md` を参照してください。
