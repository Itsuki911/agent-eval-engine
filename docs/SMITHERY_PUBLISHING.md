# Smithery 公開準備

## 配布方式

この MCP Server は、GitHub Releases を正規配布経路として使い、評価エンジン自体は利用者の PC 上の Docker で実行します。Smithery 上で評価データ、PostgreSQL、OpenRouter API キー、実行履歴を保持しません。

- MCP transport: `stdio`（ローカルプロセス）
- 配布物: GitHub Releases の `.mcpb` と SHA-256 checksum
- 実行データ: 利用者のローカル PostgreSQL volume と `local-data/`
- 公開対象: `apps/mcp/server.py` が公開する 8 ツール

Smithery の deployment API では `stdio` がローカル実行形式として定義されています。本プロジェクトは HTTP 公開（`hosted_shttp`、`external_shttp` など）を前提にしません。

## Smithery 登録用の説明文

### 表示名

`Agent Eval Engine (Local)`

### 短い説明

ローカル Docker 上の AI Agent 評価を、MCP から実行・追跡・比較するツールです。

### 詳細説明

Agent Eval Engine は、generic と coding の benchmark を評価し、run、metrics、時系列 trace をローカル PostgreSQL に保存します。MCP Host は `run_benchmark`、`get_trace`、`compare_runs` などを通じて、保存済み結果を確認できます。初期設定は dry-run です。live LLM 実行には `engine.dry_run: false` と `AGENT_EVAL_MCP_ALLOW_LIVE=1` の両方が必要です。

### 公開ツール

| ツール | 用途 | 書き込み |
|---|---|---|
| `run_benchmark` | benchmark を評価して保存 | あり |
| `evaluate_agent` | `run_benchmark` の互換入口 | あり |
| `get_run` | 保存済み run の詳細を取得 | なし |
| `get_trace` | 時系列イベントを取得 | なし |
| `get_errors` | エラーイベントを抽出 | なし |
| `compare_runs` | 2 run の metrics を比較 | なし |
| `run_regression` | 最大10件を連続評価 | あり |
| `import_agent_trace` | 外部Agentの標準記録を取込 | あり |

## 公開前に利用者が行う作業

1. GitHub Releases に動作確認済みの tag とリリースノートを公開する。
2. `docs/GITHUB_RELEASE_DISTRIBUTION.md` の手順で MCPB と checksum が添付されたことを確認する。
3. `docs/MCP_CLIENT_SETUP.md` の Windows 用起動コマンドを接続手順として掲載する。
4. 公開ページで API キー、`.env`、ローカル絶対パス、PostgreSQL の接続文字列を入力・掲載していないことを確認する。
5. 新規 Windows 利用者アカウントまたは別 PC で、E2E-MCP-003 を実施する。

Smithery の Free plan の条件は変更され得るため、公開直前に Smithery の料金ページとダッシュボードを正とします。このリポジトリは特定の無料枠や上限を前提にしていません。

## 公開後の運用

- リリースごとに `docker compose --profile mcp build mcp` と自動テストを実行する。
- Smithery の公開情報は、GitHub Release の固定 tag を参照させる。`main` の未検証状態を配布対象にしない。
- 脆弱性・破壊的変更は GitHub Release の release note と Smithery の説明欄に記載する。
- 問い合わせに run ID や trace を含める場合でも、API キー、token、password を送信しない。
- live LLM を利用する人には、利用者自身の API キーと費用負担であることを明示する。

## 現在のSmithery公開状況

2026-09-27 時点で Smithery CLI の MCPB publish は Registry 側の `400 No values to set` により保留する。このため `smithery mcp publish` を公開手順に含めない。GitHub Releases の MCPB 配布とローカル stdio 実行は利用できる。Smithery 側の不具合が解消された後、MCPB publish を別途検証する。

## 公式情報

- [Smithery deployment type API](https://smithery.ai/docs/api-reference/servers/list-deployments-1)
- [Smithery GitHub repository connection API](https://smithery.ai/docs/api-reference/servers/get-server-repository-connection)
- [Smithery Pricing](https://smithery.ai/pricing)
