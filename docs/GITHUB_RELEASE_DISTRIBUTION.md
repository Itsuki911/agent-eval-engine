# GitHub Releases による MCPB 配布

## 配布の正規経路

MCPB は GitHub Releases から配布する。評価エンジン、PostgreSQL、評価データ、実行履歴は利用者の PC 上で動作・保存される。

tag `v*` を push すると `Release MCPB` workflow が次を行う。

1. `scripts/build_mcpb.ps1` で bundle を作成する。
2. `agent-eval-engine.mcpb.sha256` を作成する。
3. 同名 tag の GitHub Release に bundle と checksum を添付する。

## リリース担当者の手順

事前に CI が対象 commit で成功していることを確認する。

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Actions の `Release MCPB` が成功した後、Release の Assets に次の2ファイルがあることを確認する。

- `agent-eval-engine.mcpb`
- `agent-eval-engine.mcpb.sha256`

## 利用者の確認手順

Release から2ファイルを同じフォルダへ保存してから、checksum と manifest を確認する。

```powershell
$expected = (Get-Content .\agent-eval-engine.mcpb.sha256).Split(' ')[0]
$actual = (Get-FileHash -Algorithm SHA256 .\agent-eval-engine.mcpb).Hash.ToLower()
if ($actual -ne $expected) { throw "checksum が一致しません" }
npx.cmd --yes @anthropic-ai/mcpb info .\agent-eval-engine.mcpb
```

期待結果は checksum が一致し、`agent-eval-engine` の bundle 情報が表示されることである。bundle は未署名のため、必ず公式 GitHub Release から取得し、checksum を確認して利用する。

## Smithery の扱い

Smithery Registry の MCPB 公開は、2026-09-27 時点で upstream の `400 No values to set` により保留する。GitHub Releases の配布とローカル stdio 実行は影響を受けない。復旧後に別途 publish を再試行する。
