# Phase 7 複数 MCP Host 手動E2Eテスト

対象: Codex、OpenCode、Antigravity、VS Code / GitHub Copilot など、stdio MCP Server を実行できる Host。

## E2E-MCP-003：任意のMCP Hostからローカル評価を開始して履歴を取得できる

- 種別: 正常系

```powershell
docker compose --profile mcp up -d mcp
docker compose --profile mcp ps
```

手順:

1. コマンドを実行する。
2. `docs/MCP_CLIENT_SETUP.md` の該当 Host の設定を登録する。
3. Host の MCP Server 一覧で `agent-eval` を有効化する。
4. Host に `agent-eval の run_benchmark を使い、GEN-TOOL-001 を sample の dry-run で評価してください。` と依頼する。
5. 返却された `run_id` を使い、Host に `get_trace` を依頼する。

期待結果:

- `db` は `healthy`、`mcp` は `running` と表示される。
- Host は 7 件の `agent-eval` ツールを表示する。
- `run_benchmark` の結果には UUID 形式の `run_id`、`status: simulated`、6件以上の `event_count` が含まれる。
- `get_trace` の結果には `benchmark_loaded` を含む時系列イベントがある。
- API キー、token、password は Host の応答に表示されない。

## E2E-MCP-004：MCPコンテナ未起動時に接続失敗を案内できる

- 種別: 異常系

```powershell
docker compose --profile mcp down
docker compose --profile mcp ps
```

手順:

1. コマンドを実行する。
2. Host で `agent-eval` MCP Server の接続または再接続を実行する。
3. Host の MCP Server 状態またはログを確認する。

期待結果:

- `mcp` と `db` は `running` ではない。
- Host は Server へ接続できず、ツールを利用可能として表示しない。
- Host は Host 側のログまたは状態画面で接続失敗を確認できる。
- DB、benchmark、既存 run の内容は変更されない。

## E2E-MCP-005：live実行を明示許可なしで拒否できる

- 種別: 異常系

```powershell
$env:AGENT_EVAL_MCP_ALLOW_LIVE = "0"
docker compose --profile mcp up -d --force-recreate mcp
```

手順:

1. `configs/phase3-local.yaml` の `engine.dry_run` を一時的に `false` に変更する。
2. コマンドを実行する。
3. Host から `run_benchmark` を実行する。
4. 確認後、`engine.dry_run` を元へ戻す。

期待結果:

- `AGENT_EVAL_MCP_ALLOW_LIVE=1` が必要であるエラーが返る。
- OpenRouter API 呼び出しと LLM 費用は発生しない。
- 新しい完了 run は保存されない。
