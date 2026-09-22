
# Agent Evaluation Framework

AIエージェントのタスク成功だけでなく、ツール利用、回復性、安全性、コスト、遅延、
coding品質を評価するためのフレームワークです。

現在はPhase 1として、再現可能なbenchmark・fixture・Docker検証環境を提供します。
エージェント実行、PostgreSQL、REST API、MCPは後続Phaseの対象です。

## Phase 1の内容

- generic benchmark: ツール利用、回復、安全性、prompt injection、境界保護。
- coding benchmark: Python、Go、C、Bash、PowerShell、TypeScript。
- fixture: 環境初期化、ツール応答、workspace、保護された検証領域。
- Docker validator: YAML schema、命名規則、fixture参照、必須ディレクトリを検証。

## はじめ方

```bash
python scripts/generate_phase1_benchmarks.py
python scripts/validate_phase1.py --check-fixtures
```

Dockerを利用できる環境では、次も実行できます。

```bash
docker compose build evaluator
docker compose run --rm evaluator
```

詳細は、[benchmarks/README.md](benchmarks/README.md)、[fixtures/README.md](fixtures/README.md)、
[docker/README.md](docker/README.md)、[docs/PHASE1_WORK_REPORT.md](docs/PHASE1_WORK_REPORT.md)を参照してください。
