# Phase 7 Codex MCP 手動E2Eテスト

## E2E-MCP-001：CodexからMCP評価を開始して結果を確認できる

- 種別: 正常系

```powershell
docker compose --profile mcp up -d mcp
codex mcp add agent-eval -- docker compose --project-directory C:\Users\ITSUKI\agent-eval-engine exec -T mcp mcp run apps/mcp/server.py:mcp --transport stdio
codex mcp list
```

手順:

1. コマンドを実行する。
2. Codex を起動する。
3. `agent-eval MCP の run_benchmark を使い、GEN-TOOL-001 を dry-run で評価してください。` と入力する。
4. 返却された `run_id` を使い、`get_trace` で時系列イベントを取得するよう依頼する。

期待結果:

- `agent-eval` が Codex MCP一覧に表示される。
- `run_benchmark` の結果に `status: simulated`、UUID形式の `run_id`、6件以上の `event_count` が含まれる。
- `get_trace` の結果は `benchmark_loaded` を含み、イベントは時系列順である。
- MCP Serverの標準出力にDockerの起動ログや秘密情報は混在しない。

## E2E-MCP-002：Codexからlive実行を明示許可なしで拒否できる

- 種別: 異常系

```powershell
$env:AGENT_EVAL_MCP_ALLOW_LIVE = "0"
docker compose --profile mcp up -d --force-recreate mcp
```

手順:

1. `configs/phase3-local.yaml` の `engine.dry_run` を一時的に `false` にする。
2. コマンドを実行する。
3. Codex に `agent-eval MCP の run_benchmark で GEN-TOOL-001 を評価してください。` と依頼する。
4. 確認後、設定を元へ戻す。

期待結果:

- `AGENT_EVAL_MCP_ALLOW_LIVE=1` が必要である旨のエラーが返る。
- OpenRouter API 呼び出し、LLM費用、完了runは発生しない。
