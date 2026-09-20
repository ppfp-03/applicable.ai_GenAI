# Task Brief Template

> Derived execution packet. It may repeat approved facts needed for implementation, but it does not replace `PROJECT_CONTEXT.md`.

## Metadata

- **Task ID:** `<ID>`
- **Status:** `ready | blocked | done`
- **Owner:** `<name/team>`
- **Expected project-context version:** `<version or N/A>`
- **Expected contract/config version:** `<version or N/A>`
- **Approved decision IDs / human approvals:** `<IDs/names or N/A>`

## Authority check

Before editing:

1. read only the control table at the top of `PROJECT_CONTEXT.md` if this brief declares an expected context/contract version;
2. if versions match, use this brief as the working packet and do not read the full context;
3. if versions do not match, stop and report that the brief may be stale;
4. inspect a named decision/section in `PROJECT_CONTEXT.md` only when this brief explicitly requires it or a material conflict blocks execution.

## Goal

One observable outcome.

## Read

Only these files initially:

- `<path>`

Direct imports/dependencies may be inspected only as needed.

## Allowed to change

- `<path>`

Everything else is read-only/out of scope.

## Workspace expectations

- Expected branch: `<branch or N/A>`
- Expected intentional local changes: `<paths or none>`
- Preserve approved existing work; do not revert it just to simplify the task.

## Approved decisions for this task

Only the decisions necessary to implement this task. Keep them concrete and serializable where relevant.

## In scope

- `<item>`

## Out of scope

- `<item>`

## Acceptance criteria

- `<observable behavior>`

## Verification

Run exactly:

```bash
<commands>
```

## Stop conditions

In addition to `AGENTS.md`, stop if:

- `<task-specific blocker>`

## Required handoff

Report only:

1. files changed;
2. concise change summary;
3. commands run and observed results;
4. unresolved issue/assumption;
5. `git status --short`.

Do not commit or push unless this brief explicitly authorizes it.
