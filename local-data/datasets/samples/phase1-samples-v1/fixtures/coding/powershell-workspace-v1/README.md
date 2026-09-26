# powershell-workspace-v1

PowerShell 7.5向けのworkspaceと保護された検証領域です。`COD-PS-*` が参照します。
Windowsを正式サポートし、検証コマンドは `pwsh -File ../verify/check.ps1` です。

Windows ContainersモードのDocker Desktopでは、次を実行できます。

```powershell
docker compose -f docker-compose.windows.yml run --rm powershell-fixture
```
