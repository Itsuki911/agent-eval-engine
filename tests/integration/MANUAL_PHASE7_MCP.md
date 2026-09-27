# Phase 7 MCP Server 手動テスト

MCP Server は標準入出力で動作するローカル専用の構成である。初回はdry-runのまま実施する。

## IT-MCP-001：MCP Inspectorでtool一覧を表示できる

- 種別: 正常系

```powershell
docker compose --profile engine run --rm engine mcp dev apps/mcp/server.py
```

手順:

1. コマンドを実行する。
2. 表示された Inspector URL をブラウザで開く。
3. `List Tools` を選択する。

期待結果:

- `run_benchmark`、`evaluate_agent`、`get_run`、`get_trace`、`get_errors`、`compare_runs`、`run_regression` の7件が表示される。
- 任意コマンドやURLを入力するツールは表示されない。

## IT-MCP-002：run_benchmarkでdry-run評価を保存できる

- 種別: 正常系

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/integration/test_phase7_mcp.py -k run_benchmark
```

手順:

1. コマンドを実行する。

期待結果:

- `status=simulated`、`event_count`、`run_id` が表示される。
- trace の総件数が評価結果の `event_count` と一致する。

## IT-MCP-003：live LLMを明示許可なしで拒否できる

- 種別: 異常系

```powershell
docker compose --profile engine run --rm -e AGENT_EVAL_MCP_ALLOW_LIVE=0 engine pytest -v -s tests/unit/test_phase7_mcp.py -k live_guard
```

手順:

1. コマンドを実行する。

期待結果:

- `AGENT_EVAL_MCP_ALLOW_LIVE=1` が必要であることを示す拒否結果が表示される。
- OpenRouter API は呼び出されず、料金は発生しない。

## IT-MCP-004：回帰評価の上限超過を拒否できる

- 種別: 境界値・異常系

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase7_mcp.py -k regression_limit
```

手順:

1. コマンドを実行する。

期待結果:

- 11件の benchmark 指定が拒否される。
- DBへ新しいrunは追加されない。
