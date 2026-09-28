# A-02/A-03 Greenhouse ingestion spike: Rothesay

Status: ready for repository execution
Owner: Marco
Scope: one real Greenhouse posting, no shared-contract change

## Goal

Prove the first real Group A source path by fetching one published Greenhouse posting and converting it into the already-approved `JobRecord` / `JobSnapshot` boundary without adding ranking, eligibility, LLM extraction, UI logic, or a new shared schema.

Target posting from `A-02-SOURCES-01_clean.xlsx`:

- Company: Rothesay
- Board token: `rothesaygraduates`
- Job post ID: `8784142002`
- Public posting: `https://job-boards.greenhouse.io/rothesaygraduates/jobs/8784142002`
- Expected title from the reviewed source pack: `2027 Summer Internship Programme - Trading and Asset Origination`

Greenhouse documents the public endpoint as:

`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}`

GET Job Board API endpoints require no authentication.

## Existing project boundaries to preserve

1. Group A owns public-job ingestion, normalization, reproducible snapshots, PDF-to-text plumbing, and data/input integration.
2. Group B owns semantic extraction, `JobFacts`, requirement classification, eligibility, ranking, explanations, and UI.
3. Do not modify frozen `0.2.0-draft` core payload semantics.
4. Consume the approved `JobSnapshot 0.2.1-draft` boundary as-is.
5. `updated_at` is never relabeled as publication time.
6. Populate `source_published_at` only when Greenhouse actually returns `first_published`.
7. Populate `deadline_at` only when Greenhouse actually returns structured `application_deadline`. Do not parse a deadline out of job-description prose in Group A.
8. Missing source values remain null/unknown, not invented defaults.

## Bounded implementation

### 1. Add a Greenhouse source adapter

Preferred path if consistent with the current repository layout:

`src/oi/io/greenhouse.py`

Minimum public functions:

```python
def fetch_greenhouse_job(board_token: str, job_id: str, *, timeout_s: float = 15.0) -> dict:
    """Fetch one public Greenhouse job and return the decoded JSON object."""


def greenhouse_job_to_record(
    payload: dict,
    *,
    board_token: str,
    observed_at: datetime,
) -> JobRecord:
    """Convert one Greenhouse API payload into the frozen shared JobRecord."""
```

Keep network I/O separate from normalization so transformation tests do not require internet.

Do not add a dependency solely for this task. Reuse the repository's existing HTTP client if one is already installed; otherwise use the Python standard library.

### 2. Validate raw source identity

Fail visibly rather than silently repairing when any required identity/source field is unusable:

- `id`
- `title`
- `company_name`
- `absolute_url`
- non-empty `content`

The returned post ID must equal the requested post ID in the integration path.

### 3. Create deterministic source documents

Create one `SourceDocument(kind="job")` from the normalized Greenhouse `content`.

Create one `SourceDocument(kind="ats_metadata")` from a deterministic representation of the source metadata used by Group A, at minimum:

- `id`
- `internal_job_id` when present
- `company_name`
- `title`
- `location.name` when present
- `first_published` when present
- `updated_at` when present
- `application_deadline` when present
- `absolute_url`
- `language` when present

The metadata representation must be stable for identical input. `source_ref` should identify the public source endpoint/posting, not an invented URL.

### 4. Normalize description safely

Convert the Greenhouse HTML/entity-encoded `content` into readable text without executing source HTML.

Requirements:

- deterministic output;
- preserve useful paragraph/list boundaries where practical;
- collapse pathological whitespace;
- empty/unusable result is an error/quarantine condition, not a valid semantic input.

Do not use OCR, browser rendering, or LLM cleanup.

### 5. Map source fields conservatively

Use the frozen `JobRecord` fields.

Required mapping:

- `schema_version`: existing frozen core value
- `job_id`: `greenhouse:<source_job_id>`
- `source`: `greenhouse`
- `source_job_id`: string form of Greenhouse `id`
- `company`: `company_name`
- `title`: `title`
- `url`: `absolute_url`
- `description`: normalized job `SourceDocument`
- `source_documents`: include ATS metadata document
- `source_published_at`: parsed `first_published` or null
- `source_updated_at`: parsed `updated_at` or null
- `deadline_at`: parsed `application_deadline` or null
- `first_seen_at`: `observed_at` for this first-observation spike
- `last_seen_at`: same `observed_at`
- `active_state`: use only an already-approved deterministic source rule; otherwise `unknown`
- `discovery_kind`: `initial_snapshot`
- `facts`: null
- `extraction`: null

### 6. Location rule for this spike

Do not infer a country from city name alone.

If the source itself explicitly contains a country in the returned structured location string and the repository already has an approved/documented location normalizer, reuse it. Otherwise preserve the source location as evidence and leave unresolved structured country data unknown rather than introducing a new location-map decision inside this task.

Do not use the audited workbook's interpreted location column as the runtime source of truth.

### 7. Evidence/provenance

Any location/timestamp field that the contract requires to reference evidence must point to evidence contained in the created source documents.

Quotes must actually occur in the referenced normalized document under the contract's existing whitespace rules.

Do not manufacture evidence from the workbook annotations.

## Tests

Add deterministic tests under the repository's existing test structure.

Minimum cases:

1. documented Greenhouse-shaped payload converts to a valid `JobRecord`;
2. namespaced job ID is stable;
3. `first_published` and `updated_at` remain distinct;
4. missing `first_published` stays null and does not fall back to `updated_at`;
5. missing `application_deadline` stays null;
6. description HTML/entities normalize to non-empty text;
7. empty/unusable description fails visibly;
8. source metadata document is deterministic;
9. evidence references resolve;
10. `facts` and `extraction` remain null after Group A ingestion.

Keep a network-free unit test fixture clearly labeled as a test fixture, not evidence of the live Rothesay response.

## Live smoke test

Run one real GET for:

`https://boards-api.greenhouse.io/v1/boards/rothesaygraduates/jobs/8784142002`

Record, without fabricating missing values:

- HTTP status;
- observed timestamp in UTC;
- returned `id`, `title`, `company_name`, location string;
- presence/absence of `first_published`, `updated_at`, `application_deadline`;
- resulting namespaced `job_id`;
- validation result.

Then create a one-job `JobSnapshot 0.2.1-draft`, serialize it, load it through the existing `load_snapshot(Path)` boundary, and verify round-trip equality if that is the repository's existing snapshot acceptance pattern.

If the live post has disappeared or the API request fails, record the failure as observed evidence. Do not replace it silently with workbook data or a handcrafted payload.

## Acceptance criteria

The task is done only when:

- the adapter transforms the live source shape without changing shared contracts;
- the full existing test suite remains green;
- the new normalization tests pass;
- a real Rothesay fetch is either successfully validated or its live-source failure is explicitly recorded;
- the one-job snapshot passes the existing loader/contract boundary when a live fetch succeeds;
- no ranking, eligibility, LLM, UI, or second-ATS code is added;
- the diff is reviewed for staged, unstaged, and untracked files before handoff.

## Verification commands

Use the repository's documented environment and commands. At minimum, rerun the full test suite already used for A-01 plus the targeted Greenhouse tests. Also run the repository's existing mechanical checks if configured.

Do not report any command as passed unless it was actually executed.

## Handoff

On completion, hand the one-job normalized snapshot/result to:

- Pierpaolo, to confirm Group B consumes it without schema patches;
- Tommaso, for the first real source/input integration acceptance check.

## Sources

- Team source pack: `A-02-SOURCES-01_clean.xlsx`, Rothesay row.
- Current Project Context: source boundaries, JobRecord contract, provenance/freshness rules, Group A/B ownership.
- Greenhouse Job Board API: https://docs.greenhouse.io/job-board.html
