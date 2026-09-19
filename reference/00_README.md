\# Agent Evaluation Framework

&nbsp;

\#\# Overview

This project is a reusable evaluation and observability framework for AI agents.

&nbsp;

Primary goals:

\- Evaluate agent performance beyond binary task success.

\- Measure trajectory quality, tool usage, recovery, cost, latency, robustness, and safety.

\- Support coding-agent-specific evaluation through plugins.

\- Make debugging easy by preserving detailed execution traces.

\- Reuse the same evaluation framework across multiple agent projects.

\- Support local development first, then REST API, MCP, plugins, and package distribution.

&nbsp;

\#\# Main Technology Choices

\- Python: evaluation engine, LangGraph integration, OpenRouter integration, database access, REST API, MCP server, plugins, benchmarks.

\- Go: CLI and TUI only.

\- PostgreSQL: local development database and persistence layer. Accessed only through Python.

\- LangGraph: evaluation workflow / agent execution orchestration.

\- OpenRouter: API model provider.

\- OpenTelemetry: trace and trajectory instrumentation.

\- FastAPI: REST API.

\- MCP: Python implementation.

\- GitHub: public repository and CI/CD target.

&nbsp;

\#\# Core Principle

Go does not implement evaluation logic and does not connect directly to PostgreSQL.

&nbsp;

Go CLI/TUI \-\> Python API / process interface \-\> EvaluationService \-\> Evaluators / Plugins \-\> PostgreSQL

&nbsp;

All public interfaces should reuse the same Python EvaluationService.

&nbsp;

\#\# Development Phases

1\. Evaluation datasets, benchmarks, fixtures, environment

2\. PostgreSQL

3\. Python evaluation engine / evaluation agent

4\. Go CLI / TUI

5\. Unit, integration, E2E, regression tests

6\. REST API

7\. MCP server

8\. Plugin system

9\. Real coding-agent tests with Codex / OpenCode / custom agents

10\. Python/npm packaging and distribution

&nbsp;

\#\# Initial Development Target

The first working milestone is Phase 3:

\- Load benchmark YAML/JSON

\- Run an agent

\- Record events / trajectory

\- Compute metrics

\- Persist run data

\- Print results in the terminal

&nbsp;

Do not start by building the API, MCP, or package publishing workflow.

&nbsp;

\#\# Suggested First Commands

\`\`\`bash

git init

python \-m venv .venv

source .venv/bin/activate

&nbsp;

\# Later

docker compose up \-d postgres

pytest

go test ./...

\`\`\`

&nbsp;

\#\# Security

Never commit:

\- .env

\- OpenRouter API keys

\- Database passwords

\- credentials.json

\- private benchmark data

&nbsp;

Use .env.example for public configuration templates.

&nbsp;