# MCP Host 接続ガイド

## 対応方針

この Server は MCP の `stdio` transport を使います。したがって、ローカル stdio MCP Server を実行できる Host であれば利用できます。確認済みの設定形式は Codex、OpenCode、Antigravity、VS Code / GitHub Copilot です。Claude Code、Cursor、Cline、Windsurf なども stdio MCP 設定を持つ場合は、同じ Docker コマンドを登録できます。

Host ごとの UI や設定ファイル名は更新されるため、登録操作の直前に各 Host の公式ドキュメントも確認してください。

## 共通の準備

Docker Desktop を起動し、リポジトリを任意のローカルフォルダへ配置します。次に MCP 用コンテナを起動します。

```powershell
docker compose --profile mcp up -d mcp
```

期待結果: `mcp` と `db` が起動し、外部公開ポートは作成されません。

Host に登録する共通コマンドは次です。`C:\Users\<ユーザー名>\agent-eval-engine` は実際の絶対パスへ置き換えます。

```text
docker compose --project-directory C:\Users\<ユーザー名>\agent-eval-engine exec -T mcp mcp run apps/mcp/server.py:mcp --transport stdio
```

このコマンドの標準出力は MCP プロトコル専用です。Docker 起動ログを同じ接続に混在させないでください。

## Codex

```powershell
codex mcp add agent-eval -- docker compose --project-directory C:\Users\<ユーザー名>\agent-eval-engine exec -T mcp mcp run apps/mcp/server.py:mcp --transport stdio
codex mcp list
```

期待結果: `agent-eval` が一覧に表示される。

## OpenCode

OpenCode V2 の `opencode.json` で、`mcp.servers` に次を追加します。

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "agent-eval": {
        "type": "local",
        "command": [
          "docker",
          "compose",
          "--project-directory",
          "C:\\Users\\<ユーザー名>\\agent-eval-engine",
          "exec",
          "-T",
          "mcp",
          "mcp",
          "run",
          "apps/mcp/server.py:mcp",
          "--transport",
          "stdio"
        ],
        "timeout": {
          "startup": 45000,
          "execution": 600000
        }
      }
    }
  }
}
```

期待結果: OpenCode は `agent-eval_*` の MCP ツールを検出する。作業ディレクトリが異なる場合も、`--project-directory` により正しい Compose プロジェクトを使う。

## Antigravity

Antigravity の **Settings > Customizations > Open MCP Config** を開きます。プロジェクト単位では `.agents/mcp_config.json`、グローバルでは `~/.gemini/config/mcp_config.json` が利用できます。`mcpServers` に次を追加します。

```json
{
  "mcpServers": {
    "agent-eval": {
      "command": "docker",
      "args": [
        "compose",
        "--project-directory",
        "C:\\Users\\<ユーザー名>\\agent-eval-engine",
        "exec",
        "-T",
        "mcp",
        "mcp",
        "run",
        "apps/mcp/server.py:mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

期待結果: Antigravity の Installed MCP Servers に `agent-eval` が表示され、個別ツールを有効／無効にできる。

## VS Code / GitHub Copilot

ワークスペースの `.vscode/mcp.json` を作成または編集します。

```json
{
  "servers": {
    "agent-eval": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "compose",
        "--project-directory",
        "C:\\Users\\<ユーザー名>\\agent-eval-engine",
        "exec",
        "-T",
        "mcp",
        "mcp",
        "run",
        "apps/mcp/server.py:mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

期待結果: コマンドパレットの `MCP: List Servers` に `agent-eval` が現れ、Host が起動していることを確認できる。

Windows 版 VS Code の MCP sandbox は現時点で利用できないため、信頼したローカルリポジトリでのみ Server を有効化してください。

## 初回の安全な利用方法

1. 最初は `configs/phase3-local.yaml` の `engine.dry_run: true` を維持する。
2. Host から `run_benchmark` に `GEN-TOOL-001` と `source: sample` を渡す。
3. 返った `run_id` を `get_trace` に渡し、`benchmark_loaded` を含むイベントを確認する。
4. live LLM を使う場合だけ、`engine.dry_run: false` と `AGENT_EVAL_MCP_ALLOW_LIVE=1` を両方設定して `mcp` を再作成する。

## 接続解除

Host 側の MCP 設定から `agent-eval` を削除または無効化し、次を実行します。

```powershell
docker compose --profile mcp down
```

期待結果: MCP と DB が停止する。`postgres_data` volume は保持される。

## 公式情報

- [OpenCode MCP servers](https://dev.opencode.ai/v2/docs/mcp-servers/)
- [Google Antigravity MCP setup](https://developers.google.com/knowledge/mcp)
- [VS Code MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
- [VS Code MCP server management](https://code.visualstudio.com/docs/agent-customization/mcp-servers)
- [Codex MCP](https://developers.openai.com/learn/docs-mcp)
