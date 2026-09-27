# Google Antigravity / Claude Desktop MCP 接続ガイド

Google Antigravity、Claude Desktop、VS Code GitHub Copilot 等の MCP 対応クライアントから Agent Eval Engine を呼び出す手順です。

---

## 1. 設定方法

各クライアントの MCP 設定ファイル（例: `claude_desktop_config.json` または Antigravity MCP 設定）を開き、`agent-eval` を stdio サーバーとして登録します。

### 設定例 (`mcp_config.json`)
```json
{
  "mcpServers": {
    "agent-eval": {
      "command": "agent-eval",
      "args": ["mcp", "serve", "--stdio"]
    }
  }
}
```

Windows 環境で絶対パスを指定する場合:
```json
{
  "mcpServers": {
    "agent-eval": {
      "command": "C:\\Users\\<ユーザー名>\\AppData\\Local\\Programs\\AgentEvalEngine\\agent-eval.exe",
      "args": ["mcp", "serve", "--stdio"]
    }
  }
}
```

---

## 2. 安全性設計

- **完全標準ストリーム分離**: プロトコルメッセージ (JSON-RPC) のみが `stdout` に送出され、診断・デバッグログはすべて `stderr` に出力されるため、クライアントの接続パーサーがエラーを起こしません。
- **データローカリティ**: 評価対象コードやログはローカルの Docker / データベース内に保持され、外部クライアントへ渡されるのはツールの実行結果・要約のみです。
- **機密情報の遮断**: トレースデータや実行ログに含まれる API キーやトークンは自動的にマスク・排除されます。

---

## 3. よく使われるツールとプロンプト例

### ベンチマーク評価の実行
```text
ユーザー: GEN-TOOL-001 ベンチマークを dry-run で評価して結果を教えてください。
アシスタント: run_benchmark(benchmark_id="GEN-TOOL-001", dry_run=true) を呼び出します。
```

### 実行履歴の比較
```text
ユーザー: 直近の 2 つの実行結果 (run-a と run-b) のレイテンシと成功率を比較してください。
アシスタント: compare_runs(left_run_id="run-a", right_run_id="run-b") を呼び出します。
```
