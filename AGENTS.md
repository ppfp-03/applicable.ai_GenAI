# AGENTS.md

## Purpose

Repository-wide operating rules for coding agents. Keep this file stable and small.
Task-specific implementation context belongs in `docs/agent/tasks/*.md`.
`PROJECT_CONTEXT.md` remains the canonical source for current project truth.

## Default context loading

For a normal implementation task:

1. Read this file.
2. Read only the task brief explicitly named by the user.
3. Inspect only the repository files named by that brief, plus direct dependencies when necessary.
4. Do not read the full `PROJECT_CONTEXT.md`, starter guides, session logs, proposal, guidelines, other task briefs, or remote branches by default.
5. If the task brief declares an expected project-context or contract version, perform only a narrow authority check against the control table at the top of `PROJECT_CONTEXT.md`.
6. Read additional project context only when:
   - the version check does not match;
   - the brief explicitly names a decision/section that must be verified;
   - a material conflict or unknown blocks safe execution;
   - execution would otherwise require guessing.
7. When additional context is needed, locate only the relevant section or decision. Do not scan the whole document for background.

Do not recursively explore the repository for context. Search narrowly for symbols, imports, tests, or interfaces required by the task.

## Source authority

Use sources only for their intended role:

- `PROJECT_CONTEXT.md`: current project truth, approved decisions, contracts, constraints, open questions.
- `docs/agent/tasks/*.md`: derived execution briefs. They may repeat approved facts but never override `PROJECT_CONTEXT.md`.
- Repository code/tests: implementation evidence, not project approval.
- `SESSION_LOGS.md` and team planning documents: read only when a task explicitly requires them.

If a task brief conflicts with `PROJECT_CONTEXT.md`, stop and report the conflict. Do not reconcile it silently.

## Decision discipline

- Implement approved decisions. Do not redesign them silently.
- Do not promote a comment, prototype, branch, agent output, or existing implementation into an approved decision.
- Do not invent schema fields, business rules, ranking weights, hard constraints, provider choices, or scope.
- Keep data-shape validation separate from business logic unless the task explicitly says otherwise.
- If execution requires a new material decision, stop and report the smallest blocking question.

## Git and workspace safety

Unless the task brief explicitly overrides these rules:

- do not commit;
- do not push;
- do not merge, rebase, cherry-pick, reset, or rewrite history;
- do not switch branches;
- do not discard or overwrite unrelated user changes;
- do not modify files outside the task's allowed-file list.

Before editing, run `git status --short`.
If unexpected changes exist outside allowed files, stop.
Expected local changes inside allowed files must be preserved and reviewed, not reverted.

## Implementation workflow

Use the shortest safe loop:

`inspect -> change -> verify -> inspect diff -> report`

Before reporting completion:

- run every verification command in the task brief;
- run `git diff --check` unless the task says otherwise;
- inspect the diff for every changed allowed file;
- run `git status --short`;
- report observed results only.

Do not broaden the task because nearby code could be improved.

## Stop conditions

Stop without expanding the task when:

- required behavior is not covered by an approved decision;
- the task brief's context/contract snapshot is stale;
- a required interface conflicts with current code in a way that needs a product or architecture decision;
- completion would require changing an out-of-scope file or shared interface;
- tests reveal a failure outside the task boundary that cannot be fixed without expanding scope;
- repository state makes safe execution ambiguous.

Report the blocker, evidence, and minimum human decision needed.

## Final handoff

Keep the handoff short:

1. files changed;
2. concise change summary;
3. verification commands and observed results;
4. unresolved issues or assumptions;
5. `git status --short`.

Do not include a long project recap.
