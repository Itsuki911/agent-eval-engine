# Phase 4 TUIモックの手動単体テスト

対象は静的な画面描画・キー操作・画面遷移だけです。PostgreSQL、Python評価エンジン、OpenRouter APIは使用しません。

## UT-TUI-001 モック画面を描画して固定の案内情報を確認できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestMockupRendersAllScreens ./...'
```

1. 実行コマンドを実行する。
2. 各サブテスト名と結果を確認する。

期待結果: 正常系。`home`、`runs`、`detail`、`trace`、`compare`、`confirm`、`error`、`new evaluation`、`search`、`help`の10サブテストが表示される。各画面で案内用の固定文字列が描画され、DB接続・Python・LLM API通信は行われない。

## UT-TUI-002 モック選択を先頭・末尾から範囲外へ移動しない（境界値）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestMockupSelectionStaysWithinBounds ./...'
```

1. 実行コマンドを実行する。
2. `home`、`runs`、`trace`、`new evaluation`、`search`の結果を確認する。

期待結果: 境界値。先頭の選択状態で上矢印を入力しても選択番号は`0`未満にならない。末尾の選択状態で下矢印を入力しても選択番号は増加しない。5サブテストが成功する。

## UT-TUI-003 モックのlive選択が実エンジンを起動せず詳細画面へ遷移する（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestMockupLiveSelectionOnlyChangesScreen ./...'
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。`Run live`の選択はモック詳細画面への遷移だけを行う。描画内容に`OPENROUTER_API_KEY`、`DATABASE_URL`、`python`が含まれず、外部API・DB・Python評価エンジンを呼び出さない。

## UT-TUI-004 モック対話をqキーで終了できる（正常系）

実行コマンド:

```powershell
docker compose --profile cli run --rm --build --entrypoint sh cli -c 'go test -v -run TestMockupQuitEndsInteraction ./...'
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。下矢印とEnterで`NEW EVALUATION`画面へ遷移した後、`q`によりエラーなく対話処理が終了する。外部サービスへの通信は行われない。
