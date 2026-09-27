# MCPB 配布手動E2Eテスト

## E2E-MCPB-001：MCPB bundleを作成してSmithery公開用ファイルを生成できる

- 種別: 正常系

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_mcpb.ps1
npx.cmd --yes @anthropic-ai/mcpb info .\dist\agent-eval-engine.mcpb
```

手順:

1. コマンドを実行する。
2. `mcpb info` の出力を確認する。
3. `dist\agent-eval-engine.mcpb` が作成されたことを確認する。

期待結果:

- `dist\agent-eval-engine.mcpb` が1個作成される。
- manifest の名前は `agent-eval-engine`、version は `0.1.0` である。
- bundle は `run_benchmark`、`get_trace`、`compare_runs` を含む7ツールの定義を持つ。
- bundle 内に `.env` または `.env.*` が含まれない。
- bundle は既定でホスト側 PostgreSQL ポート `15432` を使い、開発用の `5432` と衝突しない。

## E2E-MCPB-002：MCPB bundleに秘密情報ファイルを含めず作成できる

- 種別: 異常系

```powershell
Set-Content -LiteralPath .\build\mcpb\.env -Value "OPENROUTER_API_KEY=not-a-real-key"
powershell -ExecutionPolicy Bypass -File .\scripts\build_mcpb.ps1
```

手順:

1. 初回の build を実行する。
2. コマンドを実行する。
3. build 結果を確認する。
4. `build\mcpb\.env` が残っていないことを確認する。

期待結果:

- build は staging directory を再作成するため、手動で作った `.env` は bundle に残らない。
- 生成済み bundle に `OPENROUTER_API_KEY=not-a-real-key` は含まれない。
- 実在する API キーをテストデータに使用しない。

## E2E-MCPB-003：MCPB bundleをSmitheryへ公開できる

- 種別: 正常系

```powershell
smithery auth whoami
smithery namespace use neymar020510
smithery mcp publish .\dist\agent-eval-engine.mcpb -n neymar020510/agent-eval-engine
```

手順:

1. bundle 作成済みであることを確認する。
2. コマンドを実行する。
3. Smithery の公開結果を確認する。

期待結果:

- 認証済みの Smithery アカウントが表示される。
- `agent-eval-engine.mcpb` が指定され、ENOENT は発生しない。
- `neymar020510/agent-eval-engine` として公開処理が開始または完了する。
- Smithery に API キー、`.env`、PostgreSQL 接続文字列が表示されない。
