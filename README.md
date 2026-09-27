# Agent Eval Engine

Agent Eval Engine は、AI Coding Agent の実行を **評価・記録・分析・比較** するローカル実行型の評価基盤です。
評価データセットを使った dry-run / LLM 評価、実行履歴の時系列表示、実際の Coding Agent (Codex, OpenCode, Antigravity) の記録取込を行えます。

利用者は単一の `agent-eval` コマンドを通じて、直感的な TUI (ターミナルUI) や自動化向け CLI、MCP Server を利用できます。

---

## 主な機能

- **ワンコマンド起動**: 単一バイナリ `agent-eval` から TUI または CLI を起動
- **100% ローカル保存**: 評価データ、PostgreSQL、API キー、履歴はすべて利用者の PC 内に保持
- **直感的な TUI**: キーボード操作で評価実行、Trace タイムライン再生、比較、Agent 記録取込
- **Real Coding Agent 記録取込**: Codex, OpenCode, Antigravity などの実行記録 (`.jsonl`) を共通スキーマで分析
- **MCP サーバー統合**: Codex や Antigravity 等の MCP Host からワンクリックで評価ツールを呼び出し
- **環境自動診断**: `agent-eval doctor` による Docker・DB・設定の日本語診断と修復案内

---

## 必要な環境

- **OS**: Windows (x86_64, ARM64), macOS (Apple Silicon, Intel), Linux (x86_64)
- **Docker Desktop** または **Docker Engine** (Compose v2 対応)
  - 評価エンジン (Python) と PostgreSQL は Docker 内で安全に分離実行されます。
  - ※ ホスト端末に Python や Go の開発環境をインストールする必要はありません。

---

## インストール

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```
※ `%LOCALAPPDATA%\Programs\AgentEvalEngine` にインストールされ、自動的に `PATH` に追加されます。

### macOS / Linux
GitHub Releases よりお使いの OS に対応したアーカイブ (`tar.gz`) をダウンロードし、解凍した `agent-eval` を `/usr/local/bin` 等に配置します。

```bash
tar -xzf agent-eval-<os>-<arch>.tar.gz
chmod +x agent-eval
sudo mv agent-eval /usr/local/bin/
```
詳細は [インストールガイド (docs/INSTALL.md)](docs/INSTALL.md) を参照してください。

---

## 最短の使い方 (Quick Start)

### 1. 初回セットアップ
```bash
agent-eval init
```
OS 標準のデータ保存先を作成し、Docker コンテナの準備、データベースマイグレーション、サンプルベンチマークの展開、初期動作確認 (dry-run) を自動で行います。

### 2. 環境診断
```bash
agent-eval doctor
```
Docker、DB、保存先、MCP 環境の健全性を診断し、問題があれば解決手順を日本語で案内します。

### 3. TUI を起動する
引数なしで実行すると、全画面 TUI が起動します。
```bash
agent-eval
```
矢印キー・Enter で「新しい評価を開始」「Trace を見る」「Real Agent 記録取込」などを操作できます (`q` で終了、`Esc`/`b` で戻る)。

### 4. CLI から評価を実行する
```bash
agent-eval run GEN-TOOL-001
```
機械可読な JSON 出力が必要な場合:
```bash
agent-eval run GEN-TOOL-001 --json
```

---

## Real Coding Agent の記録を取り込む

Codex や OpenCode が出力した実行トランスクリプト (`.jsonl`) を取り込み、時系列 Trace を分析できます。

### 1. 形式の事前検証
```bash
agent-eval validate-trace fixtures/agent-traces/codex-success.jsonl
```

### 2. 取り込み実行
```bash
agent-eval import-trace fixtures/agent-traces/codex-success.jsonl
```

### 3. Trace タイムラインの確認
```bash
agent-eval trace <run-id>
```
※ 安全のため、API キーや Authorization ヘッダー、不正なパストラバーサルを含むファイルは自動的に拒否されます。詳細は [Trace 取込ガイド (docs/TRACE_GUIDE.md)](docs/TRACE_GUIDE.md) を参照してください。

---

## Codex / MCP Host から利用する

### 1. Codex へのワンコマンド登録
```bash
agent-eval mcp install codex
```
自動的に Codex へ `agent-eval mcp serve --stdio` が登録されます。

### 2. 手動登録の場合
```bash
codex mcp add agent-eval -- agent-eval mcp serve --stdio
```
標準入出力 (stdio) 経由で `run_benchmark`, `get_trace`, `compare_runs`, `import_agent_trace` などのツールが利用可能になります。
詳細は [Codex MCP 接続ガイド (docs/MCP_CODEX_GUIDE.md)](docs/MCP_CODEX_GUIDE.md) を参照してください。

---

## ユーザーデータの保存先

ユーザーのデータはリポジトリ外の OS 標準ディレクトリに安全に分離保存されます。

- **Windows**: `%LOCALAPPDATA%\AgentEvalEngine\`
- **macOS**: `~/Library/Application Support/AgentEvalEngine/`
- **Linux**: `~/.local/share/agent-eval-engine/`

保存内容:
- `config/`: 設定ファイル (`.env`)
- `datasets/`: ユーザー独自ベンチマーク
- `agent-traces/`: 取り込んだトランスクリプト
- `exports/`: CSV 出力ファイル
- `logs/`: 実行ログ・MCP 通信ログ
- `diagnostics/`: 診断レポート

---

## ドキュメント一覧

- [インストールガイド (docs/INSTALL.md)](docs/INSTALL.md)
- [セットアップと初期化 (docs/SETUP.md)](docs/SETUP.md)
- [TUI 操作ガイド (docs/TUI_GUIDE.md)](docs/TUI_GUIDE.md)
- [Codex MCP 接続ガイド (docs/MCP_CODEX_GUIDE.md)](docs/MCP_CODEX_GUIDE.md)
- [OpenCode MCP 接続ガイド (docs/MCP_OPENCODE_GUIDE.md)](docs/MCP_OPENCODE_GUIDE.md)
- [Google Antigravity MCP 接続ガイド (docs/MCP_ANTIGRAVITY_GUIDE.md)](docs/MCP_ANTIGRAVITY_GUIDE.md)
- [Real Agent トレース取込ガイド (docs/TRACE_GUIDE.md)](docs/TRACE_GUIDE.md)
- [トラブルシューティング (docs/TROUBLESHOOTING.md)](docs/TROUBLESHOOTING.md)
- [よくある質問 (FAQ) (docs/FAQ.md)](docs/FAQ.md)
- [セキュリティとプライバシー (docs/SECURITY_PRIVACY.md)](docs/SECURITY_PRIVACY.md)
- [アップグレードとアンインストール (docs/UNINSTALL_UPGRADE.md)](docs/UNINSTALL_UPGRADE.md)
- [GitHub Releases 配布と SBOM (docs/GITHUB_RELEASE_DISTRIBUTION.md)](docs/GITHUB_RELEASE_DISTRIBUTION.md)

---

## セキュリティ

- 本ツールは完全ローカル完結型です。明示的に外部 LLM API を設定しない限り、外部通信は一切発生しません。
- ログやトレース、診断出力には API キーやパスワード等の秘密情報は一切含まれません。
- 脆弱性報告等は [セキュリティポリシー (SECURITY.md)](SECURITY.md) をご確認ください。
