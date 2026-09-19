\# Development Steps

&nbsp;

\#\# Phase 1: Evaluation Data, Benchmarks, Fixtures, Environment

Goal: define what the framework measures before building interfaces.

&nbsp;

Tasks:

\- Define generic evaluation categories.

\- Create benchmark schema.

\- Create 10-30 initial benchmark tasks.

\- Create reproducible fixtures.

\- Define expected outcomes and limits.

&nbsp;

Generic categories:

\- Task success

\- Planning

\- Tool use

\- Recovery

\- Robustness

\- Cost

\- Latency

\- Safety

&nbsp;

Coding categories:

\- Bug fix

\- Code generation

\- Test fix

\- Refactoring

\- Repository understanding

&nbsp;

Done when:

\- Benchmark schema exists.

\- Fixtures can reset to a clean state.

\- Expected outputs are explicit.

\- Initial benchmark set is runnable in principle.

&nbsp;

\#\# Phase 2: PostgreSQL

Goal: create local persistence for real evaluation runs.

&nbsp;

Initial tables:

\- runs

\- events

\- metrics

\- evaluations

&nbsp;

Recommended stack:

\- SQLAlchemy

\- Alembic

\- PostgreSQL JSONB

&nbsp;

Done when:

\- Migration works.

\- create\_run / add\_event / add\_metric / finish\_run / get\_run work.

\- One run can be reconstructed from persisted events.

&nbsp;

\#\# Phase 3: Python Evaluation Engine / Evaluation Agent

Goal: complete the core framework before API or MCP.

&nbsp;

Build:

\- Pydantic models

\- Benchmark loader / validator

\- Environment setup

\- LangGraph evaluation workflow

\- OpenRouter integration

\- Event collector

\- Evaluators

\- Persistence

\- Terminal output

&nbsp;

Core workflow:

\`\`\`text

START

&nbsp;\-\> load\_benchmark

&nbsp;\-\> setup\_environment

&nbsp;\-\> run\_agent

&nbsp;\-\> collect\_trajectory

&nbsp;\-\> evaluate

&nbsp;\-\> persist

&nbsp;\-\> END

\`\`\`

&nbsp;

Initial evaluators:

\- success

\- trajectory

\- tool\_usage

\- recovery

\- cost

\- latency

\- robustness

\- safety

&nbsp;

Done when the whole flow works from terminal without Go, API, MCP, or package publishing.

&nbsp;

\#\# Phase 4: Go CLI / TUI

Start with CLI:

\`\`\`bash

agent-eval run benchmark.yaml

agent-eval list

agent-eval show run\_001

agent-eval trace run\_001

agent-eval compare run\_001 run\_002

\`\`\`

&nbsp;

Initial integration may use Python subprocess.

After Phase 6, migrate to HTTP.

&nbsp;

Then add TUI:

\- Run list

\- Run details

\- Trace view

\- Error view

\- Compare view

&nbsp;

\#\# Phase 5: Tests and Fixes

Python unit tests:

\- benchmark loader

\- validator

\- evaluators

\- cost calculator

\- trajectory parser

\- repositories

\- service layer

&nbsp;

Go unit tests:

\- command parsing

\- formatting

\- config

\- API client later

&nbsp;

Integration flow:

\`\`\`text

benchmark \-\> execution \-\> events \-\> evaluation \-\> PostgreSQL

\`\`\`

&nbsp;

Failure tests:

\- LLM timeout

\- OpenRouter 429 / 500

\- tool failure

\- invalid YAML

\- missing benchmark

\- DB error

\- malformed model response

&nbsp;

Regression tests:

\- Compare current results to baseline.

\- Detect success, cost, latency, trajectory, and recovery regressions.

&nbsp;

\#\# Phase 6: REST API

Use FastAPI.

&nbsp;

Minimum endpoints:

\`\`\`text

POST /runs

POST /runs/{id}/events

POST /runs/{id}/finish

POST /evaluate

GET /runs

GET /runs/{id}

GET /runs/{id}/trace

GET /runs/{id}/metrics

GET /compare

\`\`\`

&nbsp;

Routes call EvaluationService.

Do not place evaluation logic inside route handlers.

&nbsp;

At this phase:

\`\`\`text

Go \-\> HTTP \-\> FastAPI \-\> EvaluationService \-\> PostgreSQL

\`\`\`

&nbsp;

\#\# Phase 7: MCP Server

Python implementation.

&nbsp;

Suggested tools:

\- evaluate\_agent

\- run\_benchmark

\- get\_run

\- get\_trace

\- get\_errors

\- compare\_runs

\- run\_regression

&nbsp;

MCP and REST API call the same EvaluationService.

&nbsp;

\#\# Phase 8: Plugin System

Core stays domain-neutral:

\- success

\- trajectory

\- tool use

\- recovery

\- cost

\- latency

\- robustness

\- safety

&nbsp;

Coding plugin:

\- pytest

\- lint

\- type check

\- security

\- diff

\- complexity

\- regression

\- unnecessary file modification

&nbsp;

\#\# Phase 9: Real Coding-Agent Validation

Evaluate:

\- Custom LangGraph coding agent

\- Codex

\- OpenCode

&nbsp;

Compare:

\- Success

\- Cost

\- Latency

\- Steps

\- Tool calls

\- Recovery

\- Loop rate

\- Failure category

\- Coding plugin metrics

&nbsp;

\#\# Phase 10: Packaging and Distribution

Only after the framework is stable.

&nbsp;

Python:

\`\`\`bash

pip install ...

\`\`\`

&nbsp;

TypeScript:

\`\`\`bash

npm install ...

\`\`\`

&nbsp;

Tasks:

\- Public Python SDK

\- TypeScript API SDK

\- Stable schemas

\- Semantic versioning

\- PyPI / npm

\- GitHub Releases

\- Example projects

\- Public documentation

&nbsp;