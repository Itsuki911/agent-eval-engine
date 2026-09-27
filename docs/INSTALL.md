# インストールガイド (Installation Guide)

Agent Eval Engine のインストール手順です。
本ツールは、利用者の端末から直接 `agent-eval` コマンドで TUI や CLI を起動できる単一バイナリとして配布されます。

---

## 1. 対応環境と前提条件

### 対応 OS / アーキテクチャ
- **Windows**: x86_64 (`windows_amd64`), ARM64 (`windows_arm64`)
- **macOS**: Apple Silicon (`darwin_arm64`), Intel (`darwin_amd64`)
- **Linux**: x86_64 (`linux_amd64`)

### 前提ソフトウェア
- **Docker Desktop** または **Docker Engine** (Compose v2 対応)
  - 評価エンジン (Python) とデータストレージ (PostgreSQL) は Docker コンテナ内で安全に分離実行されます。
  - ホスト端末に Python や Go の開発環境をインストールする必要はありません。

---

## 2. Windows へのインストール

PowerShell 7 または Windows PowerShell 5.1 を開き、以下のワンライナーまたはインストーラースクリプトを実行します。

### インストーラースクリプトを使用する場合

```powershell
# GitHub Releases またはリポジトリからスクリプトを実行
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

特定のバージョンを指定する場合:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Version "1.0.0"
```

インストーラーの動作:
1. GitHub Releases より最新の `agent-eval-windows-amd64.zip` と `checksums.txt` をダウンロードします。
2. SHA-256 チェックサムを自動検証し、改ざんや破損がないことを確認します。
3. `%LOCALAPPDATA%\Programs\AgentEvalEngine` に `agent-eval.exe` を配置します。
4. ユーザー環境変数 `PATH` に上記ディレクトリを追加します。

### 手動インストールの場合
1. GitHub Releases ページから `agent-eval-windows-amd64.zip` をダウンロードします。
2. `agent-eval.exe` を任意のフォルダ（例: `C:\Tools\agent-eval.exe`）に解凍します。
3. 解凍先フォルダをシステム環境変数 `PATH` に追加します。

---

## 3. macOS / Linux へのインストール

### 手動インストール手順

```bash
# 1. GitHub Releases から対応アーカイブをダウンロード
# 例 (macOS Apple Silicon):
curl -LO https://github.com/Itsuki911/agent-eval-engine/releases/latest/download/agent-eval-darwin-arm64.tar.gz
curl -LO https://github.com/Itsuki911/agent-eval-engine/releases/latest/download/checksums.txt

# 2. SHA-256 チェックサムを検証
shasum -a 256 --check checksums.txt --ignore-missing

# 3. 解凍と配置
tar -xzf agent-eval-darwin-arm64.tar.gz
chmod +x agent-eval
sudo mv agent-eval /usr/local/bin/

# 4. バージョン確認
agent-eval version
```

---

## 4. インストール確認と初期診断

端末を再起動（または新しいターミナルを開き）、以下を実行します。

```text
agent-eval version
agent-eval doctor
```

`agent-eval doctor` が実行環境（Docker, ストレージ, 設定）を診断し、準備状況を日本語で案内します。
問題がなければ、続いて初期化を行います（詳細は [docs/SETUP.md](SETUP.md) を参照）。
