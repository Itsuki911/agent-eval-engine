# 外部実行版評価エンジン Notebook の手動 E2E テスト

## E2E-NOTEBOOK-001 外部Notebookでdry-runを実行して履歴を復元できる（正常系）

実行コマンド:

```powershell
ブラウザで https://colab.research.google.com/ を開く
```

1. 実行コマンドを実行する。
2. `examples/evaluation_engine_python_walkthrough.ipynb` をアップロードして開く。
3. Notebook の全セルを上から順に実行する。
4. 結果表示を確認する。

期待結果: 正常系。ローカル PostgreSQL、benchmark、fixture、`status: simulated`、events の順序付き履歴、metrics が表示される。PostgreSQL に新しい run、8件の events、16件の metrics、1件の evaluation が保存される。

## E2E-NOTEBOOK-002 外部PostgreSQL接続先が不正なら失敗を確認できる（異常系）

実行コマンド:

```powershell
$env:DATABASE_URL = "postgresql://invalid:invalid@localhost:1/invalid"
```

1. 外部の Python Notebook 環境で実行コマンド相当の環境変数を設定する。
2. Notebook の「PostgreSQL テーブルを作成する」セルを実行する。
3. 接続エラーを確認する。

期待結果: 異常系。接続エラーが表示され、評価データは保存されない。接続可能な `DATABASE_URL` を設定するか、環境変数を削除して最初のセルを再実行すると復帰できる。
