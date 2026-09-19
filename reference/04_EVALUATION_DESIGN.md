\# Evaluation Design

&nbsp;

\#\# Core Policy

Do not reduce agent performance to one pass/fail result.

Store and report dimensions independently.

&nbsp;

\#\# Generic Evaluation Dimensions

&nbsp;

\#\#\# Task Success

\- success

\- partial success

\- constraint satisfaction

&nbsp;

\#\#\# Trajectory

\- step count

\- redundant steps

\- repeated actions

\- loop count

\- plan revisions

\- invalid transitions

\- trajectory efficiency

&nbsp;

\#\#\# Tool Usage

\- tool-call success rate

\- invalid argument rate

\- duplicate tool calls

\- retry count

\- unnecessary calls

\- tool latency

&nbsp;

\#\#\# Recovery

\- recovery success

\- recovery steps

\- repeated failure loops

\- self-correction after tool / environment failure

&nbsp;

\#\#\# Cost

\- input tokens

\- output tokens

\- model/provider

\- API calls

\- tool calls

\- total estimated cost

\- cost per successful task

&nbsp;

\#\#\# Latency

\- end-to-end duration

\- per-node latency

\- per-tool latency

\- per-model-call latency

&nbsp;

\#\#\# Robustness

\- prompt variation

\- tool failure

\- tool replacement

\- environment changes

\- task phrasing changes

\- held-out task family performance

&nbsp;

\#\#\# Safety

\- forbidden action count

\- policy / constraint violation

\- unsafe command attempts

\- recovery after violation

\- sandbox boundary violations

&nbsp;

\#\# Coding Plugin Dimensions

\- test pass

\- build success

\- syntax / compile success

\- lint errors

\- type errors

\- security warnings

\- code complexity

\- diff size

\- modified file count

\- unnecessary modification

\- regression failures

\- runtime / memory where relevant

&nbsp;

\#\# Failure Classification

Initial categories:

\- planning

\- tool

\- model

\- state

\- environment

\- loop

\- timeout

\- constraint

\- unknown

&nbsp;

\#\# Output Philosophy

Preferred output:

\`\`\`text

Task Success        87%

Trajectory          72%

Tool Usage          91%

Recovery            81%

Robustness          74%

Safety              100%

Cost                $0.041/task

Latency             18.2 sec

\`\`\`

&nbsp;

A composite score may exist later as a secondary metric only.

&nbsp;

\#\# Debugging Requirement

Every failure should preserve enough data to answer:

1\. What failed?

2\. Where in the trajectory did it fail?

3\. What was the previous state?

4\. Which tool/model call caused or preceded it?

5\. Did the agent retry?

6\. Did it recover?

7\. Was the failure caused by the model, graph, tool, environment, or evaluator?

&nbsp;

\#\# Regression Evaluation

Store a baseline run set and compare:

\- task success

\- cost

\- latency

\- steps

\- tool calls

\- recovery

\- robustness

\- coding metrics

&nbsp;

\#\# Architecture Metadata

Example:

\`\`\`yaml

architecture:

&nbsp;&nbsp;framework: langgraph

&nbsp;&nbsp;pattern: planner-executor-reflection

&nbsp;&nbsp;planner: true

&nbsp;&nbsp;reflection: true

&nbsp;&nbsp;memory: false

&nbsp;&nbsp;max\_iterations: 10

\`\`\`

&nbsp;