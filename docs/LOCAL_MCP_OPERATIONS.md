# ローカル MCP 運用手順

## 運用境界

Agent Eval Engine は利用者 PC 内で動作します。Smithery、MCP Host、GitHub Releases は配布・接続のための外部サービスであり、評価の DB や benchmark を外部に送信しません。ただし、live LLM 実行時は利用者が選んだ LLM API へ評価プロンプトを送信します。

## 日常運用

### 起動

```powershell
docker compose --profile mcp up -d mcp
docker compose --profile mcp ps
```

期待結果: `db` は `healthy`、`mcp` は `running` である。

### 接続状態の確認

MCP Host のツール一覧で、次の 7 件を確認します。

```text
run_benchmark, evaluate_agent, get_run, get_trace, get_errors, compare_runs, run_regression, import_agent_trace
```

Host が接続できない場合は、次を確認します。

```powershell
docker compose --profile mcp logs --tail 100 mcp
docker compose --profile mcp ps
```

期待結果: `mcp` の実行状態と `db` の health 状態を確認できる。ログや共有時には API キーを含めない。

### 更新

```powershell
git pull
docker compose --profile mcp build mcp
docker compose --profile mcp up -d --force-recreate mcp
```

期待結果: 新しいイメージで `mcp` が再作成され、既存 `postgres_data` volume は維持される。

## セキュリティ確認

- `.env`、OpenRouter API キー、PostgreSQL 接続文字列を GitHub Release、Smithery、Issue、trace に掲載しない。
- 初期値の dry-run を維持し、live 実行は利用者が料金と送信内容を理解した上で明示的に有効化する。
- `run_benchmark`、`run_regression`、`import_agent_trace` は DB に書き込む。利用者が意図した benchmark と記録だけ実行する。
- MCP Host の実行承認画面では、ツール名と引数を確認する。
- Docker Desktop と依存イメージを定期的に更新する。

## 障害時の切り分け

| 状況 | 最初の確認 | 期待する判断 |
|---|---|---|
| Host にツールが表示されない | `docker compose --profile mcp ps` | `mcp` と `db` を起動する |
| DB 接続に失敗する | `docker compose --profile mcp logs --tail 100 db` | `db` が healthy になるまで待つ |
| live が拒否される | `engine.dry_run` と `AGENT_EVAL_MCP_ALLOW_LIVE` | 両方を明示的に有効化する |
| 想定外の費用が心配 | dry-run へ戻す | `mcp` を再作成して live を停止する |
| Server を緊急停止する | `docker compose --profile mcp down` | MCP と DB を停止する |

## 監査とバックアップ

run、event、metrics はローカル PostgreSQL volume に保存されます。公開前・更新前に必要な run を CSV 出力または PostgreSQL dump として別媒体へ保管してください。削除操作や volume の削除は、必要な履歴を退避してから人が実行します。
