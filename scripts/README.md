# スクリプト

## データセット生成

```bash
python scripts/generate_phase1_benchmarks.py
```

タイトル一覧を正本として、`benchmarks/generic` と `benchmarks/coding` に個別のYAMLを生成します。生成結果を直接編集せず、追加・修正は生成スクリプトのタイトル一覧で行います。

## 検証

```bash
python scripts/validate_phase1.py --check-fixtures
```

すべてのYAMLをJSON Schemaで検証し、benchmarkが参照するfixtureと必須ディレクトリの存在を確認します。Docker利用時は `docker compose run --rm evaluator` を使います。
