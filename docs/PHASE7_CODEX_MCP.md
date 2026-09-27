# Phase 7: Codex から MCP を利用する

この手順はローカル開発用である。MCP Server は HTTP 公開せず、Codex と Docker コンテナを標準入出力で接続する。

## 1. MCP 実行環境を起動する

```powershell
docker compose --profile mcp up -d mcp
```

期待結果: `agent-eval-engine-mcp-1` と `agent-eval-engine-db-1` が起動する。MCP通信はまだ開始しない。

## 2. Codex にローカル MCP Server を登録する

プロジェクトの絶対パスを自分の環境に合わせて指定する。

```powershell
codex mcp add agent-eval -- docker compose --project-directory C:\Users\ITSUKI\agent-eval-engine exec -T mcp mcp run apps/mcp/server.py:mcp --transport stdio
codex mcp list
```

期待結果: `agent-eval` が一覧に表示される。`docker compose up` の起動ログは MCP の標準出力へ混在しない。

## 3. Codex から評価を開始する

Codex を起動し、次のように依頼する。

```text
agent-eval MCP の run_benchmark を使い、GEN-TOOL-001 を dry-run で評価してください。結果の run_id と task_success を報告してください。
```

期待結果:

- `run_benchmark` が1回呼ばれる。
- `status` は `simulated` である。
- `run_id`、`event_count`、metrics が返る。
- `get_trace` を使うと `benchmark_loaded` を含む時系列イベントを確認できる。

## 4. live LLM 実行を許可する場合

live実行は料金発生の可能性がある。設定ファイルの `engine.dry_run: false` と、次の環境変数の両方が必要である。

```powershell
$env:AGENT_EVAL_MCP_ALLOW_LIVE = "1"
docker compose --profile mcp up -d --force-recreate mcp
```

期待結果: `AGENT_EVAL_MCP_ALLOW_LIVE=1` がない限り、MCPはlive LLM評価を拒否する。

## 5. 終了する

```powershell
docker compose --profile mcp down
```

期待結果: MCPとDBコンテナが停止する。PostgreSQL volume は削除されない。
