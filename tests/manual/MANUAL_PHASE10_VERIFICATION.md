# Phase 10 手動テスト仕様書: 一般提供向け Packaging / Distribution / CLI-TUI 統合

## 概要

本ドキュメントは、Agent Eval Engine の Phase 10（一般提供向け配布・CLI・TUI統合・MCP接続）に関する手動検証手順を定義する。

---

## テストケース一覧

### TC-10-01: Windows インストーラーと Checksum 検証
- **目的**: 利用者が Git clone なしで PowerShell インストーラーから安全に `agent-eval` を導入できることを確認する。
- **手順**:
  1. PowerShell を起動する。
  2. `scripts/install.ps1` を `-DryRun` またはローカル成果物指定で実行する。
  3. checksum 不一致の破損ファイルを指定して実行する。
  4. 正常な ZIP アーカイブを指定して実行する。
- **期待結果**:
  - 不正な checksum の場合はインストールが拒否され、エラー案内が表示される。
  - 正常な場合は `%LOCALAPPDATA%\Programs\AgentEval\bin\agent-eval.exe` に配置される。
  - PATH への追加案内が表示される。

### TC-10-02: CLI 基本コマンドと `--json` 出力の純度
- **目的**: コマンドライン引数が正しく解析され、機械可読出力と人間向け出力が分離されていることを確認する。
- **手順**:
  1. `agent-eval version` を実行する。
  2. `agent-eval version --json` を実行する。
  3. `agent-eval doctor` を実行する。
  4. `agent-eval doctor --json` を実行する。
  5. `agent-eval run GEN-TOOL-001 --json` を実行する。
  6. 存在しないサブコマンド `agent-eval unknown` を実行する。
- **期待結果**:
  - `agent-eval version` でバージョン、コミット、アーキテクチャが表示される。
  - `--json` 指定時、標準出力は有効な JSON 1件のみが出力され、進捗やログは標準エラーに出力される。
  - 未知のサブコマンドに対しては、使用可能なサブコマンド一覧とヘルプ案内が表示される。

### TC-10-03: `agent-eval doctor` の診断と日本語エラー案内
- **目的**: 環境不備（Docker 未起動、DB 未接続、migration 未適用等）が発生した際に、非エンジニア向けに【原因】【次の操作】【ログ場所】が分かりやすく表示されることを確認する。
- **手順**:
  1. Docker が起動している状態で `agent-eval doctor` を実行する。
  2. （シミュレーション環境）Docker 未起動状態で `agent-eval doctor` を実行する。
- **期待結果**:
  - Docker、DB、マイグレーション、データ保存先、MCP 環境の各ステータス（OK / WARN / FAIL）が日本語で明確に表示される。
  - 失敗項目に対して、具体的な解決コマンドや操作手順が表示される。

### TC-10-04: TUI の一般利用者画面とレスポンシブ確認
- **目的**: 80x24 および狭小ターミナルで画面が崩れず、ウィザード・取込・MCP 設定画面が操作できることを確認する。
- **手順**:
  1. ターミナルサイズを 80x24 に設定し、`agent-eval`（引数なし）を実行する。
  2. ホーム画面から「初回設定ウィザード」を選択し、ステップを進める。
  3. 「Real Agent 記録取込」画面を選択し、JSONL パスを入力・検証する。
  4. 「MCP 接続設定」画面を選択し、Codex / OpenCode / Antigravity の案内を確認する。
  5. 各画面で `b` または `Esc` を押して前画面に戻る。
  6. `q` を押して安全に終了する。
- **期待結果**:
  - 画面の重なりや崩れが発生せず、操作キーガイドが常時表示される。
  - 画面遷移が正常に動作し、前画面へ正しく復帰できる。
  - API キーやパスワード等の秘密情報が画面上に一切露出しない。

### TC-10-05: Codex 向け MCP Server (`agent-eval mcp serve --stdio`) と登録
- **目的**: Codex からプロジェクトの絶対パスや Docker コマンドを意識せずに MCP Server を呼び出せることを確認する。
- **手順**:
  1. `agent-eval mcp install codex` を実行する。
  2. `agent-eval mcp status` を実行する。
  3. `agent-eval mcp serve --stdio` を起動し、標準入力から MCP の `initialize` リクエストを送信する。
- **期待結果**:
  - `agent-eval mcp install codex` で、Codex の有無確認と `codex mcp add agent-eval -- agent-eval mcp serve --stdio` の登録案内が行われる。
  - `agent-eval mcp serve --stdio` の標準出力には純粋な JSON-RPC レスポンスのみが出力され、コンテナ起動ログ等は標準エラーに分離される。

### TC-10-06: Real Agent 記録の形式検証と秘密情報拒否
- **目的**: 外部 Agent の JSONL トレースを安全に検証・取り込めることを確認する。
- **手順**:
  1. 正常なトレース `agent-eval validate-trace fixtures/agent-traces/codex-success.jsonl` を実行する。
  2. 秘密情報（API キー等）を含む不正な JSONL を作成し、`validate-trace` を実行する。
  3. 行番号が不正またはイベント sequence が不連続な JSONL を検証する。
  4. 正常なトレースを `agent-eval import-trace fixtures/agent-traces/codex-success.jsonl` で取り込む。
  5. `agent-eval trace <run-id>` で取り込んだイベント履歴を確認する。
- **期待結果**:
  - 正常な形式では adapter 種別、イベント数、タスク成否が表示される。
  - 秘密情報を含む場合は即座に拒否され、警告が表示される。
  - フォーマット異常時は該当行番号と修正方針が表示される。
  - 取込後に run ID が発行され、時系列 Trace を閲覧できる。

### TC-10-07: 利用者データ永続化と更新耐性
- **目的**: アプリケーションの更新やコンテナ再作成を行っても、利用者の作成データ（datasets, agent-traces, exports）が削除されないことを確認する。
- **手順**:
  1. Windows 環境で `%LOCALAPPDATA%\AgentEvalEngine` 内のディレクトリ構造を確認する。
  2. カスタム benchmark を作成・保存する。
  3. コンテナを停止・削除し、再度 `agent-eval run` を実行する。
- **期待結果**:
  - 利用者データはリポジトリ外の OS 標準パスに保存され、コンテナやバイナリの更新によって消去されない。
