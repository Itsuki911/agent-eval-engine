# tests

このフォルダは評価フレームワーク自体のテストを置く場所です。

- `unit/`: loader、validator、metric計算、Phase 10 配布・CLI 関連などの単体テスト。
- `integration/`: benchmarkから実行、イベント、評価、永続化、CLI-バックエンド結合テスト。
- `e2e/`: CLI、API、MCP、インストーラーを含む利用者視点のテスト。
- `regression/`: baselineと比較する回帰テスト。
- `manual/`: Phase 10 手動検証仕様書 (`MANUAL_PHASE10_VERIFICATION.md`) などの手動検証手順書。

Phase 1では `scripts/validate_phase1.py` がデータ契約を検証します。フレームワークの
自動テストはPhase 3から追加します。
