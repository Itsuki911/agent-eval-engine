# Agent Eval Engine Release vX.Y.Z

## 主な変更点 (What's New)
- 新機能や改善点の要約

## 配布バイナリ (Binaries)
以下の配布バイナリが本リリースに含まれています:
- `agent-eval-windows-amd64.zip` (Windows x86_64)
- `agent-eval-windows-arm64.zip` (Windows ARM64)
- `agent-eval-darwin-amd64.tar.gz` (macOS Intel)
- `agent-eval-darwin-arm64.tar.gz` (macOS Apple Silicon)
- `agent-eval-linux-amd64.tar.gz` (Linux x86_64)
- `agent-eval-mcpb.zip` (MCPB パッケージ)
- `sbom.json` (ソフトウェア部品表)
- `checksums.txt` (各バイナリの SHA-256 チェックサム)

## インストール手順 (Quick Install)
### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Version "X.Y.Z"
```

### macOS / Linux
```bash
tar -xzf agent-eval-<os>-<arch>.tar.gz
chmod +x agent-eval
sudo mv agent-eval /usr/local/bin/
agent-eval version
agent-eval doctor
```

## チェックサム検証
```bash
# SHA-256 チェックサムの照合
sha256sum -c checksums.txt
```
