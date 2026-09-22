# スキーマ

このフォルダはbenchmarkとfixtureのYAML契約をJSON Schemaで定義します。

- `benchmark.schema.json`: タスク、制約、期待結果、上限値の形式。
- `fixture-manifest.schema.json`: 環境初期化、ツール、検証コマンドの形式。

YAMLを追加・変更した後は、次のコマンドで検証します。

```bash
python scripts/validate_phase1.py --check-fixtures
```

ローカル環境に依存パッケージがない場合は、Dockerで実行してください。
