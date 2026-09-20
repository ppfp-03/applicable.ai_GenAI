# J-01 Job Contract

> Derived execution brief for the jointly approved job/requirement portion of shared contract `0.2.0-draft`.

## Metadata

- **Task ID:** `J-01 / JobRecord implementation + tests`
- **Status:** `ready`
- **Owner:** Marco / Group A, shared boundary with Pierpaolo
- **Expected project-context version:** `0.4.1-draft`
- **Expected contract version:** `0.2.0-draft`
- **Approval relied on:** Marco + Pierpaolo; project decision `D-034`
- **Final contract freeze:** not complete; `CandidateProfile`, `ClarificationRequest`, and shared sample-payload compatibility remain separate follow-up work

## Authority check

Before editing:

1. inspect only the control table at the top of `PROJECT_CONTEXT.md`;
2. confirm project context is `0.4.1-draft` and contract is `0.2.0-draft`;
3. if either value differs, stop and report that this brief may be stale;
4. do not read the rest of `PROJECT_CONTEXT.md` unless a material conflict/unknown appears during execution.

## Goal

Finish and verify the already-approved `RequirementFact`, `JobFacts`, `JobLocation`, and `JobRecord` contract behavior without expanding scope.

## Read

Start with only:

- `src/oi/contracts.py`
- `tests/test_contracts.py`

Inspect direct imports only if required by these files.
Do not inspect remote branches for this task.

## Allowed to change

- `src/oi/contracts.py`
- `tests/test_contracts.py`

No other files.

## Workspace expectations

- **Expected branch:** `a/j01-contracts-a01-input`
- There may be intentional uncommitted edits in `src/oi/contracts.py` containing part or all of the JobRecord block.
- Preserve correct existing approved work. Fix only deviations from this brief.
- Do not commit, push, merge, rebase, cherry-pick, switch branches, or rewrite history.

## Approved contract decisions

### Shared conventions

- Shared Pydantic models reject unknown extra fields.
- Contract version remains exactly `0.2.0-draft` for this task.
- Required strings must not use empty string as unknown.
- Timestamps are timezone-aware and normalize to UTC.
- Requirement extraction describes the job only. Candidate-relative outcomes belong to the deterministic rule engine.

### RequirementClassification

Allowed values only:

- `hard_constraint`
- `fit`
- `informational`

### RequirementModality

Allowed values only:

- `mandatory`
- `preferred`
- `optional`
- `unspecified`

### ActiveState

Allowed values only:

- `active`
- `closed`
- `unknown`

### DiscoveryKind

Allowed values only:

- `initial_snapshot`
- `later_observation`
- `synthetic_scenario`

### RequirementFact

Fields:

- `requirement_id`
- `text`
- `classification`
- `modality`
- nullable `constraint_id`
- `evidence_ids`

Rules:

- `constraint_id` is required when `classification == hard_constraint`;
- `constraint_id` must be null for `fit` and `informational`;
- do not add `met`, `conflict`, `unknown`, `not_applicable`, eligibility, or candidate-assessment fields.

### JobFacts

Fields:

- `skills: list[SupportedText]`
- `experience: list[SupportedText]`
- `education: list[SupportedText]`
- `role_family: SupportedText | None`
- `requirements: list[RequirementFact]`

Do not add semantic-extraction logic here.

### JobLocation

Fields:

- nullable `country_code`
- nullable `city`
- `evidence_ids: list[str]`

Do not infer ambiguous locations.

### JobRecord

Fields:

- `schema_version`
- `job_id`
- `source`
- `source_job_id`
- `company`
- `title`
- `url`
- `description`
- `source_documents`
- `locations`
- nullable `source_published_at`
- nullable `source_updated_at`
- nullable `deadline_at`
- `first_seen_at`
- `last_seen_at`
- `active_state`
- `discovery_kind`
- nullable `facts`
- `evidence`
- nullable `extraction`

Rules:

- `schema_version` must be exactly `0.2.0-draft`;
- `job_id == "<source>:<source_job_id>"`;
- `company`, `title`, and `url` are required non-empty strings;
- `description` is the primary `SourceDocument` and must have `kind="job"`;
- `source_documents` contains additional documents only and must not duplicate the primary description document ID;
- `first_seen_at` and `last_seen_at` are observation timestamps;
- `last_seen_at` cannot be before `first_seen_at`;
- source publication/update/deadline timestamps remain distinct nullable fields;
- incomplete records will later be quarantined outside `JobRecord`; do not invent a quarantine model here.

## In scope

- review the current Job contract code against the approved rules above;
- correct only contract-shape or validation defects;
- extend `tests/test_contracts.py` without deleting existing useful tests;
- keep all existing contract tests passing.

## Out of scope

- `CandidateProfile` or `ClarificationRequest` design/freeze;
- `RuleOutcome`, eligibility, ranking, scoring, ranking weights, or hard-rule catalogue contents;
- snapshot/quarantine implementation;
- PDF/OCR behavior;
- Kimi/LLM/provider integration;
- Streamlit/UI;
- source ingestion;
- remote-branch reconciliation;
- refactors unrelated to this contract.

## Acceptance criteria

Tests cover at least:

1. valid hard-constraint `RequirementFact`;
2. hard constraint without `constraint_id` rejected;
3. non-hard requirement with `constraint_id` rejected;
4. valid `JobRecord`;
5. incorrectly namespaced `job_id` rejected;
6. non-job primary description rejected;
7. duplicate primary description in `source_documents` rejected;
8. `last_seen_at < first_seen_at` rejected;
9. invalid `schema_version` rejected;
10. unknown extra fields rejected by shared strict-model behavior.

All pre-existing contract tests must still pass.

## Verification

Run exactly:

```bash
PYTHONPATH=src python -m compileall -q src
git diff --check
PYTHONPATH=src python -m pytest -q
git --no-pager diff -- src/oi/contracts.py tests/test_contracts.py
git status --short
```

Do not claim success unless these commands were actually run.
Do not commit or push.

## Stop conditions

Stop and report instead of expanding scope if:

- the current implementation requires changing a field not specified above;
- a test failure requires `CandidateProfile`, provider, OCR, ranking, or UI changes;
- another branch contains conflicting code that would require a merge/cherry-pick decision;
- a new cross-group schema decision is needed;
- the authority check fails.

## Required handoff

Report only:

1. files changed;
2. concise summary;
3. exact verification commands and observed results;
4. unresolved issues/assumptions;
5. `git status --short`.
