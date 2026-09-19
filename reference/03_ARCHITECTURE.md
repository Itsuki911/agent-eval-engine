\# Architecture

&nbsp;

\#\# High-Level Architecture

&nbsp;

\`\`\`text

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Go CLI / TUI

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| HTTP (after Phase 6\)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FastAPI

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;EvaluationService

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+--------------+--------------+

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|              |              |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v              v              v

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Evaluators       LangGraph       Plugins

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|              |              |

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+--------------+--------------+

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PostgreSQL

&nbsp;

External agent / Codex / OpenCode

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+---- REST API

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+---- MCP Server

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\+---- Python SDK (Phase 10\)

\`\`\`

&nbsp;

\#\# Core Rule

All interfaces reuse EvaluationService.

&nbsp;

Do not duplicate evaluation logic in:

\- FastAPI routes

\- MCP tools

\- Go CLI

\- SDKs

&nbsp;

\#\# EvaluationService

Coordinates:

\- benchmark loading

\- environment setup

\- execution

\- trace collection

\- metric calculation

\- persistence

\- comparison

&nbsp;

\#\# LangGraph

Suggested evaluation workflow:

\`\`\`text

load\_benchmark

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

setup\_environment

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

run\_agent

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

collect\_trajectory

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

evaluate

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

persist

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|

END

\`\`\`

&nbsp;

\#\# OpenRouter

Record:

\- provider

\- model

\- input tokens

\- output tokens

\- latency

\- API cost when available

\- request success / failure

&nbsp;

\#\# OpenTelemetry

Instrument:

\- agent run

\- LangGraph node

\- tool call

\- LLM call

\- error / retry

&nbsp;

Suggested spans:

\`\`\`text

agent.run

├── planner

│   └── llm.call

├── inspect

│   ├── tool.read

│   └── tool.search

├── edit

│   └── tool.write

├── test

│   └── tool.bash

└── reflection

&nbsp;&nbsp;&nbsp;&nbsp;└── llm.call

\`\`\`

&nbsp;

\#\# Go Layer

Responsibilities:

\- argument parsing

\- command dispatch

\- API calls

\- terminal rendering

\- TUI navigation

\- local configuration

&nbsp;

No evaluation algorithm belongs in Go.

&nbsp;

\#\# Interface Evolution

Phase 3:

\`\`\`text

Terminal \-\> Python Core \-\> PostgreSQL

\`\`\`

&nbsp;

Phase 4:

\`\`\`text

Go CLI \-\> Python subprocess \-\> Python Core \-\> PostgreSQL

\`\`\`

&nbsp;

Phase 6+:

\`\`\`text

Go CLI/TUI \-\> FastAPI \-\> EvaluationService \-\> PostgreSQL

MCP        \-\> EvaluationService \-\> PostgreSQL

\`\`\`

&nbsp;

Phase 10:

\`\`\`text

Python Agent \-\> Python SDK \-\> Core/API

TypeScript Agent \-\> TS SDK \-\> REST API

Other language \-\> REST API

\`\`\`

&nbsp;