<#
.SYNOPSIS
    Agent Eval Engine Windows インストーラー
.DESCRIPTION
    GitHub Releases から agent-eval ネイティブバイナリを取得し、
    SHA-256 チェックサムを検証した上で安全にインストールします。
#>

[CmdletBinding()]
param (
    [string]$Version = "latest",
    [string]$Repo = "itsuki911/agent-eval-engine",
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\AgentEval\bin",
    [string]$ArchiveFile = "",
    [string]$ChecksumFile = "",
    [switch]$DryRun,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       Agent Eval Engine Windows インストーラー" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# アーキテクチャの判定 (amd64 / arm64)
$arch = "amd64"
if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
    $arch = "arm64"
}
$assetName = "agent-eval_windows_$arch.zip"

Write-Host "対象アーキテクチャ: $arch"
Write-Host "インストール先:   $InstallDir"

# 作業用一時ディレクトリ
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("agent-eval-install-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    $zipPath = ""
    $checksumPath = ""

    if ($ArchiveFile -ne "" -and (Test-Path $ArchiveFile)) {
        Write-Host "ローカルアーカイブを使用: $ArchiveFile"
        $zipPath = (Resolve-Path $ArchiveFile).Path
    } else {
        Write-Host "GitHub Releases ($Repo) から $assetName を取得中..."
        $downloadUrl = "https://github.com/$Repo/releases/latest/download/$assetName"
        if ($Version -ne "latest") {
            $downloadUrl = "https://github.com/$Repo/releases/download/$Version/$assetName"
        }
        $zipPath = Join-Path $tempDir $assetName
        if (-not $DryRun) {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        }
    }

    if ($ChecksumFile -ne "" -and (Test-Path $ChecksumFile)) {
        Write-Host "ローカルチェックサムを使用: $ChecksumFile"
        $checksumPath = (Resolve-Path $ChecksumFile).Path
    } else {
        Write-Host "checksums.txt を取得中..."
        $checksumUrl = "https://github.com/$Repo/releases/latest/download/checksums.txt"
        if ($Version -ne "latest") {
            $checksumUrl = "https://github.com/$Repo/releases/download/$Version/checksums.txt"
        }
        $checksumPath = Join-Path $tempDir "checksums.txt"
        if (-not $DryRun) {
            Invoke-WebRequest -Uri $checksumUrl -OutFile $checksumPath -UseBasicParsing
        }
    }

    if (-not $DryRun) {
        # SHA-256 チェックサムの検証
        Write-Host "SHA-256 チェックサムを検証しています..."
        $calculatedHash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLower()

        $checksumContent = Get-Content $checksumPath -Raw
        $expectedLine = ($checksumContent -split "`r?`n") | Where-Object { $_ -match $assetName }

        if (-not $expectedLine) {
            throw "【エラー】checksums.txt 内に $assetName のエントリが見つかりません。"
        }

        $expectedHash = ($expectedLine.Trim() -split "\s+")[0].ToLower()

        if ($calculatedHash -ne $expectedHash) {
            Write-Host "計算値: $calculatedHash" -ForegroundColor Red
            Write-Host "期待値: $expectedHash" -ForegroundColor Yellow
            throw "【セキュリティエラー】SHA-256 チェックサムが一致しません！アーカイブが破損または改ざんされている可能性があります。"
        }
        Write-Host "✓ SHA-256 チェックサム検証に合格しました: $calculatedHash" -ForegroundColor Green

        # インストール先ディレクトリの準備
        if (-not (Test-Path $InstallDir)) {
            New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        }

        # 展開
        Write-Host "アーカイブを展開中..."
        Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force
        $extractedExe = Join-Path $tempDir "agent-eval.exe"
        if (-not (Test-Path $extractedExe)) {
            $found = Get-ChildItem -Path $tempDir -Filter "agent-eval.exe" -Recurse | Select-Object -First 1
            if ($found) {
                $extractedExe = $found.FullName
            } else {
                throw "アーカイブ内に agent-eval.exe が見つかりませんでした。"
            }
        }

        $targetExe = Join-Path $InstallDir "agent-eval.exe"
        Copy-Item -Path $extractedExe -Destination $targetExe -Force
        Write-Host "✓ バイナリを配置しました: $targetExe" -ForegroundColor Green

        # PATH の確認
        $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($userPath -notlike "*$InstallDir*") {
            Write-Host ""
            Write-Host "【PATH 設定】" -ForegroundColor Yellow
            Write-Host "コマンドプロンプトや PowerShell から agent-eval を直接呼び出せるように、ユーザー環境変数の PATH へ追加することをお勧めします。"
            if (-not $NonInteractive) {
                $answer = Read-Host "ユーザー環境変数 PATH に $InstallDir を追加しますか？ (Y/n)"
                if ($answer -ne "n" -and $answer -ne "N") {
                    $newPath = ($userPath + ";" + $InstallDir).Trim(";")
                    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
                    $env:PATH = "$env:PATH;$InstallDir"
                    Write-Host "✓ ユーザー PATH に追加しました。新しいターミナルで有効になります。" -ForegroundColor Green
                }
            } else {
                Write-Host ('手動で追加する場合: [Environment]::SetEnvironmentVariable("PATH", "$env:PATH;' + $InstallDir + '", "User")')
            }
        }

        # 動作確認
        Write-Host ""
        Write-Host "インストール確認を実行中..."
        & $targetExe version
    } else {
        Write-Host "[DryRun] インストール処理シミュレーション完了" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "✓ agent-eval のインストールが正常に完了しました！" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "次のステップ:"
    Write-Host "  1. 新しいターミナルを開きます"
    Write-Host "  2. 初回設定: agent-eval init"
    Write-Host "  3. 環境診断: agent-eval doctor"
    Write-Host "  4. 画面起動: agent-eval (TUI)"
    Write-Host ""

} finally {
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
