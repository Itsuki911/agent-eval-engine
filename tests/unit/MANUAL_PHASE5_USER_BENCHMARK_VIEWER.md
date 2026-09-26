# Phase 5 自作benchmark YAML閲覧の手動テスト

対象はホーム画面の`自作benchmarkを確認する`である。ここでは評価を実行せず、利用者が保存したYAML原文だけを確認する。

## UT-VIEWER-001 自作benchmarkを選択してYAML原文を確認できる（正常系）

実行コマンド:

```powershell
docker compose --profile tui run --rm --build tui
```

1. 自作benchmarkを1件以上作成する。
2. 実行コマンドを実行する。
3. ホーム画面で`自作benchmarkを確認する`を選ぶ。
4. Enterキーを押す。
5. 作成したbenchmark IDを選ぶ。
6. Enterキーを押す。
7. 表示されたYAMLの`id`、`title`、`family`を確認する。
8. 下矢印キーを押して続きのYAMLを確認する。
9. `b`キーを押して一覧へ戻る。

期待結果: 正常系。自作benchmarkだけが一覧に表示され、サンプルbenchmarkは混在しない。選択した`GEN-DATA-001`などのIDに対応するYAML原文と保存パスが表示される。矢印キーでYAMLをページ単位にスクロールでき、`b`キーで自作一覧へ戻る。評価は開始されず、実行履歴も追加されない。

## UT-VIEWER-002 自作benchmarkがない状態で空一覧の案内を確認できる（異常系）

実行コマンド:

```powershell
docker compose --profile tui run --rm --build tui
```

1. 自作benchmarkを保存していないローカルデータ保存先を使用する。
2. 実行コマンドを実行する。
3. ホーム画面で`自作benchmarkを確認する`を選ぶ。
4. Enterキーを押す。
5. 空一覧の案内を確認する。
6. `b`キーを押してホーム画面へ戻る。

期待結果: 異常系。`自作benchmarkはまだありません。ホーム画面の c から作成できます。`が表示される。空一覧でEnterを押してもエラー画面や評価開始画面へ遷移しない。`b`キーでホーム画面へ戻れる。
