# Phase 3 OpenRouter例外処理・障害耐性の手動単体テスト

README.md 80行目以降に記載されたLLM呼び出しにおける各種エラー分類、上限超過、再試行、スキーマ検証、冪等性制御の例外処理を手動確認する単体テストケースです。

---

## UT-RESIL-001 OpenRouter正常応答を検証して取得できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k normal_response_succeeds
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 正常系。`OpenRouter接続: 正常系チャット応答と冪等性キー送信を確認` と表示される。レスポンス本文、トークン数、コストが正しく解析され、リクエスト時に `X-Idempotency-Key` が送信される。

---

## UT-RESIL-002 OpenRouter認証エラー(401)を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k auth_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 401認証エラーを専用例外へ変換` と表示される。HTTP 401 AuthenticationError が `OpenRouterAuthenticationError` へ変換され、APIキーの再確認を促すメッセージが含まれる。

---

## UT-RESIL-003 OpenRouter認可エラー(403)を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k permission_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 403認可エラーを専用例外へ変換` と表示される。HTTP 403 PermissionDeniedError が `OpenRouterPermissionError` へ変換され、対象モデル利用権限不足が明示される。

---

## UT-RESIL-004 OpenRouterリクエスト形式エラー(400)を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k bad_request_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 400リクエスト形式エラーを専用例外へ変換` と表示される。HTTP 400 BadRequestError が `OpenRouterBadRequestError` へ変換され、不正なリクエスト形式が通知される。

---

## UT-RESIL-005 OpenRouter入力文字数上限超過を事前検出できる（境界値・異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k input_limit_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 境界値・異常系。`OpenRouter接続: 入力上限超過を事前検出` と表示される。設定された `max_prompt_chars` を超過するプロンプトが API 呼び出し前に `OpenRouterInputLimitError` として拒否され、外部APIとの不要な通信および課金を抑止する。

---

## UT-RESIL-006 OpenRouter出力上限到達(length)による打ち切りを検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k output_limit_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: finish_reason=length による出力上限超過を検出` と表示される。`finish_reason` が `length` の場合に `OpenRouterOutputLimitError` が送出され、生成が途中で打ち切られた不完全な応答の受容を防止する。

---

## UT-RESIL-007 OpenRouterモデル未発見(404)を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k not_found_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 404モデル未発見を専用例外へ変換` と表示される。HTTP 404 NotFoundError が `OpenRouterNotFoundError` へ変換され、モデル名の誤りや提供終了を通知する。

---

## UT-RESIL-008 OpenRouterプロバイダー障害(500)を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k server_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 500プロバイダー障害を専用例外へ変換` と表示される。HTTP 500 InternalServerError が `OpenRouterServerError` へ変換され、LLM提供元内部エラーとして識別される。

---

## UT-RESIL-009 OpenRouter一時的サービス停止(503)を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k service_unavailable_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 503サービス停止を専用例外へ変換` と表示される。HTTP 503 APIStatusError が `OpenRouterServiceUnavailableError` へ変換され、ゲートウェイやメンテナンスによる一時停止を識別する。

---

## UT-RESIL-010 OpenRouter接続障害を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k connection_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: ネットワーク接続障害を専用例外へ変換` と表示される。DNS解決失敗やTLSエラー等の APIConnectionError が `OpenRouterConnectionError` へ変換される。

---

## UT-RESIL-011 OpenRouterストリーミング切断を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k stream_disconnected_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: ストリーミング切断を専用例外へ変換` と表示される。チャンク受信途絶等のストリーム障害が `OpenRouterStreamDisconnectedError` へ変換される。

---

## UT-RESIL-012 OpenRouter不正JSON応答を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k invalid_format_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 不正JSON文字列の解析失敗を専用例外へ変換` と表示される。JSON形式でないテキスト応答が `OpenRouterInvalidFormatError` として拒否される。

---

## UT-RESIL-013 OpenRouter空応答を検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k empty_response_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 空のレスポンス受信を検出` と表示される。choicesが空、または本文が空の応答が `OpenRouterEmptyResponseError` として検出される。

---

## UT-RESIL-014 OpenRouter安全フィルタによる拒否を検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k safety_filter_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 安全フィルタによる拒否を検出` と表示される。`refusal` や `finish_reason=safety` が返された場合に `OpenRouterSafetyFilterError` として処理される。

---

## UT-RESIL-015 OpenRouterコンテンツフィルタによる途中停止を検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k content_filter_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: コンテンツフィルタによる中断を検出` と表示される。`finish_reason=content_filter` が返された場合に `OpenRouterContentFilterError` として処理される。

---

## UT-RESIL-016 OpenRouterツール呼出引数JSON破損を検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k tool_call_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: ツール呼出引数のJSON破損を検出` と表示される。破損した引数JSONを持つ `tool_calls` が `OpenRouterToolCallError` として検出される。

---

## UT-RESIL-017 OpenRouter構造化出力スキーマ検証失敗を検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k structured_output_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: スキーマ必須フィールド欠落を専用例外へ変換` と表示される。スキーマで要求された必須キーが存在しない場合、`OpenRouterStructuredOutputError` として拒否される。

---

## UT-RESIL-018 OpenRouter設定コスト上限超過を検出できる（境界値・異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k cost_limit_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 境界値・異常系。`OpenRouter接続: 設定コスト上限超過を検出` と表示される。実績コスト（`cost`）が設定値（`max_estimated_cost_usd`）を超過した場合、`OpenRouterCostLimitError` として遮断される。

---

## UT-RESIL-019 OpenRouterリトライ上限到達を検出できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k retry_limit_error_is_converted
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 異常系。`OpenRouter接続: 再試行可能ステータスでのリトライ上限到達を検出` と表示される。`retryable_status_codes` に該当する障害が指定回数（`max_retries`）連続した場合に `OpenRouterRetryLimitError` が送出される。

---

## UT-RESIL-020 OpenRouter冪等性キーヘッダーを正しく生成できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k idempotency_key_is_resolved
```

1. 実行コマンドを実行する。
2. 標準出力の表示を確認する。

期待結果: 正常系。`OpenRouter接続: idempotency_key_modeに応じたヘッダー生成を確認` と表示される。`per_request` モードで `X-Idempotency-Key` が適切に割り当てられ、`none` モードではヘッダーが付与されない。

