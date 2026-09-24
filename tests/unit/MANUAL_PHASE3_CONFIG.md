# Phase 3設定とデータ検証の手動単体テスト

## UT-CONFIG-001 設定YAMLを読み込みOpenRouter設定を取得できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_config.py -k load_phase3_settings
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。`設定読込: dry_run=True, provider=openrouter, api_key_env=OPENROUTER_API_KEY, max_retries=1` と表示される。設定YAMLから dry-run、有効なプロバイダー、APIキーの環境変数名、最大再試行回数を取得できる。

## UT-CONFIG-002 プレースホルダーのAPIキーを拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_config.py -k placeholder_api_key
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 異常系。`APIキー検証: プレースホルダーを拒否し、外部通信を開始しない` と表示される。APIキーの値そのものは表示されず、仮のキーでクライアントを作成しない。

## UT-CONFIG-003 Phase 1 benchmarkを検証して読み込める（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_config.py -k load_phase1_benchmark
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 正常系。`benchmark検証: id=GEN-TOOL-001, required_metric=task_success` と表示される。JSON SchemaとPydantic検証を通過し、対象benchmarkと必須指標を取得できる。

## UT-CONFIG-004 不正なschema versionを拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_config.py -k invalid_benchmark
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: 異常系。`benchmark検証: schema_version=invalidを実行前に拒否` と表示される。不正なschema versionのbenchmarkは評価処理を開始しない。

## UT-CONFIG-005 OpenRouterモデルの構造化応答を取得できる（正常系）

実行コマンド:

```powershell
$env:RUN_LIVE_OPENROUTER_UNIT = "1"
docker compose --profile engine run --rm -e RUN_LIVE_OPENROUTER_UNIT engine pytest -v -s -m live tests/unit/test_phase3_openrouter_live.py
```

1. `.env` に有効な `OPENROUTER_API_KEY` を設定する。
2. 実行コマンドを順に実行する。
3. `OpenRouter Unit:` から始まる結果を確認する。

期待結果: 正常系。`model`、`success`、モデルの`answer`、`input_tokens`、`output_tokens`、`duration_ms`が表示される。応答は`success`と`final_answer`を持つJSONとして解析できる。APIキーは表示しない。

備考: OpenRouterへの外部通信とモデル利用料金が発生する可能性がある。`RUN_LIVE_OPENROUTER_UNIT=1`を指定しない限り、このテストはskipされる。

## UT-CONFIG-006 OpenRouterのタイムアウトを専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k timeout_is_converted
```

1. 実行コマンドを実行する。
2. `OpenRouter接続:` から始まる結果を確認する。

期待結果: 異常系。`OpenRouter接続: タイムアウトを専用例外へ変換` と表示される。OpenRouter SDKのタイムアウトは、`timeout_seconds`と`max_retries`を示す専用例外として扱われる。外部APIへは通信しない。

## UT-CONFIG-007 OpenRouterのレート制限を専用例外へ変換できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v -s tests/unit/test_phase3_openrouter.py -k rate_limit_is_converted
```

1. 実行コマンドを実行する。
2. `OpenRouter接続:` から始まる結果を確認する。

期待結果: 異常系。`OpenRouter接続: レート制限を専用例外へ変換` と表示される。HTTP 429のレート制限は、対象モデルと再試行設定を示す専用例外として扱われる。外部APIへは通信しない。
