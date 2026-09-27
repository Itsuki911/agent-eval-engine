# トラブルシューティングガイド (Troubleshooting Guide)

Agent Eval Engine の使用中に問題が発生した場合の診断と解決手順です。

---

## 1. 最初に確認すること: `agent-eval doctor`

問題が発生した場合、まず環境診断コマンドを実行してください。

```bash
agent-eval doctor
```

診断コマンドは、システム構成（Docker、PostgreSQL、ストレージ、MCP）を検査し、以下の形式で原因と解決策を具体的に提示します。

```text
【原因】Docker デーモンに接続できませんでした。
【次の操作】Docker Desktop が起動しているか確認してください。
【詳細ログ】%LOCALAPPDATA%\AgentEvalEngine\logs\doctor.log
```

---

## 2. よくある問題と解決策

### Q1. "Docker daemon is not running" エラーが出る
- **原因**: Docker Desktop が未起動、またはサービスが停止しています。
- **対処法**:
  - Windows / macOS: Docker Desktop を起動し、アイコンが「Running」になるまで待機します。
  - Linux: `sudo systemctl start docker` を実行します。

### Q2. "Database connection refused" (ポート 5432 の競合)
- **原因**: 既存の PostgreSQL がローカルポート 5432 を占有しているか、DB コンテナが起動していません。
- **対処法**:
  - `agent-eval init` を再度実行してコンテナを起動します。
  - 既存の PostgreSQL とポートが競合している場合、`.env` の `DATABASE_PORT` を 5433 等に変更してください。

### Q3. "Migration pending" エラーが出る
- **原因**: データベーススキーマのバージョンが古くなっています。
- **対処法**:
  - `agent-eval init` を実行すると自動で最新の migration が適用されます。

### Q4. JSONL 取込時に "Secret detected" で拒絶される
- **原因**: 取り込もうとした `.jsonl` ファイル内に、API キー (`api_key`)、`Authorization` ヘッダー、パスワード等の文字列が含まれています。
- **対処法**:
  - トランスクリプトファイルをテキストエディタで開き、認証トークンやパスワードを `<REDACTED>` 等に置換してから再度取り込んでください。

### Q5. MCP 接続時に Codex / OpenCode から応答がない
- **原因**: Docker コンテナが停止しているか、stdout に余計なログが混入している可能性があります。
- **対処法**:
  - `agent-eval mcp status` で待機状態を確認します。
  - プロトコル以外のログはすべて stderr に出力される仕様ですが、コンテナの再起動 (`agent-eval mcp start`) を試してください。

---

## 3. 診断ログの採取

サポートに問い合わせる場合や Issue を作成する場合は、以下のコマンドで診断レポートを生成できます。
（※ 機密情報やローカルパスは自動的にサニタイズされます）

```bash
agent-eval doctor --json > diagnostics.json
```
