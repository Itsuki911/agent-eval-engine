# よくある質問 (FAQ)

Agent Eval Engine に関するよくある質問とその回答です。

---

### Q1. ホスト端末に Python や Go の実行環境が必要ですか？
**いいえ、不要です。**
配布される `agent-eval` はネイティブコンパイルされた単一の Go バイナリです。
また、Python 評価エンジンや PostgreSQL データベースは Docker Compose 内で自動実行されるため、利用者の端末環境を汚しません。

---

### Q2. 評価データや実行ログが外部サーバーに送信されることはありますか？
**いいえ、一切送信されません。**
Agent Eval Engine は 100% ローカル完結型アーキテクチャを採用しています。
評価データセット、実行ログ、トレース記録、データベースはすべて利用者の端末内（`%LOCALAPPDATA%\AgentEvalEngine` 等）に保存されます。
テレメトリや外部トラッキング機能も含まれていません。

※ 唯一の例外は、利用者が明示的に `.env` に `OPENROUTER_API_KEY` を設定し、`dry_run: false` で live LLM 評価を実行した場合に、評価プロンプトが指定された LLM プロバイダーに送信される点のみです。

---

### Q3. Docker なしで動かすことはできますか？
現在は Docker Desktop または Docker Engine が必須です。
評価対象コードがファイルシステムやシステムコマンドを破壊しないよう、Docker コンテナによるサンドボックス隔離と PostgreSQL による高速な検索・比較機能を提供するためです。

---

### Q4. 評価結果をチームメンバーに共有したい場合はどうすればよいですか？
以下の方法が利用できます。
1. **CSV エクスポート**:
   `agent-eval` TUI または MCP `export_runs_csv` を使用して、メトリクス一覧を CSV として出力できます。
2. **JSON 出力**:
   `agent-eval run <id> --json` や `agent-eval show <id> --json` を利用して、CI パイプラインやレポートツールと連携できます。

---

### Q5. データのバックアップはどのように行いますか？
以下の 2 箇所をバックアップしてください。
1. OS のユーザーデータ保存先フォルダ:
   - Windows: `%LOCALAPPDATA%\AgentEvalEngine\`
   - macOS: `~/Library/Application Support/AgentEvalEngine/`
   - Linux: `~/.local/share/agent-eval-engine/`
2. Docker のボリュームデータ (PostgreSQL):
   `docker compose` の `postgres_data` ボリューム。
