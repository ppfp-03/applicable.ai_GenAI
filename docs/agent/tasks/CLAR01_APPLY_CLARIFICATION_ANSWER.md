# CLAR-01 Clarification Engine v1 - Apply One Structured Answer

> Derived execution brief. It may repeat approved facts needed for implementation, but it does not replace the repository-root `PROJECT_CONTEXT.md`.
>
> CLAR-01 covers only **applying a structured answer to an existing `ClarificationRequest`**. It is not the complete Clarification Engine: gap detection, request generation, question wording, the RuleCatalogue and downstream recomputation are later work.

## Metadata

- **Task ID:** `CLAR-01 / Clarification Engine v1 - apply a structured answer to an existing ClarificationRequest`
- **Status:** `done`
- **Observed completion evidence (2026-09-25, branch `feature/clarification-engine-tommaso`, base `0e27535`, uncommitted working tree at the time of verification):**
  - focused clarification tests (`tests/test_clarification.py`): `32 passed`;
  - full pytest suite: `306 passed`;
  - `compileall -q src`: exit 0;
  - `npm test` wrapper: `306 passed`;
  - `git diff --check`: clean.

  The implementation was approved by the human owner (Tommaso) after final review. It is ready for PR review. It has not been merged or integrated into `main`, the UI or any downstream engine.
- **Owner:** Tommaso (Clarification Engine)
- **Expected project-context version:** `0.4.9-draft`
- **Expected contract version:** `0.2.0-draft` (candidate/clarification core frozen)
- **Approved decision IDs / human approvals:** `D-019`, `D-020`, `D-035`, `D-040`; `PROJECT_CONTEXT.md` sections 4 ("What remains deterministic"), 6C, 6D and 7 ("Clarification behavior"). Task-level decisions P-1 to P-6 were approved by the human owner (Tommaso) on 2026-09-25: P-1, P-2 and P-4 as proposed, and P-3, P-5 and P-6 as modified below.
- **Scope note:** these approvals govern this task's local behavior only. They do not approve new contract fields, rule semantics, constraint IDs, answer keys or RuleCatalogue content.

## Authority check

Before editing:

1. read only the control table at the top of the repository-root `PROJECT_CONTEXT.md`;
2. confirm context version `0.4.9-draft` and contract version `0.2.0-draft` (core frozen);
3. if either differs, stop and report that this brief may be stale;
4. do not read the full Project Context. If a material conflict appears, inspect only `D-035`, `D-040` or sections 6C/6D.

## Goal

Given an existing, valid `CandidateProfile`, an existing, valid `ClarificationRequest` and the user's structured answer, deterministically return a new, fully revalidated `CandidateProfile`. The answer is the current `EligibilityAnswer` at its canonical `eligibility_answers` destination, backed by resolvable clarification provenance.

The only destination supported in CLAR-01 is the approved boolean case `eligibility_answers.HC_MIN_EXPERIENCE.has_corporate_finance_experience`.

## Read

Only these files initially:

- `src/oi/contracts.py` (read-only)
- `src/oi/intelligence/clarification.py`
- `tests/test_contracts.py` (read-only, for existing fixture/test helper conventions)
- `tests/fixtures/contracts/v0.2.0-draft/candidate_profile.json` (read-only)
- `tests/fixtures/contracts/v0.2.0-draft/clarification_request.json` (read-only)

Direct imports/dependencies may be inspected only as needed.

## Allowed to change

- `src/oi/intelligence/clarification.py`
- `tests/test_clarification.py` (new file; the repository keeps tests flat under `tests/`)
- `docs/agent/tasks/CLAR01_APPLY_CLARIFICATION_ANSWER.md`

Everything else is read-only and out of scope. In particular, do not change `src/oi/contracts.py`, the shared fixtures, `config/` (including `config/hard_constraints.json`), `core/`, `views/`, `ui/`, `app.py`, `src/oi/intelligence/{eligibility,ranking,extraction,explanations}.py`, `src/oi/providers/`, `src/oi/io/`, dependency files, existing tests, or `PROJECT_CONTEXT.md`.

## Workspace expectations

- Expected branch: `feature/clarification-engine-tommaso`
- Expected base commit: `0e27535`, or a descendant that only adds this brief
- Expected intentional tracked changes before implementation: none
- Expected staged/index state: none
- Expected untracked files: at most this brief, if the human has not committed it yet
- Do not stage, commit, push, merge, rebase, reset, or create/switch branches.

If the actual `git status --short` differs materially from these expectations, stop before editing and report the mismatch.

## Project decisions this task relies on

These facts come from `PROJECT_CONTEXT.md` and are restated here only for execution:

- Applying candidate declarations, corrections and structured answers is deterministic and does not call an LLM (section 4; D-019).
- A clarification answer becomes a documented user input, updates the structured profile and has provenance (sections 6A, 7; D-020).
- A clarification answer is a `SourceDocument` with `kind="questionnaire"`. It is distinguished only by being listed in `provenance.clarification_document_ids`. No new `DocumentKind` exists or may be added (section 6C; D-035).
- `EligibilityAnswer`:
  - fields are `constraint_id`, `answer_key`, `state`, `answer_type`, `value`, `evidence_ids`, `source_document_id`;
  - `state=unknown` requires `value=null`, and `state=known` requires a non-null value that matches `answer_type` strictly (section 6C).
- The outer `eligibility_answers` key equals each contained answer's `constraint_id`. The answer's evidence must belong to its `source_document_id`. Every reference must resolve inside `provenance` (section 6C).
- `eligibility_answers.<CONSTRAINT_ID>.<ANSWER_KEY>` is structurally validated by the contract. Answer-key membership belongs to the RuleCatalogue (section 6D; D-040).
- Approved answer key (D-040): constraint `HC_MIN_EXPERIENCE`, answer key `has_corporate_finance_experience`, boolean.
- Work authorization and sponsorship are never written into `eligibility_answers` (section 6C).

## Approved CLAR-01 behavior (P-1 to P-6)

- **P-1 - Public API (intelligence-internal; not a shared contract):**

  ```python
  class ClarificationAnswerError(ValueError): ...

  def apply_clarification_answer(
      candidate: CandidateProfile,
      request: ClarificationRequest,
      answer: bool | None,
  ) -> CandidateProfile: ...
  ```

  Every unsupported request or invalid answer raises `ClarificationAnswerError`. The input `candidate` is never mutated. The result is a new, fully validated `CandidateProfile`.

- **P-2 - Supported destination:** only `eligibility_answers.HC_MIN_EXPERIENCE.has_corporate_finance_experience`, with answer type `boolean`. It is held in a small local allowlist in `clarification.py`. The allowlist is **not** a RuleCatalogue and must not be described as one. `config/hard_constraints.json` is not modified.

- **P-3 - Clarification document:**
  - `text` is exactly `"Question: <request.question>\nAnswer: <canonical answer text>"`, where the canonical answer text is `True -> "Yes"`, `False -> "No"`, `None -> "Unknown"`.
  - `kind = "questionnaire"`, `source_ref = "clarification_answer"`, `content_hash` = SHA-256 hex digest of the UTF-8 encoding of the exact stored `text`.
  - `document_id = "clarification:<question_id>:<first 16 hex characters of content_hash>:<occurrence>"`. It is content-aware and deterministic.
  - **Every successful call is a new provenance event** (clarified in human review, 2026-09-25). Each successful application adds a new `SourceDocument`, a new `EvidenceRef`, and the new document ID appended to `clarification_document_ids`. This holds even when the same question receives identical answer content again (for example True -> False -> True). A document from an earlier identical answer is never reused.
  - `<occurrence>` is the smallest integer `n >= 1` for which neither `clarification:<question_id>:<hash-prefix>:<n>` is registered in `provenance.documents` nor `ev-<that document_id>` is registered in `provenance.evidence`. It is derived only from the existing candidate provenance, with no randomness, no wall-clock time and no new contract field.

- **P-4 - Evidence:**
  - one candidate-side `EvidenceRef` with `evidence_id = "ev-<document_id>"`, `document_id` set to the clarification document, `quote` equal to the full document `text`, and `field_path = request.field_path`;
  - the request's own `evidence_ids` are job-side evidence and are not copied into candidate provenance.

- **P-5 - Upsert by `constraint_id` + `answer_key`:**
  - The new answer becomes the single current `EligibilityAnswer` for that key: every existing answer with the same `answer_key` under the same `constraint_id` is replaced, at the position of the first one, and other answer keys are untouched.
  - Earlier provenance documents and evidence stay in `CandidateProvenance`, and the new document and evidence are added.
  - The current answer always references the provenance created by the current invocation.

- **P-6 - Answer values:**

  | Answer | Resulting `EligibilityAnswer` |
  |---|---|
  | `True` | `state="known"`, `answer_type="boolean"`, `value=True` |
  | `False` | `state="known"`, `answer_type="boolean"`, `value=False` |
  | `None` | `state="unknown"`, `answer_type="boolean"`, `value=None` (the contract's existing unknown representation) |

  Everything else is rejected without coercion: `1`, `0`, `"yes"`, `"no"`, `"true"`, `"false"`, lists, dicts and other values. The check is `answer is None or type(answer) is bool`.

## Local implementation choices

These follow from the approved behavior but are choices made in this task. A reviewer should check them.

- **16-hex-character hash prefix** (64 bits) in the document ID.
- **Occurrence probing** starts at 1. The engine probes candidate IDs in provenance instead of parsing existing IDs, so a `question_id` that contains `:` cannot confuse the count. Probing also guarantees the new document and evidence IDs are unused, so an existing entry is never overwritten.
- **Validation order:**
  1. `field_path` is present;
  2. it has the eligibility-answer family shape;
  3. it agrees with `request.constraint_id` (re-checked even though the contract enforces it);
  4. it is on the allowlist;
  5. `request.answer_type` matches;
  6. the answer value is valid.
- **Revalidation:** the result is built from `candidate.model_dump()` plus new `model_dump()` payloads and passed through `CandidateProfile.model_validate`. It never uses `model_copy` without validation. A contract `ValidationError` propagates unchanged.

## Future work (not CLAR-01)

- The **RuleCatalogue**, with `constraint_id -> answer_key` membership and answer types, will replace the local allowlist. New answer keys need explicit approval (D-040).
- **Gap detection and `build_clarification_requests`**, question wording (LLM), and prioritisation.
- **Other destinations:** `preferences.*`, `declarations.*` and other `eligibility_answers` keys.
- **Choice answer types** with `allowed_choices` validation.
- **Downstream recomputation** of eligibility and ranking after an answer, once the canonical engines exist.
- **UI / Streamlit integration.**

## In scope

- `ClarificationAnswerError` and `apply_clarification_answer` in `src/oi/intelligence/clarification.py`, replacing the placeholder.
- `tests/test_clarification.py`.

## Out of scope

- Everything listed under "Future work".
- LLM or provider calls.
- Integration with `core/store.py` or `views/question.py`.
- New constraints, answer keys or contract changes.
- Fixing unrelated code, for example contract mismatches in `extraction.py` or `model_client.py`.

## Acceptance criteria

Automated tests in `tests/test_clarification.py` prove all of the following. They use the shared `candidate_profile.json` fixture as the base profile, loaded read-only, and build requests in code.

1. `True` gives the current answer `state="known"`, `value is True`.
2. `False` gives the current answer `state="known"`, `value is False`.
3. `None` gives the current answer `state="unknown"`, `value is None`.
4. The answer is written at `eligibility_answers["HC_MIN_EXPERIENCE"]` with `constraint_id="HC_MIN_EXPERIENCE"`, `answer_key="has_corporate_finance_experience"`, `answer_type="boolean"`.
5. **Provenance:**
   - the new document resolves, with `kind="questionnaire"` and `source_ref="clarification_answer"`;
   - its text is exact and `content_hash` equals the SHA-256 of that text;
   - the document ID follows the P-3 format, with occurrence `1` on first use;
   - the new evidence resolves to that document and its quote occurs in the document text;
   - `source_document_id` resolves;
   - `clarification_document_ids` contains the new ID and not `questionnaire_document_ids`;
   - no job-side evidence IDs are copied.
6. `skills`, `education`, `experience`, `preferences`, `declarations`, other `eligibility_answers`, the extraction receipt and all pre-existing provenance entries are unchanged.
7. `1`, `0`, `"yes"`, `"no"`, `"true"`, `"false"`, `[True]` and `{"value": True}` raise `ClarificationAnswerError`.
8. These unsupported destinations raise `ClarificationAnswerError`:
   - a `preferences.*` path;
   - a `declarations.*` path;
   - another `HC_MIN_EXPERIENCE` key;
   - another constraint;
   - a request with only `constraint_id`.
9. A constraint/destination mismatch is rejected: the contract rejects it at construction, and the engine still rejects a request built with `model_construct` that bypasses the contract. A non-boolean `answer_type` for the supported path is also rejected.
10. **Upsert:** starting from an existing `False` answer and applying `True` leaves exactly one answer for the key, with value `True`. The old document and evidence remain, and the new ones are present.
11. The input profile is unchanged after a successful application.
12. The result round-trips through `model_dump_json` -> `CandidateProfile.model_validate_json` unchanged.
13. **Repeated identical answers (True -> False -> True):**
    - exactly one active answer remains, with final value `True`;
    - the three applications produce three distinct documents and three distinct evidence records;
    - the two `True` documents share the hash prefix and differ only by occurrence (`:1`, `:2`);
    - the final answer references the third application's document and evidence;
    - all three documents are present, and all three evidence records resolve to their document;
    - `clarification_document_ids` lists them in application order;
    - every earlier profile instance is unchanged.
14. The full suite still passes; the baseline on `0e27535` is `274 passed`.

## Verification

Run exactly:

```bash
.venv/bin/python -m compileall -q src
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_clarification.py
.venv/bin/python -m pytest -q -p no:cacheprovider
npm test -- -q -p no:cacheprovider
git diff --check
git --no-pager diff HEAD --stat
git --no-pager diff --cached --stat
git --no-pager diff HEAD -- src/oi/intelligence/clarification.py
git --no-pager diff --no-index --check -- /dev/null tests/test_clarification.py || true
git --no-pager diff --no-index --check -- /dev/null docs/agent/tasks/CLAR01_APPLY_CLARIFICATION_ANSWER.md || true
git status --short
```

`npm test` is the repository's own wrapper around pytest (`scripts/test.cjs`). It is not a frontend check.

## Final review state

Before handoff:

1. run `git status --short` and interpret the staged and unstaged columns;
2. inspect tracked allowed-file changes relative to `HEAD` with `git diff HEAD -- <paths>`;
3. inspect every new untracked allowed file explicitly;
4. report any split staged/unstaged state such as `MM` or `AM` explicitly;
5. do not stage files for review.

## Stop conditions

In addition to `AGENTS.md`, stop and report if:

- implementation would require changing `src/oi/contracts.py`, a shared fixture or `config/`;
- a second constraint ID or answer key appears necessary;
- the approved behavior cannot be represented with the frozen `EligibilityAnswer` / `SourceDocument` / `EvidenceRef` / `CandidateProvenance` shapes;
- the resulting profile fails contract validation for a reason that is not a defect in this task's code;
- authority versions do not match this brief.

## Required handoff

Report only:

1. files changed and their Git state (tracked, untracked, staged);
2. concise change summary;
3. commands run and observed results;
4. unresolved issues or assumptions;
5. exact `git status --short` output.

For untracked files, state how they were inspected. Do not commit, push or stage.
