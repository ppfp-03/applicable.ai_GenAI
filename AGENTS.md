# AGENTS.md

## Purpose

Repository-wide operating rules for coding agents. Keep this file stable and small.
Task-specific implementation context belongs in `docs/agent/tasks/*.md`.
The repository-root `PROJECT_CONTEXT.md` is the canonical editable source for current project truth. Any ChatGPT Project Source copy is a mirror and does not override the repository copy when versions differ.

## Default context loading

For a normal implementation task:

1. Read this file.
2. Read only the task brief explicitly named by the user.
3. Inspect only the repository files named by that brief, plus direct dependencies when necessary.
4. Do not read the full `PROJECT_CONTEXT.md`, starter guides, session logs, proposal, guidelines, other task briefs, or remote branches by default.
5. If the task brief declares an expected project-context or contract version, perform only a narrow authority check against the control table at the top of the repository-root `PROJECT_CONTEXT.md`.
6. Read additional project context only when:
   - the version check does not match;
   - the brief explicitly names a decision/section that must be verified;
   - a material conflict or unknown blocks safe execution;
   - execution would otherwise require guessing.
7. When additional context is needed, locate only the relevant section or decision. Do not scan the whole document for background.

Do not recursively explore the repository for context. Search narrowly for symbols, imports, tests, or interfaces required by the task.

## Source authority

Use sources only for their intended role:

- repository-root `PROJECT_CONTEXT.md`: canonical current project truth, approved decisions, contracts, constraints, open questions;
- `docs/agent/tasks/*.md`: derived execution briefs. They may repeat approved facts but never override `PROJECT_CONTEXT.md`;
- repository code/tests: implementation evidence, not project approval;
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

- do not stage files (`git add`);
- do not commit;
- do not push;
- do not merge, rebase, cherry-pick, reset, or rewrite history;
- do not discard or overwrite unrelated user changes;
- do not modify files outside the task's allowed-file list.

### Agent-first file editing

When a task authorizes file modification and the agent has working-tree access, the agent makes the allowed edits itself and runs the required verification.

- Do not hand the human shell heredocs, `cat > file`, manual editor steps, or equivalent as a substitute for an edit the agent can make itself.
- Limit human-facing terminal instructions to control-plane Git actions, environment/access/credential steps, or genuine tool limitations.
- Editing authorization is not Git authorization. It does not permit `git add`, commit, push, merge, rebase, reset, or history rewriting; the restrictions above still apply.
- If a task explicitly authorizes named Git actions, perform only those named actions and report exact results.
- For merge/conflict tasks, edit the allowed conflict files and run verification. Staging or continuing the merge still requires explicit authorization unless the task says otherwise.
- If the required tool or repository access is unavailable, report that limitation first, then give the minimum safe manual fallback.

### Task branches

For repository coding work, use a new branch for each new independently reviewable task or implementation phase.

- Create the new branch only at a task boundary, after the previous task is committed or otherwise explicitly preserved and the working tree is clean.
- Create the branch from the branch or commit that contains the dependencies required by the new task. Do not assume every task must branch from `main`.
- Small fixes, verification changes, or follow-ups that remain within the same task may stay on the current task branch.
- Do not stack a materially different task on an existing task branch merely for convenience.
- Branch creation and switching are permitted for this task-boundary workflow. Do not switch branches mid-task when local changes are unresolved unless the user explicitly directs it.
- Creating a branch does not authorize staging, committing, pushing, merging, rebasing, cherry-picking, resetting, or rewriting history. Those actions still require the permissions stated above or an explicit task instruction.

Before editing, run `git status --short` and interpret both columns, not only the filenames.
If unexpected changes exist outside allowed files, stop.
Expected local changes inside allowed files must be preserved and reviewed, not reverted.
If status shows split staged/unstaged state such as `MM`, `AM`, or similar, report it explicitly. Do not describe the workspace as final-review-ready until the human resolves or intentionally accepts that split state.

Remember:

- ordinary `git diff` omits staged changes;
- `git diff --cached` omits unstaged changes;
- `git diff HEAD -- <paths>` shows tracked staged + unstaged changes relative to `HEAD`;
- untracked files are omitted by all normal `git diff` forms and must be inspected explicitly.

Do not stage files merely to make untracked content appear in a diff.

## Implementation workflow

Use the shortest safe loop:

`inspect -> change -> verify -> inspect complete change set -> report`

Before reporting completion:

- run every verification command in the task brief;
- run `git diff --check` unless the task says otherwise;
- inspect tracked allowed-file changes against `HEAD`, not only the unstaged diff;
- inspect every new untracked allowed file explicitly, for example by reading it or using `git diff --no-index -- /dev/null <file> || true`;
- run `git status --short` and identify staged, unstaged, split-state, and untracked files accurately;
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

1. files changed, including whether each is staged, unstaged, split-state, or untracked when relevant;
2. concise change summary;
3. verification commands and observed results;
4. unresolved issues or assumptions;
5. exact `git status --short` output.

If new files exist, confirm they were inspected even though normal `git diff` does not show them.
Do not include a long project recap.
