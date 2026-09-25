# Phase 4 Python backend境界の手動単体テスト

対象はGo TUIとPython評価エンジンの通信契約である。PostgreSQLへ接続する統合確認は`tests/integration/MANUAL_PHASE4_BACKEND_TUI.md`で実施する。

## UT-BACKEND-001 Python backendが進捗JSONと最終結果を分離できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tui_backend.py -k 'print_progress or result_output'
```

1. 実行コマンドを実行する。
2. `test_print_progress_outputs_safe_json`の結果を確認する。
3. `test_result_output_contains_run_summary`の結果を確認する。

期待結果: 正常系。進捗イベントには`type=progress`、`sequence=3`、`event_type=llm_call`、`status=recorded`が含まれる。payloadの`secret`は進捗JSONに含まれない。最終結果には`status=simulated`、`benchmark_id=GEN-TOOL-001`、`event_count=6`、`llm_cost_usd=null`が含まれる。

## UT-BACKEND-002 Python backendがgenericとcodingだけを候補として返せる（境界値）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tui_backend.py -k list_benchmarks_returns_supported_families
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 境界値。返される候補の`family`は`generic`または`coding`だけである。各候補の`path`は`benchmarks/`から始まり、`index.yaml`、terminal、web、guiのbenchmarkは候補へ含まれない。`index.yaml`は件数を持つ一覧メタデータであり、評価対象として読み込まれない。

## UT-BACKEND-003 Go bridgeが非構造化標準エラーを進捗として扱わない（異常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestBackendScanProgressReadsStructuredEvents ./...'
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 異常系。JSON Lines形式の`progress`イベントだけがGoの進捗イベントとして扱われる。構造化されていない標準エラーは画面へそのまま出力せず、診断情報として分離される。

## UT-BACKEND-004 Python backendが候補をページ単位で返せる（境界値）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_tui_backend.py -k 'requested_page or filters_by_id'
```

1. 実行コマンドを実行する。
2. `benchmark_page` の出力を確認する。
3. `benchmark_filter` の出力を確認する。

期待結果: 境界値。先頭ページとoffset=3のページにはそれぞれ3件だけが返り、同じIDを重複して含まない。`GEN-TOOL`検索では、返却される候補IDがすべて`GEN-TOOL`で始まる。Python backendは候補全件をGoへ返さない。

## UT-BACKEND-005 Go TUIがページングと実行中の中止案内を表示できる（正常系・異常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run "TestBackend(NewEvaluationShowsSinglePage|BenchmarkSelectionMovesToNextPage|TraceShowsCancelGuideWhileRunning|TraceShowsCancellationState)|TestReadKeysReceivesInputAsynchronously|TestNeedsBackendRefreshForPageChange" ./...'
```

1. 実行コマンドを実行する。
2. ページング関連のテスト名と結果を確認する。
3. 非同期キー入力と中止案内のテスト名と結果を確認する。

期待結果: 正常系・異常系。候補一覧は`候補 1-5 / 281`のように範囲を表示し、末尾の下矢印キーで次ページへ移動する。実行中のTraceには`q で中止できます`、中止要求後には`評価を中止しています`が表示される。ページ内の選択操作だけではPython backendを再取得せず、ページ変更時だけ再取得する。
