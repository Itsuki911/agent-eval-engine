# Phase 5: Dataset Storage 手動テスト

## IT-DATASET-001 自作datasetをホスト側へ保存して再利用できる（正常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `.env` の `AGENT_EVAL_HOST_DATA_DIR` を確認する。
2. TUI で自作 benchmark を保存する。
3. TUI を終了する。
4. 指定保存先の `datasets/user/generic` または `datasets/user/coding` を開く。
5. TUI を再起動する。
6. `新しい評価を開始する` を開く。
7. `s` を押して `user-created` を選ぶ。

期待結果: 正常系。ホスト側に YAML が存在し、再起動後も一覧に `user-created` として表示される。Docker コンテナを削除してもデータセットは残る。

## IT-DATASET-002 sample ZIPを検証して導入できる（正常系）

```powershell
docker compose --profile engine run --rm engine python scripts/build_sample_package.py --output dist/phase1-samples-v1.zip
docker compose --profile tui run --rm --build --entrypoint python tui scripts/tui_backend.py install-sample --package /workspace/dist/phase1-samples-v1.zip
```

1. sample ZIP を生成する。
2. 導入コマンドを実行する。
3. 導入先の `datasets/samples/phase1-samples-v1` を確認する。

期待結果: 正常系。manifest、benchmark YAML、fixture が同じ package 配下に展開される。既存 sample YAML は書き換えられない。

## IT-DATASET-003 改ざんされたsample ZIPを拒否できる（異常系）

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_sample_package.py -k tampered
```

1. コマンドを実行する。

期待結果: 異常系。ハッシュ不一致が検出され、展開先ディレクトリは作成されない。

## IT-DATASET-004 sampleと自作datasetを切り替えられる（正常系）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `新しい評価を開始する` を開く。
2. `s` を繰り返し押す。

期待結果: 正常系。`source: all`、`source: sample`、`source: user-created` の順に切り替わり、一覧の候補数・内容が対応して変わる。
