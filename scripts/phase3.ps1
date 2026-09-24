# Phase 3コマンドを実行する
[CmdletBinding()]
param(
    [ValidateSet("test", "dry-run")]
    [string]$Action = "dry-run"
)

# DBスキーマを最新版へ更新する
function Update-Phase3Database {
    Write-Host "Phase 3: checking and applying DB migrations."
    & docker compose run --rm db-tools alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Error "DB migration failed. Evaluation will not start."
        exit $LASTEXITCODE
    }
}

if ($Action -eq "test") {
    & docker compose --profile engine run --rm engine pytest -v -s -m "not live" tests/unit/test_phase3_config.py tests/unit/test_phase3_events.py tests/unit/test_phase3_metrics.py tests/unit/test_phase3_openrouter.py tests/integration/test_phase3_workflow.py
    exit $LASTEXITCODE
}

Update-Phase3Database
& docker compose --profile engine run --rm engine python scripts/run_evaluation.py --benchmark benchmarks/generic/GEN-TOOL-001.yaml
exit $LASTEXITCODE
