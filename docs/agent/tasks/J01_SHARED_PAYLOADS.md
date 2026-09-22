# J-01 Shared Candidate / Clarification Payloads

> Derived execution brief for the jointly approved final schema block of shared contract `0.2.0-draft`.

## Metadata

- **Task ID:** `J-01 / CandidateProfile + ClarificationRequest + shared fixtures`
- **Status:** `done`
- **Owner:** Marco / Group A, shared boundary with Pierpaolo / Group B
- **Expected project-context version:** `0.4.2-draft`
- **Expected contract version:** `0.2.0-draft`
- **Approved decision IDs / human approvals:** `D-034`, `D-035`; Marco + Pierpaolo joint sign-off, 2026-09-20
- **Final contract freeze:** complete for `0.2.0-draft` after observed implementation and fixture/reference verification on 2026-09-20
- **Observed completion evidence:** implementation commit `03a208a`; `121 passed`; 3/3 shared fixtures passed load -> Pydantic -> serialize -> reload; agreed negative/reference tests passed; post-push branch `a/j01-contracts-a01-input` clean with local and remote pointers aligned at `03a208a`.

## Authority check

Before editing:

1. inspect only the control table at the top of `PROJECT_CONTEXT.md`;
2. confirm context version `0.4.2-draft` and contract version `0.2.0-draft`;
3. if either differs, stop and report that this brief may be stale;
4. do not read the full Project Context unless a material conflict or unknown appears;
5. if needed, inspect only decisions `D-034` and `D-035` or the Candidate/Clarification section.

## Goal

Implement one shared strict Pydantic definition for the jointly approved candidate/clarification schema, add the three shared JSON fixtures, and prove their round-trip plus negative/reference behavior without inventing RuleCatalogue semantics.

## Read

Start with only:

- `src/oi/contracts.py`
- `tests/test_contracts.py`

Inspect the target fixture directory only when creating/updating the fixtures. Inspect direct imports only if required.

Do not inspect remote branches for this task.

## Allowed to change

- `src/oi/contracts.py`
- `tests/test_contracts.py`
- `tests/fixtures/contracts/v0.2.0-draft/candidate_profile.json`
- `tests/fixtures/contracts/v0.2.0-draft/clarification_request.json`
- `tests/fixtures/contracts/v0.2.0-draft/job_record.json`

No dependency files and no other source/docs files.

## Workspace expectations

- **Expected branch:** `a/j01-contracts-a01-input`
- **Expected working tree:** clean after the human documentation-prep commit that adds this brief and updates `PROJECT_CONTEXT.md`.
- Preserve all existing passing document/job/requirement contract behavior.
- Do not commit, push, merge, rebase, cherry-pick, switch branches, reset, or rewrite history.

## Approved decisions for this task

### Existing shared conventions

- `CONTRACT_VERSION` remains exactly `0.2.0-draft`.
- All shared models inherit strict extra-field rejection from `ContractModel`.
- Required identifiers/strings must not use empty string to mean unknown.
- JSON uses snake_case and `null` for missing scalar values.
- Existing `DocumentKind` remains exactly `cv | job | questionnaire | ats_metadata`; do not add a clarification document kind.
- Existing document/job/requirement models and tests remain valid.

### Shared answer enums

Define closed values needed by this block:

- `AnswerState`: `known | unknown`
- `AnswerType`: `boolean | single_choice | multi_choice | text | date | integer`
- `ClarificationPriority`: `high | medium | low`

Do not add answer types or priority levels.

### CandidatePreferences

Fields:

- `allowed_country_codes: list[str] | None`
- `preferred_country_codes: list[str]`
- `preferred_role_families: list[str]`
- `preferred_industries: list[str]`

Rules:

- country codes are valid ISO 3166-1 alpha-2 values in uppercase;
- duplicate country codes are rejected;
- `allowed_country_codes=None` means no explicit restriction declared;
- when non-null, `allowed_country_codes` must be non-empty, so `[]` is invalid;
- if `allowed_country_codes` is present, every preferred country must be inside it;
- do not invent semantics for empty preferred-role/industry lists beyond ordinary empty arrays.

Implement ISO alpha-2 validity without adding a new runtime dependency.

### WorkAuthorizationDeclaration

Fields:

- `country_code`
- `authorized_to_work: bool | None`
- `requires_sponsorship: bool | None`
- `evidence_ids: list[str]`

Rules:

- `country_code` follows the same ISO/uppercase rule;
- work-authorization declarations must be unique by country inside `UserDeclarations`;
- `authorized_to_work` and `requires_sponsorship` are independently nullable;
- never infer one from the other.

### UserDeclarations

Fields:

- `additional_citizenships: list[str]`
- `work_authorizations: list[WorkAuthorizationDeclaration]`

Rules:

- citizenship values use the same ISO/uppercase/no-duplicate country-code rule;
- citizenship, work authorization and sponsorship remain separate facts;
- do not derive work authorization from citizenship.

### EligibilityAnswer

Fields:

- `constraint_id`
- `answer_key`
- `state: AnswerState`
- `answer_type: AnswerType`
- `value`
- `evidence_ids: list[str]`
- `source_document_id`

`value` is closed to the logical types represented by:

- boolean -> `bool`
- single_choice -> `str`
- multi_choice -> `list[str]`
- text -> `str`
- date -> `date` in the Pydantic model and ISO `YYYY-MM-DD` in JSON
- integer -> `int`
- plus `null` only when state is unknown

Rules:

- `constraint_id`, `answer_key`, and `source_document_id` are non-empty;
- `state=unknown` requires `value=None`;
- `state=known` requires a non-null value;
- answer type and value type must match strictly;
- specifically reject permissive bool/int crossover and analogous unintended coercions;
- the outer key of `CandidateProfile.eligibility_answers` must equal every contained answer's `constraint_id`;
- `answer_key` must be structurally valid/non-empty, but this contract MUST NOT validate membership in a `constraint_id -> answer_key` catalogue;
- membership belongs to the future deterministic `RuleCatalogue` and is out of scope.

### CandidateProvenance

Fields:

- `questionnaire_document_ids: list[str]`
- `clarification_document_ids: list[str]`
- `documents: dict[str, SourceDocument]`
- `evidence: list[EvidenceRef]`
- `extraction: ExtractionReceipt`

Rules:

- document-registry keys must identify the contained document;
- `cv_document_id` on the profile must resolve in `documents` and point to `kind="cv"`;
- questionnaire and clarification IDs must resolve in `documents` and use `kind="questionnaire"`;
- every candidate-side `evidence_id` reference must resolve in `provenance.evidence`;
- every `EvidenceRef.document_id` must resolve in `provenance.documents`;
- every `EligibilityAnswer.source_document_id` must resolve in `provenance.documents`;
- when an EligibilityAnswer has evidence IDs, each referenced EvidenceRef must belong to the same document as `source_document_id`.

Do not change `SourceDocument` or `EvidenceRef` fields to implement these checks.

### CandidateProfile

Fields exactly:

- `schema_version`
- `candidate_id`
- `cv_document_id`
- `skills: list[SupportedText]`
- `education: list[SupportedText]`
- `experience: list[SupportedText]`
- `preferences: CandidatePreferences`
- `declarations: UserDeclarations`
- `eligibility_answers: dict[str, list[EligibilityAnswer]]`
- `provenance: CandidateProvenance`

Rules:

- `schema_version` must be exactly `0.2.0-draft`;
- `candidate_id` and `cv_document_id` are non-empty;
- all evidence references in semantic profile fields, work-authorization declarations and eligibility answers must satisfy the provenance-resolution rules above;
- specialized work-authorization/sponsorship facts stay in `declarations.work_authorizations`; do not duplicate or derive them in `eligibility_answers`.

### CandidateFieldPath

`field_path` is not an arbitrary string. Accept only these destination families:

- `preferences.allowed_country_codes`
- `preferences.preferred_country_codes`
- `preferences.preferred_role_families`
- `preferences.preferred_industries`
- `declarations.additional_citizenships`
- `declarations.work_authorizations.<COUNTRY>.authorized_to_work`
- `declarations.work_authorizations.<COUNTRY>.requires_sponsorship`
- `eligibility_answers.<CONSTRAINT_ID>.<ANSWER_KEY>`

Rules:

- `<COUNTRY>` follows the approved uppercase ISO alpha-2 rule;
- `<CONSTRAINT_ID>` and `<ANSWER_KEY>` must be non-empty path tokens;
- for the eligibility family, validate path structure only;
- MUST NOT validate `<ANSWER_KEY>` membership for a specific `<CONSTRAINT_ID>`.

### ClarificationRequest

Fields exactly:

- `question_id`
- `field_path: CandidateFieldPath | None`
- `constraint_id: str | None`
- `question`
- `answer_type: AnswerType`
- `allowed_choices: list[str] | None`
- `reason`
- `job_ids: list[str]`
- `evidence_ids: list[str]`
- `priority: ClarificationPriority`

Rules:

- required strings are non-empty;
- at least one of `field_path` or `constraint_id` must be present;
- `allowed_choices` is required and non-empty for `single_choice` and `multi_choice`;
- `allowed_choices` must be `None` for `boolean`, `text`, `date`, and `integer`;
- do not add a generic `validation` object;
- if `field_path` has form `eligibility_answers.<CONSTRAINT_ID>.<ANSWER_KEY>` and `constraint_id` is also present, the IDs must match;
- do not invent a new candidate destination or hard rule.

### Shared fixtures

Create exactly:

```text
tests/fixtures/contracts/v0.2.0-draft/
├── candidate_profile.json
├── clarification_request.json
└── job_record.json
```

Fixture rules:

- all fixture data is synthetic;
- `candidate_profile.json` is self-contained for candidate provenance: its document registry, evidence registry and referenced IDs must resolve;
- `clarification_request.json` uses only an approved CandidateFieldPath family;
- `job_record.json` is a representative valid `JobRecord` using the already-approved job schema;
- fixture constraint IDs/answer keys demonstrate contract shape only and MUST NOT be treated as freezing RuleCatalogue membership or rule semantics.

## In scope

- implement the approved candidate/clarification models and validators in the shared contracts module;
- create the three shared JSON fixtures;
- extend `tests/test_contracts.py` without deleting useful existing tests;
- test fixture load -> Pydantic validation -> serialize -> reload;
- test approved semantic/reference invariants and negative cases;
- preserve all 17 previously passing tests.

## Out of scope

- final hard-constraint catalogue contents or semantics;
- `constraint_id -> answer_key` membership rules;
- `RuleOutcome`, eligibility engine, ranking, scoring or ranking weights;
- applying clarification answers/recomputation behavior;
- LLM/provider extraction logic;
- UI/Streamlit;
- ingestion, snapshots, PDF/OCR changes;
- new `DocumentKind` values;
- dependency changes;
- remote-branch reconciliation;
- unrelated refactors.

## Acceptance criteria

At minimum, automated tests prove all of the following:

1. `candidate_profile.json` loads as `CandidateProfile`, serializes, reloads, and preserves equivalent model data.
2. `clarification_request.json` loads as `ClarificationRequest`, serializes, reloads, and preserves equivalent model data.
3. `job_record.json` loads as `JobRecord`, serializes, reloads, and preserves equivalent model data.
4. `CandidateProfile.schema_version` rejects values other than `0.2.0-draft`.
5. missing/non-resolving candidate evidence IDs are rejected.
6. missing/non-resolving candidate document IDs are rejected.
7. a missing CV document or a `cv_document_id` resolving to non-`cv` kind is rejected.
8. questionnaire/clarification document IDs that do not resolve, or resolve to an incompatible kind, are rejected.
9. `allowed_country_codes=None` is valid, a non-empty valid list is valid, and `allowed_country_codes=[]` is rejected.
10. preferred countries outside an explicit allowed-country perimeter are rejected.
11. invalid, lowercase, or duplicate country codes are rejected where country-code collections are used.
12. duplicate work-authorization declarations for the same country are rejected; independently-null authorization/sponsorship fields remain valid.
13. an outer eligibility dictionary key that differs from a contained answer's `constraint_id` is rejected.
14. `state=unknown` with non-null value is rejected and `state=known` with null value is rejected.
15. answer-type/value mismatches are rejected, including bool supplied for integer and integer supplied for boolean.
16. an EligibilityAnswer with evidence from a document different from its `source_document_id` is rejected.
17. empty `answer_key` is rejected, while no RuleCatalogue membership check is introduced.
18. every approved CandidateFieldPath family has at least one valid test; unsupported path families are rejected.
19. an eligibility field path whose constraint component conflicts with a present `ClarificationRequest.constraint_id` is rejected.
20. a clarification with both `field_path=None` and `constraint_id=None` is rejected.
21. single/multi-choice clarification without non-empty `allowed_choices` is rejected.
22. `allowed_choices` on non-choice answer types is rejected.
23. priority outside `high | medium | low` is rejected.
24. unknown extra fields remain rejected on new models.
25. all pre-existing document/job/requirement contract tests still pass.
26. tests do not assert or implement `constraint_id -> answer_key` membership.

## Verification

Run exactly:

```bash
PYTHONPATH=src .venv/bin/python -m compileall -q src
git diff --check
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from oi.contracts import CandidateProfile, ClarificationRequest, JobRecord

root = Path("tests/fixtures/contracts/v0.2.0-draft")
for filename, model in [
    ("candidate_profile.json", CandidateProfile),
    ("clarification_request.json", ClarificationRequest),
    ("job_record.json", JobRecord),
]:
    payload = json.loads((root / filename).read_text())
    parsed = model.model_validate(payload)
    reparsed = model.model_validate_json(parsed.model_dump_json())
    assert reparsed == parsed
    print(f"round-trip ok: {filename}")
PY
git --no-pager diff -- src/oi/contracts.py tests/test_contracts.py tests/fixtures/contracts/v0.2.0-draft/
git status --short
```

Do not claim success unless every command was actually run and its observed result is reported.

## Stop conditions

In addition to `AGENTS.md`, stop and report if:

- implementing ISO country validation appears to require a new dependency rather than a bounded local implementation;
- implementation would require changing the approved `SourceDocument`, `EvidenceRef`, JobRecord or RequirementFact field shapes;
- a test requires deciding actual `constraint_id -> answer_key` membership;
- a CandidateFieldPath family beyond the approved list appears necessary;
- a new answer type, priority level, candidate field, validation dictionary or hard-rule semantic is needed;
- any required reference invariant is ambiguous enough that implementation would require guessing;
- authority versions do not match this brief.

## Required handoff

Report only:

1. files changed;
2. concise change summary;
3. exact verification commands and observed results;
4. unresolved issues/assumptions;
5. `git status --short`.

Do not commit or push.
