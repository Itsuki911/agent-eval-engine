# Phase 4 TUIモックの手動回帰テスト

## RT-TUI-001 Trace画面で全カラーパレットが正しく出力されスタイル欠落が再発しない（回帰）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestRenderTraceAmberPaletteRegression ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系（回帰検証）。`TestRenderTraceAmberPaletteRegression`が`PASS`し、アンバーオレンジ（`#e0af68`）を含む全てのカラーパレットがTrace画面の描画に含まれること。

## RT-TUI-002 実行一覧画面でEnterキーを押して詳細画面へ遷移できる（回帰）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestRunsEnterOpensDetailScreen ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系（回帰検証）。`TestRunsEnterOpensDetailScreen`が`PASS`し、実行一覧画面（`runsScreen`）でEnterキーを押した際に詳細画面（`detailScreen`）へ確実に遷移できること。

## RT-TUI-003 ホーム画面で数字キーを押して直接目的の画面を開ける（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestHomeNumberKeysNavigateDirectly ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系。`TestHomeNumberKeysNavigateDirectly`が`PASS`し、数字キー1〜5を押すことで新人エンジニアや非エンジニアでも迷わず目的の画面へ遷移できること。

## RT-TUI-004 プロンプト入力欄でEscキーを押してフォーカスを解除しqで終了できる（回帰）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestCreateBenchmarkEscapeExitsInputMode ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系（回帰検証）。`TestCreateBenchmarkEscapeExitsInputMode`が`PASS`し、プロンプト入力欄にフォーカスが当たった状態からEscキーで確実に通常モードへ戻り、その後の`q`キーで正常終了できること。

## RT-TUI-005 プロンプト入力欄でTabキーおよびShift+Tabキーを押して他項目へ移動できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestCreateBenchmarkTabAndBacktabNavigate ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系。`TestCreateBenchmarkTabAndBacktabNavigate`が`PASS`し、プロンプト入力中であってもTabキーで次フィールド（成功条件）へ移動でき、Shift+Tabキー（backtab）で前フィールドへ確実に移動できること。

## RT-TUI-006 プロンプト入力欄をマウスでクリックしてフォーカスし外側クリックで解除できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestCreateBenchmarkMouseClickFocusAndBlur ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系。`TestCreateBenchmarkMouseClickFocusAndBlur`が`PASS`し、マウスクリックによって指示プロンプト入力欄が即座にアクティブ化（Focus）され、余白や他フィールドのクリックで編集モードが解除（Blur）されること。

## RT-TUI-007 入力モード中にCtrl+Cを押して即時強制終了できる（異常系・境界値）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestCreateBenchmarkCtrlCTerminates ./...'
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 異常系・境界値。`TestCreateBenchmarkCtrlCTerminates`が`PASS`し、複数行テキスト入力モードで文字入力中などの緊急時であっても、Ctrl+Cキーを受信してプロセスが確実に即時終了できること。
