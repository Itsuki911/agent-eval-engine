# Real Coding Agent Adapter

## 目的

Codex、OpenCode、Antigravity などが出力した実行記録を、製品固有 API に依存せず評価 DB へ保存する。Adapter 自体は Agent を起動しない。各 Agent が出力した JSONL を受け取り、run、events、metrics、agent execution、artifact を1回の transaction で保存する。

## 保存場所と安全境界

MCP と REST API は `local-data/agent-traces/` 配下の相対パスだけを読み込む。`AGENT_EVAL_AGENT_TRACE_DIR` を設定すると保存場所を変更できる。絶対パス、`..` を含む許可外パス、5 MiB 超、10,000 event 超、秘密情報キーを含む JSONL は拒否する。

CLI は利用者が明示指定したファイルを取り込める。CLI はローカルでのみ実行する。

## agent-eval.trace.v1 JSONL

先頭は `run`、途中は連番の `event`、末尾は `result` にする。`adapter_type` は `codex`、`opencode`、`antigravity`、`generic` のいずれかを指定する。

```jsonl
{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-PY-001","agent_name":"codex-cli","model":"example-model"}
{"record_type":"event","sequence":0,"event_type":"user_prompt","actor":"user","payload":{"content":"Fix the condition."}}
{"record_type":"event","sequence":1,"event_type":"tool_call","payload":{"tool":"read","path":"src/app.py"}}
{"record_type":"result","status":"completed","task_success":true,"exit_code":0,"final_state":{"changed_files":["src/app.py"]}}
```

`event.sequence` は必ず 0 から連続させる。`status` は `completed`、`failed`、`cancelled` のいずれか、`task_success` は boolean にする。

## 取込方法

CLI は任意の明示ファイルを取込できる。

```powershell
docker compose --profile engine run --rm engine python scripts/import_agent_transcript.py --file fixtures/agent-traces/codex-success.jsonl
```

期待結果は、標準出力へ run ID、execution ID、adapter type、status、task success、event count を持つ JSON 1件が表示されることである。

MCP または REST API では、先に JSONL を `local-data/agent-traces/` に保存し、相対ファイル名 `codex-success.jsonl` を指定する。MCP tool 名は `import_agent_trace`、REST endpoint は `POST /agent-transcripts/import` である。

## 現在の範囲

この Adapter は共通ログ取込基盤であり、各 CLI の実行を自動操作する driver ではない。製品ごとの CLI 自動実行・hook・plugin は、各 Agent が安定したログ export interface を公開した段階で、この JSONL 形式へ変換する薄い driver として追加する。
