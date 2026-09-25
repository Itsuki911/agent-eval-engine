# Phase 5: CSV Export 回帰テスト

## RT-EXPORT-001 CSVをホスト保存先へ出力できる（回帰）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `.env` の `AGENT_EVAL_HOST_DOWNLOAD_DIR` を Windows の Downloads パスまたは任意のローカルディレクトリに設定する。
2. TUI の実行履歴で `e` を押す。
3. 表示された保存先を確認する。
4. ホスト PC 上で保存先フォルダを開く。

期待結果: 回帰。表示されるパスは `/root/Downloads` や `/exports` ではなく、`.env` に指定したホスト側のパスになる。CSV はそのフォルダに存在し、先頭に UTF-8 BOM を持つ。

## RT-EXPORT-002 CSV保存先未設定時に安全な既定先を使う（境界値）

```powershell
docker compose --profile tui run --rm --build tui
```

1. `.env` から `AGENT_EVAL_HOST_DOWNLOAD_DIR` を一時的に外す。
2. TUI の実行履歴で `e` を押す。

期待結果: 境界値。プロジェクト直下の `exports` が保存先として表示され、コンテナ内専用の `/root/Downloads` は表示されない。
