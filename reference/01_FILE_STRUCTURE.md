\# Proposed Repository Structure

&nbsp;

\`\`\`text

agent-eval/

├── apps/

│   ├── api/                         \# Python / FastAPI

│   ├── mcp/                         \# Python MCP Server

│   └── cli/                         \# Go CLI / TUI

├── packages/

│   ├── core/                        \# Python evaluation engine

│   ├── sdk-python/                  \# Phase 10

│   └── sdk-typescript/              \# Phase 10

├── integrations/

│   ├── langgraph/

│   ├── openrouter/

│   └── opentelemetry/

├── plugins/

│   └── coding/

├── benchmarks/

│   ├── generic/

│   └── coding/

├── fixtures/

│   ├── generic/

│   └── coding/

├── database/

│   ├── models/

│   ├── repositories/

│   ├── migrations/

│   ├── session.py

│   └── base.py

├── schemas/

├── configs/

├── tests/

│   ├── unit/

│   ├── integration/

│   ├── e2e/

│   └── regression/

├── examples/

├── docs/

├── scripts/

├── docker/

├── .github/

├── .gitignore

├── .dockerignore

├── .env.example

├── docker-compose.yml

├── Makefile

├── LICENSE

├── SECURITY.md

├── CONTRIBUTING.md

├── CODE\_OF\_CONDUCT.md

├── CHANGELOG.md

└── README.md

\`\`\`

&nbsp;

\#\# Python Responsibilities

\- Evaluation engine

\- LangGraph

\- Benchmark runner

\- OpenRouter

\- OpenTelemetry

\- PostgreSQL

\- FastAPI

\- MCP server

\- Plugins

&nbsp;

\#\# Go Responsibilities

\- CLI commands

\- TUI screens

\- Formatting

\- User interaction

\- HTTP client after Phase 6

&nbsp;

Go must not:

\- Reimplement evaluator logic

\- Connect directly to PostgreSQL

\- Own benchmark semantics

&nbsp;

\#\# PostgreSQL Access

\`\`\`text

Go CLI/TUI

&nbsp;&nbsp;&nbsp;\-\> Python layer

&nbsp;&nbsp;&nbsp;\-\> EvaluationService

&nbsp;&nbsp;&nbsp;\-\> Repository layer

&nbsp;&nbsp;&nbsp;\-\> PostgreSQL

\`\`\`

&nbsp;