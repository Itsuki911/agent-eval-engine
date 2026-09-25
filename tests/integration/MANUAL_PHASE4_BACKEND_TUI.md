# Phase 4 バックエンド統合TUIの手動統合テスト

このテストは Go TUI、Python subprocess、PostgreSQL を接続する。OpenRouter APIは使用せず、`configs/phase3-local.yaml`のdry-runで実行する。

## IT-TUI-001 統合TUIからdry-runを開始して保存結果を表示できる（正常系）

実行コマンド:

```powershell
docker compose --profile tui run --rm --build tui
```

1. 実行コマンドを実行する。
2. ホーム画面で下矢印キーを2回押す。
3. Enterキーを押して`NEW EVALUATION`を開く。
4. Enterキーを押して確認画面を開く。
5. 下矢印キーを押して`Run evaluation`を選択する。
6. Enterキーを押して評価を開始する。
7. Timelineに`benchmark_loaded`、`environment_ready`、`evaluation_completed`、`persistence_requested`が順に表示されることを確認する。
8. 完了後に詳細画面のrun ID、status、metrics、eventsを確認する。
9. `q`キーを押して終了する。

期待結果: 正常系。実行前にDB migrationが確認・適用される。dry-runの進捗イベントがTUIのTimelineへ時系列で表示され、PostgreSQLへrun、events、metrics、evaluationが保存される。最終詳細に`status: simulated`、`BENCHMARK`、`EVENTS`、評価指標が表示される。OpenRouter APIへの通信と料金は発生しない。

## IT-TUI-002 統合TUIでDB接続に失敗した場合に安全なエラーを表示できる（異常系）

実行コマンド:

```powershell
docker compose --profile tui run --rm --build -e DATABASE_URL=postgresql+psycopg://invalid:invalid@db:5432/missing tui
```

1. 実行コマンドを実行する。
2. `BACKEND ERROR`と`migration`が表示されることを確認する。
3. 接続文字列のパスワードが表示されないことを確認する。
4. `q`キーを押して終了する。

期待結果: 異常系。TUIは評価を開始せず、DB migration段階の失敗を表示する。エラー画面には原因の要約と`r 再試行`、`b 一覧へ戻る`、`q 終了`が表示される。無効な接続情報やパスワード値は画面に表示されない。
