\# VS Code \+ Codex Development Guide

&nbsp;

\#\# Rule for Codex

Do not build the entire repository at once.

&nbsp;

For every phase:

1\. Inspect existing files.

2\. Propose a minimal change plan.

3\. Implement only the current phase.

4\. Run tests / commands.

5\. Report changed files.

6\. Report unresolved issues.

7\. Do not begin the next phase automatically.

&nbsp;

\#\# Recommended First Milestone

Build Phase 1 and Phase 2 first.

&nbsp;

Phase 1:

\- repository skeleton

\- benchmark schema

\- benchmark loader contract

\- 10-30 sample benchmark definitions

\- fixtures

\- environment reset mechanism

\- documentation

&nbsp;

Phase 2:

\- local PostgreSQL docker-compose setup

\- SQLAlchemy models

\- Alembic migrations

\- repository layer

\- minimal CRUD tests

&nbsp;

Do not add FastAPI or MCP yet.

&nbsp;

\#\# Suggested Codex Prompt Template

&nbsp;

\`\`\`text

You are implementing Phase \<N\> of an Agent Evaluation Framework.

&nbsp;

Before coding:

1\. Read README.md, FILE\_STRUCTURE.md, DEVELOPMENT\_STEPS.md, ARCHITECTURE.md, and EVALUATION\_DESIGN.md.

2\. Inspect the repository.

3\. Do not implement later phases.

4\. Prefer simple, maintainable code over premature abstraction.

5\. Keep evaluation logic in Python.

6\. Go is only for CLI/TUI.

7\. PostgreSQL must only be accessed through Python.

8\. Do not put evaluation logic in Go, FastAPI routes, or MCP wrappers.

9\. Add tests for every core behavior introduced.

10\. At the end, summarize changed files, commands run, test results, and remaining TODOs.

&nbsp;

Current phase:

\<describe the phase here\>

&nbsp;

Acceptance criteria:

\<copy the Done when section from DEVELOPMENT\_STEPS.md\>

\`\`\`

&nbsp;

\#\# Development Discipline

Python:

\- Python 3.12+

\- Pydantic

\- SQLAlchemy

\- Alembic

\- pytest

\- LangGraph

\- OpenTelemetry

\- httpx

\- FastAPI when Phase 6 begins

&nbsp;

Go:

\- Introduce only in Phase 4

\- Cobra for CLI

\- Bubble Tea for TUI

&nbsp;

Configuration:

\- .env for secrets

\- .env.example for public template

\- YAML for benchmark/config definitions

\- JSON Schema for interoperability

&nbsp;

\#\# Git Strategy

Suggested branches:

\`\`\`text

main

develop

feature/phase-1-benchmarks

feature/phase-2-database

feature/phase-3-core

...

\`\`\`

&nbsp;

Avoid one giant commit for an entire phase.

&nbsp;

\#\# GitHub Public Repository Checklist

Before first public push:

\- remove all secrets

\- add .gitignore

\- add .env.example

\- add LICENSE

\- add SECURITY.md

\- add CONTRIBUTING.md

\- add README

\- ensure fixtures contain no private data

\- verify benchmark licensing

\- verify third-party sample repository licensing

\- enable CI

\- add issue templates

&nbsp;

\#\# Phase 10 Reminder

Do not spend time on PyPI/npm packaging until:

\- API schemas are stable

\- SDK-facing models are stable

\- integration tests pass

\- real coding-agent validation is complete

&nbsp;