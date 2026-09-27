# セットアップと初期化ガイド (Setup Guide)

インストール後、Agent Eval Engine を使用開始するための初期化・環境設定手順です。

---

## 1. 初回初期化コマンド (`agent-eval init`)

端末で以下のコマンドを実行します。

```bash
agent-eval init
```

### このコマンドが実行すること
1. **OS 標準のユーザーデータ保存先** を作成します。
   - **Windows**: `%LOCALAPPDATA%\AgentEvalEngine\`
   - **macOS**: `~/Library/Application Support/AgentEvalEngine/`
   - **Linux**: `~/.local/share/agent-eval-engine/`
2. 上記フォルダ内に以下のサブディレクトリを作成します。
   - `config/`: 設定ファイル (`engine.yaml`, `.env`)
   - `datasets/`: ユーザー独自の評価用データセット
   - `agent-traces/`: Real Coding Agent (Codex, OpenCode等) から取り込んだ実行記録
   - `exports/`: CSV 出力ファイル
   - `logs/`: 実行ログ、MCP 通信ログ
   - `diagnostics/`: 診断ログ
3. サンプル benchmark (`GEN-TOOL-001`) をユーザー環境に展開します。
4. Docker Compose サービス（PostgreSQL データベース等）を起動・待機します。
5. データベース migration (Alembic) を適用し、スキーマを最新にします。
6. 初期 dry-run 評価を実行し、正常に稼働することを確認します。

---

## 2. 環境設定ファイル (`config/.env`)

デフォルトでは `dry_run: true` が有効になっており、外部 LLM API を呼び出さずに安全に動作します。
実際の LLM (OpenRouter 経由等) による評価を行いたい場合のみ、設定ディレクトリ内の `.env` を編集します。

### 設定例 (`%LOCALAPPDATA%\AgentEvalEngine\config\.env`)
```bash
# データベース接続 (ローカル Docker コンテナ)
DATABASE_URL=postgresql://agent_eval:agent_eval@localhost:5432/agent_eval

# 外部 LLM API キー (live LLM 評価を行う場合のみ設定)
OPENROUTER_API_KEY=sk-or-v1-...
```

> [!NOTE]
> 設定ファイル内の API キーや認証情報は、ログや画面、エクスポートファイルには一切出力されません。

---

## 3. 環境診断コマンド (`agent-eval doctor`)

設定の変更後や問題発生時は、いつでも診断コマンドを実行できます。

```bash
agent-eval doctor
```

JSON 形式で結果を取得する場合 (スクリプト連携・CI用):
```bash
agent-eval doctor --json
```

診断項目:
- Docker デーモンの稼働状態
- Docker Compose の導入状況
- ユーザーデータ保存先の書き込み権限
- PostgreSQL データベースへの接続性
- データベースマイグレーションの最新状態
- MCP Server の登録状況

すべての項目で `[OK]` が表示されれば準備完了です。
引数なしで `agent-eval` を実行して TUI を起動するか、CLI コマンドを実行してください。
