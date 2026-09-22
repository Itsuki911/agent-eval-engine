# tests

このフォルダは評価フレームワーク自体のテストを置く場所です。

- `unit/`: loader、validator、metric計算などの単体テスト。
- `integration/`: benchmarkから実行、イベント、評価、永続化までの結合テスト。
- `e2e/`: CLI、API、MCPを含む利用者視点のテスト。
- `regression/`: baselineと比較する回帰テスト。

Phase 1では `scripts/validate_phase1.py` がデータ契約を検証します。フレームワークの
自動テストはPhase 3から追加します。
