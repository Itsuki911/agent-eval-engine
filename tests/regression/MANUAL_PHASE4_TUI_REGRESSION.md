# Phase 4 TUIモックの手動回帰テスト

## RT-TUI-001 Trace画面で全カラーパレットが正しく出力されスタイル欠落が再発しない（回帰）

実行コマンド:

```powershell
docker compose --profile cli run --rm --entrypoint "go test -v -run TestRenderTraceAmberPaletteRegression ./..." cli
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系（回帰検証）。`TestRenderTraceAmberPaletteRegression`が`PASS`し、アンバーオレンジ（`#e0af68`）を含む全てのカラーパレットがTrace画面の描画に含まれること。

## RT-TUI-002 実行一覧画面でEnterキーを押して詳細画面へ遷移できる（回帰）

実行コマンド:

```powershell
docker compose --profile cli run --rm --entrypoint "go test -v -run TestRunsEnterOpensDetailScreen ./..." cli
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系（回帰検証）。`TestRunsEnterOpensDetailScreen`が`PASS`し、実行一覧画面（`runsScreen`）でEnterキーを押した際に詳細画面（`detailScreen`）へ確実に遷移できること。

## RT-TUI-003 ホーム画面で数字キーを押して直接目的の画面を開ける（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --entrypoint "go test -v -run TestHomeNumberKeysNavigateDirectly ./..." cli
```

1. 実行コマンドを実行する。
2. テスト結果がPASSすることを確認する。

期待結果: 正常系。`TestHomeNumberKeysNavigateDirectly`が`PASS`し、数字キー1〜5を押すことで新人エンジニアや非エンジニアでも迷わず目的の画面へ遷移できること。
