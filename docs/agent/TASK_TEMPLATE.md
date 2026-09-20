# Task Brief Template

> Derived execution packet. It may repeat approved facts needed for implementation, but it does not replace the repository-root `PROJECT_CONTEXT.md`.

## Metadata

- **Task ID:** `<ID>`
- **Status:** `ready | blocked | done`
- **Owner:** `<name/team>`
- **Expected project-context version:** `<version or N/A>`
- **Expected contract/config version:** `<version or N/A>`
- **Approved decision IDs / human approvals:** `<IDs/names or N/A>`

## Authority check

Before editing:

1. read only the control table at the top of the repository-root `PROJECT_CONTEXT.md` if this brief declares an expected context/contract version;
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
- Expected intentional tracked changes: `<paths or none>`
- Expected staged/index state: `<none | exact expected paths/state>`
- Expected untracked files/directories: `<none | exact expected paths>`
- Preserve approved existing work; do not revert it just to simplify the task.
- Do not stage files unless this brief explicitly authorizes staging.

If actual `git status --short` differs materially from these expectations, stop before editing and report the mismatch.

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

## Final review state

Before handoff:

1. run `git status --short` and interpret staged vs unstaged columns;
2. inspect all tracked allowed-file changes relative to `HEAD` using `git diff HEAD -- <paths>` or an equivalent command that includes both staged and unstaged tracked changes;
3. inspect every new untracked allowed file explicitly; normal `git diff` does not include untracked files;
4. if the workspace has split staged/unstaged state such as `MM` or `AM`, report it explicitly and do not describe the change set as final-review-ready;
5. do not stage files solely for review unless this brief explicitly authorizes staging.

## Stop conditions

In addition to `AGENTS.md`, stop if:

- `<task-specific blocker>`

## Required handoff

Report only:

1. files changed and their relevant Git state;
2. concise change summary;
3. commands run and observed results;
4. unresolved issue/assumption;
5. exact `git status --short` output.

For untracked files, state how they were inspected.
Do not commit, push, or stage unless this brief explicitly authorizes it.
