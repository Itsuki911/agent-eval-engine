# GitHub Releases MCPB 配布手動E2Eテスト

## E2E-RELEASE-001：tagをpushしてMCPBをGitHub Releaseへ公開できる

- 種別: 正常系

```powershell
git tag v0.1.0
git push origin v0.1.0
```

手順:

1. 対象 commit の CI 成功を確認する。
2. 未使用の version tag を作成する。
3. tag を push する。
4. GitHub Actions の `Release MCPB` を開く。
5. GitHub Release の Assets を確認する。

期待結果:

- `Release MCPB` は成功する。
- 対応 tag の Release に `agent-eval-engine.mcpb` と `agent-eval-engine.mcpb.sha256` が添付される。
- version は tag の `v` を除いた値になる。

## E2E-RELEASE-002：Release MCPBのchecksum不一致を検出できる

- 種別: 異常系

```powershell
$expected = "0" * 64
$actual = (Get-FileHash -Algorithm SHA256 .\agent-eval-engine.mcpb).Hash.ToLower()
if ($actual -ne $expected) { "checksum mismatch detected" }
```

手順:

1. Release から MCPB をダウンロードする。
2. コマンドを実行する。
3. 出力を確認する。

期待結果:

- `checksum mismatch detected` が表示される。
- checksum が一致しない bundle を利用しない。
