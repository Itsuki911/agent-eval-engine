# 設定

`phase1-local.yaml` は、Phase 1のデータ検証・ローカル実行に使う共通設定です。

- benchmarkとfixtureのルートディレクトリ
- 外部ネットワークの既定値
- 並列数
- 軌跡の保存方針
- 選択するbenchmarkの状態

Phase 1では `draft` の定義を検証対象にしています。実エージェントの実行を導入するPhase 3で、`active` のみを通常実行対象に切り替えます。

---

`phase3-local.yaml` は、Phase 3の評価エンジン実行およびLLMモデル呼び出しに関する設定です。

### 主な設定項目 (`model`)
- **タイムアウト・接続制御**:
  - `timeout_seconds`: 全体タイムアウト（秒）
  - `connect_timeout_seconds` / `read_timeout_seconds`: 接続確立と応答待機のタイムアウト分離
- **リトライ制御**:
  - `max_retries`: 最大再試行回数
  - `retryable_status_codes`: 再試行対象のHTTPステータスコード（例: `[408, 429, 500, 502, 503, 504]`）
  - `retry_backoff_initial_seconds` / `retry_backoff_max_seconds` / `retry_jitter`: 再試行間隔および集中再試行の抑制
- **入力・出力上限チェック**:
  - `max_input_tokens` / `max_prompt_chars`: API呼び出し前の入力上限チェック
  - `max_output_tokens`: 出力トークン上限
- **コスト制御**:
  - `max_estimated_cost_usd` / `max_cost_per_run_usd`: 実行前・実行中のコスト停止基準（米ドル）
- **出力検証・スキーマ**:
  - `validate_structured_output`: 構造化出力（JSON等）の検証を有効化
  - `response_format` / `response_schema`: 期待する応答形式・JSONスキーマ
- **冪等性**:
  - `idempotency_key_mode`: 再試行時の同一キー使用方針（`none` / `per_run` / `per_request`）

