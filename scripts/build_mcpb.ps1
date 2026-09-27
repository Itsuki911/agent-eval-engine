param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BundleSource = Join-Path $ProjectRoot "distribution\mcpb"
$StagingRoot = Join-Path $ProjectRoot "build\mcpb"
$BundleOutput = Join-Path $ProjectRoot "dist\agent-eval-engine.mcpb"
$ProjectOutput = Join-Path $StagingRoot "project"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 20 or later is required"
}

if (Test-Path -LiteralPath $StagingRoot) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
}

if (Test-Path -LiteralPath $BundleOutput) {
    Remove-Item -LiteralPath $BundleOutput -Force
}

New-Item -ItemType Directory -Path $ProjectOutput -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $StagingRoot "server") -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $BundleOutput) -Force | Out-Null

$BundleItems = @(
    "apps",
    "benchmarks",
    "configs",
    "database",
    "docker",
    "fixtures",
    "packages",
    "schemas",
    "requirements-db.txt",
    "requirements-engine.txt",
    "docker-compose.yml",
    "pytest.ini"
)

foreach ($Item in $BundleItems) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $Item) -Destination $ProjectOutput -Recurse -Force
}

Copy-Item -LiteralPath (Join-Path $BundleSource "server\launch.js") -Destination (Join-Path $StagingRoot "server\launch.js") -Force
Copy-Item -LiteralPath (Join-Path $BundleSource ".mcpbignore") -Destination (Join-Path $StagingRoot ".mcpbignore") -Force

$Manifest = Get-Content -LiteralPath (Join-Path $BundleSource "manifest.json") -Raw | ConvertFrom-Json
$Manifest.version = $Version
$ManifestJson = $Manifest | ConvertTo-Json -Depth 10
$Utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $StagingRoot "manifest.json"), $ManifestJson, $Utf8WithoutBom)

$SecretFiles = Get-ChildItem -LiteralPath $StagingRoot -Recurse -Force -File | Where-Object {
    $_.Name -eq ".env" -or $_.Name -like ".env.*"
}
if ($SecretFiles) {
    throw "Secret environment files cannot be included in a bundle"
}

& npx.cmd --yes @anthropic-ai/mcpb validate $StagingRoot
if ($LASTEXITCODE -ne 0) {
    throw "MCPB manifest validation failed"
}

& npx.cmd --yes @anthropic-ai/mcpb pack $StagingRoot $BundleOutput
if ($LASTEXITCODE -ne 0) {
    throw "MCPB bundle creation failed"
}

Write-Output "MCPB bundle created: $BundleOutput"
