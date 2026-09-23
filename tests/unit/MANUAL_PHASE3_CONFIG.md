# Phase 3設定とデータ検証の手動単体テスト

## UT-CONFIG-001 設定YAMLを読み込みOpenRouter設定を取得できる（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_config.py -k load_phase3_settings
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_load_phase3_settings PASSED`と表示され、`openrouter`と`OPENROUTER_API_KEY`を含む設定を読み込める。

## UT-CONFIG-002 プレースホルダーのAPIキーを拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_config.py -k placeholder_api_key
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_placeholder_api_key_is_rejected PASSED`と表示され、仮のキーでAPI通信を開始しない。

## UT-CONFIG-003 Phase 1 benchmarkを検証して読み込める（正常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_config.py -k load_phase1_benchmark
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_load_phase1_benchmark PASSED`と表示され、JSON SchemaとPydantic検証を通過する。

## UT-CONFIG-004 不正なschema versionを拒否できる（異常系）

実行コマンド:

```powershell
docker compose --profile engine run --rm engine pytest -v tests/unit/test_phase3_config.py -k invalid_benchmark
```

1. 実行コマンドを実行する。
2. テスト名と結果を確認する。

期待結果: `test_invalid_benchmark_is_rejected PASSED`と表示され、不正なbenchmarkを実行前に拒否できる。
