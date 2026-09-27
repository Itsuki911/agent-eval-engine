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

### A. 最速ワンライナー (推奨・clone 不要)
PowerShell 7 または Windows PowerShell 5.1 を開き、以下を実行します:

```powershell
irm https://raw.githubusercontent.com/Itsuki911/agent-eval-engine/main/scripts/install.ps1 | iex
```

### B. リポジトリをクローンして導入する場合 (開発者向け)
```powershell
git clone https://github.com/Itsuki911/agent-eval-engine.git
cd agent-eval-engine
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

### インストーラーの動作:
1. GitHub Releases より最新の `agent-eval_windows_<arch>.zip` と `checksums.txt` を取得します。
2. SHA-256 チェックサムを自動検証し、改ざんや破損がないことを確認します。
3. `%LOCALAPPDATA%\Programs\AgentEval\bin` に `agent-eval.exe` を配置します。
4. ユーザー環境変数 `PATH` に上記ディレクトリを追加します。
5. `agent-eval init` 時に、GHCR (`ghcr.io/itsuki911/agent-eval-engine:latest`) を利用するスタンドアロン Compose 環境が自動構築されます。

---

## 3. macOS / Linux へのインストール

### A. 最速ワンライナー (推奨・clone 不要)
ターミナル (Bash / Zsh) を開き、以下を実行します:

```bash
curl -fsSL https://raw.githubusercontent.com/Itsuki911/agent-eval-engine/main/scripts/install.sh | bash
```

### B. リポジトリをクローンして導入する場合 (開発者向け)
```bash
git clone https://github.com/Itsuki911/agent-eval-engine.git
cd agent-eval-engine
chmod +x ./scripts/install.sh
./scripts/install.sh
```

### シェルインストーラーの動作:
1. OS (`Darwin` / `Linux`) と CPU (`arm64` / `amd64`) を自動判定します。
2. GitHub Releases から対応アーカイブと `checksums.txt` を取得し、SHA-256 を検証します。
3. `/usr/local/bin/agent-eval`（権限がない場合は `~/.local/bin/agent-eval`）へバイナリを配置します。
4. `agent-eval init` 時に、GHCR イメージを利用する Compose 定義が自動配置されます。
5. （リポジトリ内で実行した場合）リポジトリパスを `~/Library/Application Support/AgentEvalEngine/config/repo_root.txt`（Linux は `~/.local/share/...`）に自動保存します。

---

## 4. 手動インストールの場合

GitHub Releases ページから直接アーカイブをダウンロードして手動配置することも可能です。

### 手動手順
1. Releases ページから `agent-eval_<os>_<arch>.tar.gz` (Windows は `.zip`) をダウンロードします。
2. `shasum -a 256` (または `sha256sum`) で `checksums.txt` と突合します。
3. 解凍した `agent-eval` を PATH が通ったディレクトリに配置します。
4. リポジトリのディレクトリで一度 `agent-eval init` を実行すると、リポジトリのパスが自動記憶されます。

---

## 5. インストール確認と初期診断

新しいターミナルを開き、以下を実行します。

```text
agent-eval version
agent-eval init
agent-eval doctor
```

`agent-eval doctor` がすべての環境チェック（Docker, DB, ストレージ, MCP）に `[OK]` を出せば準備完了です。
引数なしで `agent-eval` を実行して TUI を起動してください。
