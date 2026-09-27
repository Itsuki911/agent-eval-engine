# Real Coding Agent トレース取込ガイド (Real Agent Trace Guide)

Agent Eval Engine は、Codex, OpenCode, Antigravity などの外部コーディングエージェントが記録した実行トランスクリプトを取り込み、共通スキーマで時系列分析・スコアリングを行うことができます。

---

## 1. トレース形式の仕様 (`agent-eval.trace.v1`)

トランスクリプトは **JSON Lines (`.jsonl`)** 形式で構成され、以下の 3 種類のレコード行を順序正しく含んでいる必要があります。

### レコード構成
1. **`run` レコード (先頭 1 行)**: エージェント名、アダプター種別、ベンチマークID、モデル名
2. **`event` レコード (複数行)**: `sequence: 0` から連続する整数でインクリメントされる時系列イベント
3. **`result` レコード (末尾 1 行)**: 最終ステータス、成功フラグ、終了コード、変更ファイル一覧

### 具体例 (`trace-sample.jsonl`)
```jsonl
{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-PY-001","agent_name":"codex-cli","model":"gpt-4o"}
{"record_type":"event","sequence":0,"event_type":"user_prompt","actor":"user","payload":{"content":"Fix the off-by-one error in search algorithm."}}
{"record_type":"event","sequence":1,"event_type":"tool_call","payload":{"tool":"read_file","path":"src/search.py"}}
{"record_type":"event","sequence":2,"event_type":"tool_result","payload":{"tool":"read_file","content":"def search(arr, target): ..."}}
{"record_type":"result","status":"completed","task_success":true,"exit_code":0,"final_state":{"changed_files":["src/search.py"]}}
```

### 対応アダプター種別 (`adapter_type`)
- `codex`: OpenAI Codex CLI
- `opencode`: OpenCode エージェント
- `antigravity`: Google Antigravity / Gemini CLI
- `generic`: 汎用 Coding Agent トランスクリプト

---

## 2. CLI による検証と取込

### 事前検証 (`validate-trace`)
取り込み前にファイル形式と機密情報の有無を検証できます。

```bash
agent-eval validate-trace path/to/trace.jsonl
```

### 取り込み実行 (`import-trace`)
```bash
agent-eval import-trace path/to/trace.jsonl
```

正常に取り込まれると、Run ID が発行され、DB にイベントが格納されます。

```text
[OK] トレースを取り込みました
  Run ID:       run_codex_20260927_123456
  エージェント: codex (codex-cli)
  イベント数:   3 件
  ステータス:   completed (成功: true)
```

---

## 3. 安全規則とバリデーション

Agent Eval Engine はプライバシーとセキュリティを最優先としており、以下の条件に違反するファイルは **即座に拒絶** されます。

1. **機密情報の混入禁止**:
   - レコード内のキーまたは文字列に `api_key`, `Authorization`, `token`, `password`, `secret`, `cookie` 等が含まれている場合は取り込みを拒否します。
2. **ファイルサイズとイベント数上限**:
   - 最大ファイルサイズ: **5 MiB**
   - 最大イベント数: **10,000 件**
3. **パストラバーサルの禁止**:
   - `../` を含むパスや、安全でない外部絶対パスの直接参照を拒否します。
4. **イベント順序の整合性**:
   - `sequence` 番号が `0` から始まっていない、または連番が抜けている場合は拒否します。

---

## 4. TUI での確認

取り込んだトレースは、TUI の「Agent Trace を見る」メニューから、1 ステップずつプロンプトやツール呼出の履歴を詳細に再生・確認できます。
また `agent-eval trace <run-id>` でもターミナル上に直接タイムラインを出力可能です。
