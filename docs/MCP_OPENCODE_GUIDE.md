# OpenCode MCP 接続ガイド (OpenCode MCP Integration Guide)

OpenCode から Agent Eval Engine の評価基盤および Trace 機能を呼び出すための設定手順です。

---

## 1. 設定の概要

OpenCode は stdio トランスポートによる MCP 接続に対応しています。
`agent-eval mcp serve --stdio` コマンドを MCP サーバーとして指定することで、評価・比較・履歴取得が可能になります。

---

## 2. 設定ファイルの編集

OpenCode の設定ファイル（通常は `~/.config/opencode/config.json` または OpenCode の設定画面）に以下のエントリーを追加します。

### 設定例 (`config.json`)
```json
{
  "mcpServers": {
    "agent-eval": {
      "command": "agent-eval",
      "args": ["mcp", "serve", "--stdio"],
      "env": {}
    }
  }
}
```

※ Windows 環境で `agent-eval` が PATH に通っていない場合は、フルパス（例: `C:\\Users\\<ユーザー名>\\AppData\\Local\\Programs\\AgentEvalEngine\\agent-eval.exe`）を指定してください。

---

## 3. 動作確認

OpenCode を起動し、チャット画面で以下のように指示します。

```text
/mcp agent-eval list_benchmarks
```
または自然言語で:
```text
agent-eval ツールを使って、登録されているベンチマーク一覧を取得してください。
```

---

## 4. トラブルシューティング
- **接続がタイムアウトする**: Docker Desktop が起動しているか `agent-eval doctor` で確認してください。
- **ツール呼出時にエラーが返る**: OS ユーザーデータ保存先 (`%LOCALAPPDATA%\AgentEvalEngine\logs\mcp.log`) のログを確認してください。
