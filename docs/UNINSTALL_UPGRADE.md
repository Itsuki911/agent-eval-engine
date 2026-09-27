# アップグレードとアンインストール手順 (Upgrade & Uninstall Guide)

Agent Eval Engine のバージョン更新および完全削除の手順です。

---

## 1. アップグレード手順

### Windows の場合
インストーラースクリプトを再実行することで、最新のバイナリに自動更新されます。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

手動更新の場合は、GitHub Releases から新しい `agent-eval.exe` をダウンロードし、既存の実行ファイルと置き換えてください。

### macOS / Linux の場合
新しいバージョンのバイナリをダウンロードし、`/usr/local/bin/agent-eval` に上書き配置します。

```bash
chmod +x agent-eval
sudo mv agent-eval /usr/local/bin/agent-eval
```

### アップグレード後の確認
バイナリ更新後、マイグレーションと動作確認を実行します:

```bash
agent-eval version
agent-eval doctor
```
新しいデータベース migration がある場合、`agent-eval init` または `agent-eval doctor` が自動的に適用を案内します。

> [!NOTE]
> ユーザーデータ（ベンチマーク、トレース履歴、設定、PostgreSQL データベース）はバイナリとは完全に分離されているため、バイナリを更新しても削除されません。

---

## 2. アンインストール手順

Agent Eval Engine をシステムから完全に削除する場合は、以下の手順を実行します。

### ステップ 1: Docker リソースの停止と削除
リポジトリまたは作業ディレクトリでコンテナとボリュームを削除します。

```bash
docker compose down -v
```
※ `-v` フラグを付けると、PostgreSQL データベースの Docker ボリュームも完全に消去されます。

### ステップ 2: ユーザーデータディレクトリの削除
OS ごとのデータ保存先フォルダを手動で削除します。

- **Windows**:
  ```powershell
  Remove-Item -Recurse -Force "$env:LOCALAPPDATA\AgentEvalEngine"
  Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Programs\AgentEvalEngine"
  ```
  ※ 必要に応じて環境変数 `PATH` から `AgentEvalEngine` のパスを削除してください。

- **macOS**:
  ```bash
  rm -rf ~/Library/Application\ Support/AgentEvalEngine
  sudo rm /usr/local/bin/agent-eval
  ```

- **Linux**:
  ```bash
  rm -rf ~/.local/share/agent-eval-engine
  sudo rm /usr/local/bin/agent-eval
  ```
