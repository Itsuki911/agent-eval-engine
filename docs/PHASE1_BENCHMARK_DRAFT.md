# Phase 1 Benchmark Draft

## Purpose

This is a review draft for the evaluation data, benchmark, and fixture
contracts. It defines no runner or external-service integration.

## Scope

- `generic`: tool selection, tool execution, recovery, and safety tasks.
- `coding`: repository-based tasks that are verified by commands.
- `terminal`: a capability tag for tasks that require a shell environment.
- `web` and `gui`: deferred. Their future adapters use the same contracts.

## Reference patterns adopted

| Reference | Adopted element |
| --- | --- |
| SWE-bench | Issue-like task, reproducible workspace, verification command, patch constraints |
| Terminal-Bench | Isolated environment contract, reset, limits, and oracle stability check |
| tau-bench | Stateful tool interaction, policy constraints, failure/retry/recovery evaluation |
| BFCL | Tool-call syntax, semantic argument, and execution-result evaluation |
| AgentBench | Pluggable environment and evaluator interfaces |
| WebArena / OSWorld | Future final-state evaluation and environment snapshots |

## Phase 1 decisions for review

1. YAML is the source format; JSON Schema validates its shape.
2. A benchmark declares the task and scoring contract. A fixture declares only
   reproducible starting state and environment behavior.
3. Final-state assertions are preferred over fixed action sequences.
4. The initial public suite must be self-contained: no network, credentials,
   private data, or unlicensed third-party repository snapshot.
5. Actual regression baselines are added after the runner exists; they are not
   part of this draft.

## Proposed initial suite

| Family | Count | Focus |
| --- | ---: | --- |
| Tool selection and arguments | 4 | correct tool, arguments, absent-tool handling |
| Tool execution and recovery | 4 | timeout, rate limit, validation error, retry limit |
| Safety and policy | 2 | forbidden action, confirmation requirement |
| Coding | 4 | Python bug fix, Go bug fix, test fix, repository understanding |
| Terminal | 2 | workspace command task, failure diagnosis |

## Open questions

- Should one benchmark allow more than one fixture variant for robustness runs?
- Which metrics are hard pass/fail gates, and which are reported only?
- Should tool-call semantic checks use a custom assertion DSL or evaluator
  plugins from the start?
- What license policy applies when a coding fixture is derived from an existing
  repository?
