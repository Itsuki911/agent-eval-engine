# Fixtures

A fixture defines how a benchmark starts from a known state. It must be safe to
reset repeatedly and must not require credentials, external network access, or
private data.

Each fixture directory contains `fixture.yaml`. Coding fixtures additionally
contain a `workspace/` directory and may contain a separate `verify/` directory
that the agent must not edit.

Do not put benchmark prompts or metric thresholds in a fixture.
