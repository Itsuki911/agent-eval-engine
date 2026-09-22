# fixtures

fixtureはbenchmarkを開始するたびに復元される初期状態です。タスク本文や採点閾値は含めず、環境、ツール、workspace、検証コマンドだけを定義します。

## 共通ルール

- `fixture.yaml` にID、family、reset方法、環境、検証方法を記載する。
- IDは `<name>-v<version>` の形式にする。
- 外部ネットワーク、認証情報、個人情報、非公開データに依存しない。
- `workspace/` はエージェントが変更可能、`verify/` は変更禁止にする。
- 初期状態を変更したら同じIDを上書きせず、新しいversionを作る。

## 利用方法

`python scripts/validate_phase1.py --check-fixtures` で、全benchmarkが参照するfixtureと必須ディレクトリを確認できます。
