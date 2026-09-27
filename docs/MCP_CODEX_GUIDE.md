# Codex MCP 接続ガイド (Codex MCP Integration Guide)

Agent Eval Engine は、OpenAI Codex CLI などの MCP Host から評価機能や Trace 検査機能を呼び出せる MCP Server 機能を標準搭載しています。

利用者がプロジェクトの内部パスや Docker コマンドを直接意識することなく、`agent-eval` コマンドを通じて Codex にワンクリックで連携できます。

---

## 1. ワンコマンドによる自動登録

端末で以下のコマンドを実行します。

```text
agent-eval mcp install codex
```

### 実行内容
1. `codex` CLI がインストールされているか確認します。
2. 以下の登録コマンドを案内、または自動実行します:
   ```bash
   codex mcp add agent-eval -- agent-eval mcp serve --stdio
   ```
3. 登録が完了すると、Codex から直接 Agent Eval Engine の全ツールが利用可能になります。

---

## 2. MCP Server の動作仕様 (`agent-eval mcp serve --stdio`)

Codex などの MCP Host が内部で呼び出す起動コマンドです。

```text
agent-eval mcp serve --stdio
```

### 責務と安全設計
1. **データ保存先の確認**: OS 標準の保存先ディレクトリが存在することを確認します。
2. **Docker / DB 健全性チェック**: バックエンドコンテナの待機状態を確認します。
3. **プロトコル分離 (厳格)**:
   - JSON-RPC 2.0 (MCP プロトコル) は **stdout のみ** に出力します。
   - 起動ログ、進捗メッセージ、エラー詳細はすべて **stderr** に出力します。
   - これにより、Codex 側の JSON パーサーが破損することはありません。
4. **子プロセスのライフサイクル連動**:
   - Codex がセッションを終了（stdin が EOF またはパイプ切断）した際、バックグラウンドの子プロセスを安全に終了させ、ゾンビプロセスを残しません。

---

## 3. 利用可能な MCP ツール一覧

Codex から以下の 8 つのツールを呼び出すことができます。

| ツール名 | 説明 | 主要引数 |
| --- | --- | --- |
| `run_benchmark` | 指定した benchmark を評価実行 | `benchmark_id`, `dry_run` |
| `get_run` | 過去の実行結果・メトリクスを取得 | `run_id` |
| `get_trace` | 実行の時系列イベント（プロンプト・ツール呼出・応答）を取得 | `run_id`, `limit` |
| `compare_runs` | 2 つの実行結果を比較 (成功率, コスト, 遅延) | `left_run_id`, `right_run_id` |
| `list_benchmarks` | 利用可能な benchmark 一覧を取得 | `category` |
| `list_runs` | 過去の実行履歴一覧を取得 | `limit`, `status` |
| `import_agent_trace` | Real Coding Agent の JSONL 記録を取り込む | `transcript_file` |
| `export_runs_csv` | 実行結果を CSV 形式でエクスポート | `output_file` |

---

## 4. 登録状態と動作確認

Codex への登録状態を確認するには:
```text
agent-eval mcp status
```

Codex 内で Agent Eval Engine をテストするには:
```text
codex
> agent-eval の list_benchmarks ツールを使って利用可能なベンチマークを教えてください。
```

---

## 5. 安全性と注意事項
- デフォルトの `dry_run: true` 設定により、無制限な外部 LLM 課金は発生しません。
- トレース取込時 (`import_agent_trace`) に API キーや Authorization ヘッダーが検出された場合、MCP レベルで安全に拒絶されます。
