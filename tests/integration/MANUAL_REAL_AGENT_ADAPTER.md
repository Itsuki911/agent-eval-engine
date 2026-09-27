# Real Coding Agent Adapter 手動テスト

## IT-AGENT-001：Codex記録を取り込んで完全な履歴を保存できる

- 種別: 正常系

```powershell
docker compose --profile engine run --rm engine python scripts/import_agent_transcript.py --file fixtures/agent-traces/codex-success.jsonl
```

手順:

1. コマンドを実行する。
2. 標準出力の JSON を確認する。
3. `run_id` を控える。
4. TUI または `get_run` で run を開く。

期待結果:

- JSON は `adapter_type: "codex"`、`status: "completed"`、`task_success: true`、`event_count: 3` を持つ。
- run には `user_prompt`、`tool_call`、`tool_result` の順で3 event が保存される。
- agent execution の adapter type は `codex`、artifact URI は `local://agent-traces/codex-success.jsonl` である。

## IT-AGENT-002：秘密情報を含む記録を拒否しDBへ保存しない

- 種別: 異常系

```powershell
docker compose --profile engine run --rm engine python scripts/import_agent_transcript.py --file fixtures/agent-traces/invalid-secret.jsonl
```

手順:

1. コマンドを実行する。
2. 終了コードと標準出力の JSON を確認する。

期待結果:

- 終了コードは `2` である。
- JSON は `status: "rejected"` を持ち、理由に秘密情報の拒否が含まれる。
- run、event、artifact は追加されない。

## IT-AGENT-003：MCP取込で許可外パスを拒否できる

- 種別: 異常系

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_real_agent_adapter.py -k path
```

手順:

1. コマンドを実行する。
2. JSON形式のテスト出力を確認する。

期待結果:

- `real_agent_trace_path` が `result: "passed"`、`rejected: "path_traversal"` を表示する。
- 許可フォルダ外のファイルは MCP と REST API から読めない。
