# A-01 Input Path - JobSnapshot loader + PDF text input

> Derived execution packet. It repeats only the decisions needed for this task and does not replace `PROJECT_CONTEXT.md`.

## Metadata

- **Task ID:** `A-01 / JobSnapshot loader + PDF text input`
- **Status:** `ready`
- **Owner:** Marco / Group A; shared `JobSnapshot` boundary consumed by Pierpaolo / Group B
- **Expected project-context version:** `0.4.5-draft`
- **Current frozen core contract version:** `0.2.0-draft`
- **Approved shared extension:** `JobSnapshot.schema_version = "0.2.1-draft"`, backward-compatible with embedded `0.2.0-draft` `JobRecord` payloads
- **Approved decision IDs / human approvals:** `D-006`, `D-026`, `D-036`, `D-037`; Marco + Pierpaolo joint sign-off, 2026-09-20

## Activation condition

This task is ready because `PROJECT_CONTEXT.md` records the joint Marco + Pierpaolo approval of the shared `JobSnapshot 0.2.1-draft` extension under D-006/D-037.

Do not redesign the approved schema during implementation. If the authority check does not match, stop and report the mismatch.

## Authority check

Before editing:

1. read the control table at the top of `PROJECT_CONTEXT.md`;
2. confirm context version `0.4.5-draft` and that D-037 records `JobSnapshot 0.2.1-draft` as jointly approved;
3. confirm the existing `0.2.0-draft` core payload models remain frozen and unchanged;
4. if any of those facts do not match, stop and report that the brief is stale;
5. otherwise use this brief as the working packet and do not scan the full project context.

## Goal

Provide one A-owned, tested input path that:

1. loads a UTF-8 JSON snapshot into a validated shared `JobSnapshot`; and
2. converts text-bearing uploaded PDF bytes into a `SourceDocument` while exposing stable A-owned PDF extraction errors.

The result must be consumable by Group B without inventing fields or importing Streamlit/business logic into Group A.

## Read

Only these files initially:

- `src/oi/contracts.py`
- `src/oi/io/pdf.py`
- `tests/test_contracts.py`
- `tests/fixtures/contracts/v0.2.0-draft/job_record.json`

Direct imports/dependencies may be inspected only as needed. Read `requirements.txt` only if necessary to confirm the existing `pypdf` dependency. Do not inspect remote branches for implementation ideas.

## Allowed to change

- `src/oi/contracts.py`
- `src/oi/io/pdf.py`
- `src/oi/io/snapshot.py` (new)
- `tests/test_contracts.py`
- `tests/test_io.py` (new)
- `tests/fixtures/contracts/v0.2.1-draft/job_snapshot.json` (new)

Everything else is read-only/out of scope.

## Workspace expectations

- **Expected branch:** `a/j01-contracts-a01-input`
- **Expected intentional local changes:** none when implementation starts
- Preserve all frozen `0.2.0-draft` behavior and fixtures.
- Do not commit or push.

## Approved decisions for this task

### 1. Versioning and compatibility

- `0.2.0-draft` remains frozen for existing `JobRecord`, `CandidateProfile`, `ClarificationRequest` and their fixtures.
- The new snapshot envelope is backward-compatible and serializes with `schema_version = "0.2.1-draft"`.
- Do not change the accepted values or semantics of existing `0.2.0-draft` payload fields merely to implement the snapshot envelope.
- Keep the existing `CONTRACT_VERSION` behavior stable unless a direct implementation need proves otherwise; a snapshot-specific version constant is acceptable. Do not perform a versioning refactor outside this task.

### 2. Persisted snapshot format

Snapshots are one UTF-8 JSON object, not JSONL.

`SourceManifestEntry` contains exactly:

- `source: str`
- `source_ref: str`
- `retrieved_at: AwareDatetime`
- `record_count: int >= 0`
- `redistribution_allowed: bool | null`

`QuarantineSummary` contains exactly:

- `reason: str`
- `count: int > 0`

`JobSnapshot` contains exactly:

- `schema_version`
- `snapshot_id`
- `created_at`
- `jobs: list[JobRecord]`
- `documents: dict[str, SourceDocument]`
- `source_manifest: list[SourceManifestEntry]`
- `quarantine: list[QuarantineSummary]`

Use the existing shared `ContractModel` strict-extra behavior (`extra="forbid"`). String IDs/reasons/source references are non-empty. Snapshot/manifest timestamps are timezone-aware and normalize to UTC.

### 3. Snapshot reference integrity

- Every key in `documents` must equal the contained `SourceDocument.document_id`.
- For every job, its `description` and every item in `source_documents` must exist in `documents` under the same ID and represent the same `SourceDocument` value.
- Every `EvidenceRef.document_id` in every job's top-level `evidence` list must resolve in the snapshot `documents` registry.
- Do not add a new shared rule that maps field-level `evidence_ids` to `JobRecord.evidence`; that is outside the approved A-01 delta.
- Do not add uniqueness rules for job IDs, manifest entries or quarantine reasons unless already structurally guaranteed.
- Do not validate manifest `record_count` against job counts or quarantine totals; those relationships were not approved.
- No raw quarantined payload belongs in `JobSnapshot`.

### 4. Snapshot loader

Implement exactly:

```python
def load_snapshot(path: Path) -> JobSnapshot: ...
```

Behavior:

- read one UTF-8 JSON object from `path`;
- validate it through `JobSnapshot`;
- return the validated model;
- preserve `FileNotFoundError`/filesystem errors for inaccessible paths;
- invalid JSON or contract-invalid JSON must fail visibly through Pydantic validation rather than returning partial/default data;
- no network calls, source fetching, caching or mutation.

### 5. PDF boundary

Keep the existing public signature:

```python
def extract_pdf_text(pdf_bytes: bytes, document_id: str) -> SourceDocument: ...
```

Add local A-owned:

```python
class PdfExtractionError(ValueError): ...
```

Behavior:

- successful text extraction remains a `SourceDocument(kind="cv")`;
- preserve SHA-256 of the original bytes as `content_hash` and `source_ref="uploaded_pdf"`;
- join extracted page text deterministically and reject all-whitespace/no-text output;
- malformed/unreadable PDF input, password-protected/unusable encrypted input, and no-text PDFs must surface as `PdfExtractionError`;
- preserve exception chaining when wrapping an underlying pypdf read/decryption/extraction error;
- do not add OCR, external binaries, network calls or a dependency.

## In scope

- Shared `0.2.1-draft` `JobSnapshot` envelope and its two supporting metadata models.
- One self-contained synthetic shared snapshot fixture.
- Local snapshot loader.
- Stable PDF extraction error boundary.
- Deterministic unit/contract tests for all approved invariants and error paths.

## Out of scope

- Greenhouse/Ashby/Lever fetching or normalization.
- Real source/company configuration.
- HTML normalization.
- Deduplication algorithms.
- Raw quarantine storage.
- Semantic job/CV extraction.
- RuleCatalogue, eligibility, ranking, embeddings, clarification or UI.
- OCR or scanned-PDF support.
- New dependencies.
- Changes to existing frozen `0.2.0-draft` schemas/fixtures.
- README/documentation cleanup unrelated to this task.

## Acceptance criteria

1. Existing `0.2.0-draft` tests and fixtures still pass unchanged.
2. `JobSnapshot` accepts only `schema_version="0.2.1-draft"`.
3. `created_at` and every manifest `retrieved_at` require timezone-aware datetimes and serialize normalized to UTC.
4. Manifest `record_count < 0` is rejected; quarantine `count <= 0` is rejected.
5. Unknown fields are rejected by all new shared models.
6. The snapshot fixture is a standalone UTF-8 JSON object and round-trips load -> Pydantic -> serialize -> reload.
7. Registry keys that disagree with `SourceDocument.document_id` are rejected.
8. A missing or conflicting registry copy of any embedded job description/source document is rejected.
9. A job `EvidenceRef.document_id` that does not resolve in the snapshot registry is rejected.
10. `load_snapshot` returns a validated `JobSnapshot` for the fixture.
11. Missing snapshot paths fail visibly; malformed JSON and schema-invalid JSON are not silently repaired/defaulted.
12. `extract_pdf_text` success preserves extracted text, document ID, `kind="cv"`, SHA-256 content hash and `source_ref="uploaded_pdf"`.
13. No-text PDF behavior raises `PdfExtractionError`.
14. Representative pypdf read/decryption/extraction failures are translated to `PdfExtractionError` with the original cause chained where applicable.
15. PDF tests do not require OCR, network access or a new package. Mock/fake reader objects are acceptable for deterministic unit coverage; do not claim they constitute a real-PDF integration test.
16. No Streamlit, ranking, eligibility or semantic extraction code is introduced in A-owned input modules.
17. The final diff contains only allowed files.

## Verification

Run exactly:

```bash
PYTHONPATH=src .venv/bin/python -m compileall -q src
git diff --check
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from oi.io.snapshot import load_snapshot

path = Path("tests/fixtures/contracts/v0.2.1-draft/job_snapshot.json")
snapshot = load_snapshot(path)
reloaded = type(snapshot).model_validate_json(snapshot.model_dump_json())
assert reloaded == snapshot
assert snapshot.schema_version == "0.2.1-draft"
print("snapshot round-trip ok")
PY
git --no-pager diff -- \
  src/oi/contracts.py \
  src/oi/io/pdf.py \
  src/oi/io/snapshot.py \
  tests/test_contracts.py \
  tests/test_io.py \
  tests/fixtures/contracts/v0.2.1-draft/job_snapshot.json
git status --short
```

## Stop conditions

In addition to `AGENTS.md`, stop if:

- D-037 is not recorded as jointly approved in `PROJECT_CONTEXT.md`;
- implementing the snapshot requires changing any existing `0.2.0-draft` payload semantics;
- a loader requirement would require inventing source-manifest fields, deduplication rules, source-count reconciliation or raw quarantine shape;
- PDF support would require OCR, a new dependency or external process;
- required verification exposes a failure that can only be fixed outside the allowed files.

## Required handoff

Report only:

1. files changed;
2. concise change summary;
3. verification commands and observed results;
4. unresolved issue/assumption;
5. `git status --short`.

Do not commit or push.
