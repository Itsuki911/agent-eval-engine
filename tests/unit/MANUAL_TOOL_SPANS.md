# 個別ツールスパン機能の手動単体テスト

## 共通出力形式

`pytest -s` で表示される確認結果は1行JSONである。`test` はテスト名、`result` は `passed`。`span_count`、`status_code`、`parent_span` でスパン階層と属性を確認する。

---

## UT-TOOL-SPAN-001 個別ツールの独立スパン階層を正しく生成できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tool_spans.py -k test_individual_tool_spans_hierarchy
```

1. 上記の実行コマンドを実行する。
2. 出力されるJSON結果とテストステータスを確認する。

期待結果: 正常系。`result="passed"`, `span_count=6` が表示され、`tool.read`, `tool.search`, `tool.bash` が親ステップ（`inspect`, `test`）の子スパンとして生成される。

---

## UT-TOOL-SPAN-002 ツール実行エラー時にスパンへ異常が記録される（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tool_spans.py -k test_tool_span_records_error
```

1. 上記の実行コマンドを実行する。
2. 出力されるJSON結果とテストステータスを確認する。

期待結果: 異常系。`result="passed"`, `status_code="ERROR"`, `error_recorded=true` が表示され、スパン内に例外イベント（`FileNotFoundError`）が記録される。

---

## UT-TOOL-SPAN-003 ツール実行中のイベント収集とスパンが連動する（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tool_spans.py -k test_tool_span_with_event_collector
```

1. 上記の実行コマンドを実行する。
2. 出力されるJSON結果とテストステータスを確認する。

期待結果: 正常系。`result="passed"`, `parent_span="tool.write"` が表示され、ツール実行中に記録されたイベントの親スパンが `tool.write` になる。

---

## UT-TOOL-SPAN-004 設計書の全ツリー階層構造を再現・検証できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tool_spans.py -k test_agent_architecture_tree_hierarchy
```

1. 上記の実行コマンドを実行する。
2. 出力されるJSON結果とテストステータスを確認する。

期待結果: 正常系。`result="passed"`, `total_spans=12`, `architecture_verified=true` が表示され、`planner`, `inspect`, `edit`, `test`, `reflection` 配下の全スパン階層が整合する。

---

## UT-TOOL-SPAN-005 ツール引数の秘密情報をSpan属性から除外できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tool_spans.py -k test_tool_span_masks_secret_arguments
```

1. 上記の実行コマンドを実行する。
2. 出力されるJSON結果とテストステータスを確認する。

期待結果: 異常系。`result="passed"`, `secret_redacted=true` が表示される。`api_key`など秘密情報を示す引数はSpan属性に`[REDACTED]`として記録され、元の値は出力されない。
