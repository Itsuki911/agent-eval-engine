# Phase 6 REST API 手動テスト

APIサーバーを起動する。

```powershell
docker compose --profile api up --build api
```

別の PowerShell で以下のケースを実施する。終了時は API を起動した端末で `Ctrl+C` を押す。

## IT-API-001：評価APIでsample benchmarkを実行して実行IDを取得できる

- 種別: 正常系

```powershell
$result = Invoke-RestMethod -Method Post -Uri http://localhost:8000/evaluate -ContentType application/json -Body '{"benchmark_id":"GEN-TOOL-001","source":"sample"}'
$result | ConvertTo-Json -Depth 8
```

手順:

1. コマンドを実行する。
2. `run_id` を控える。

期待結果:

- HTTP 201 が返る。
- `status` は `simulated`、`benchmark_id` は `GEN-TOOL-001` である。
- `event_count` は 6 以上であり、`metrics` に `task_success` が含まれる。

## IT-API-002：trace APIで時系列イベントとOpenTelemetry識別子を確認できる

- 種別: 正常系

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/runs/$($result.run_id)/trace" | ConvertTo-Json -Depth 8
```

手順:

1. IT-API-001 の `$result` を保持する。
2. コマンドを実行する。

期待結果:

- `total` は IT-API-001 の `event_count` と一致する。
- `events` は `sequence` 昇順であり、`benchmark_loaded` を含む。
- 各イベントに `trace_id` と `span_id` の項目が存在する。値がないイベントは `null` と表示される。

## IT-API-003：存在しないbenchmarkの評価を拒否できる

- 種別: 異常系

```powershell
try { Invoke-WebRequest -Method Post -Uri http://localhost:8000/evaluate -ContentType application/json -Body '{"benchmark_id":"UNKNOWN-API-001"}' -ErrorAction Stop } catch { $_.Exception.Response.StatusCode.value__ }
```

手順:

1. コマンドを実行する。

期待結果:

- `404` が表示される。
- `runs` テーブルに `UNKNOWN-API-001` の実行記録は追加されない。

## IT-API-004：外部Agentのイベント重複連番を拒否できる

- 種別: 異常系・境界値

```powershell
$run = Invoke-RestMethod -Method Post -Uri http://localhost:8000/runs -ContentType application/json -Body '{"benchmark_id":"GEN-API-001","agent_name":"manual-agent"}'
$event = '{"sequence":0,"event_type":"tool_call","payload":{"tool":"read"}}'
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/runs/$($run.run_id)/events" -ContentType application/json -Body $event
try { Invoke-WebRequest -Method Post -Uri "http://localhost:8000/runs/$($run.run_id)/events" -ContentType application/json -Body $event -ErrorAction Stop } catch { $_.Exception.Response.StatusCode.value__ }
```

手順:

1. コマンドを上から順に実行する。

期待結果:

- 最初のイベント登録は HTTP 201 で成功する。
- 同じ `sequence: 0` の2回目は `409` となる。
- `GET /runs/{run_id}/trace` の `total` は 1 である。

## IT-API-005：比較APIで2実行の指標差分を取得できる

- 種別: 正常系

```powershell
$left = Invoke-RestMethod -Method Post -Uri http://localhost:8000/evaluate -ContentType application/json -Body '{"benchmark_id":"GEN-TOOL-001"}'
$right = Invoke-RestMethod -Method Post -Uri http://localhost:8000/evaluate -ContentType application/json -Body '{"benchmark_id":"GEN-TOOL-001"}'
Invoke-RestMethod -Uri "http://localhost:8000/compare?left_run_id=$($left.run_id)&right_run_id=$($right.run_id)" | ConvertTo-Json -Depth 8
```

手順:

1. コマンドを実行する。

期待結果:

- `left_run_id` と `right_run_id` に別々の実行IDが表示される。
- `metrics` に `success.task_success`、`latency.end_to_end_latency_ms` が含まれる。
- 各指標に `left`、`right`、`difference` が表示される。
