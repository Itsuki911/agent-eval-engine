# Benchmarks

Each YAML file is a task contract. It states what the agent must achieve and
how success is evaluated; it does not embed mutable fixture state.

## Naming

- `GEN-<AREA>-NNN`: generic tool, recovery, robustness, or safety task.
- `COD-<AREA>-NNN`: coding task.
- `TERM-<AREA>-NNN`: terminal-specific task.
- Future: `WEB-<AREA>-NNN` and `GUI-<AREA>-NNN`.

Use one immutable ID per task. Retire an invalid task rather than reusing its
ID. Increment a fixture version when its initial state changes materially.

## Authoring checklist

1. Reference a fixture by `family/id-vN`.
2. Define observable success conditions and failure conditions.
3. Use action-sequence assertions only when order itself is the requirement.
4. Set an explicit step, time, and cost limit when relevant.
5. Add the task to the family's `index.yaml`.
