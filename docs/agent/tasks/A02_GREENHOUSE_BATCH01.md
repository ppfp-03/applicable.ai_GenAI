# A-02/A-03 Greenhouse Batch 01 orchestration

> Derived execution brief. It may repeat approved facts needed for implementation, but it does not replace or override the repository-root `PROJECT_CONTEXT.md`. If this brief and `PROJECT_CONTEXT.md` conflict, stop and report the conflict.

## Metadata

- **Task ID:** `A-02/A-03-BATCH-01`
- **Status:** `ready`
- **Owner:** Marco / Group A
- **Expected project-context version:** `0.4.6-draft`
- **Expected contract versions:** core `0.2.0-draft`; `JobSnapshot 0.2.1-draft`
- **Approved decisions:** `D-038`, `D-039`

## Approved decisions applied by this task

- **D-038:** Group A Greenhouse batch ingestion is partial-success. A configured posting that fails with an expected Greenhouse fetch or normalization failure is omitted from `jobs` and summarized through stable `JobSnapshot.quarantine` reasons, while other valid postings remain in the snapshot. Unexpected programming/contract failures propagate.
- **D-039:** Group A Greenhouse batch snapshots use one `SourceManifestEntry` per successfully fetched-and-normalized posting, preserving the exact Greenhouse public API posting endpoint as `source_ref`, the batch observation time as `retrieved_at`, and `record_count=1`. Failed targets do not create successful manifest entries.

## Goal

Extend the already-verified single-job Greenhouse ingestion path into deterministic multi-job batch orchestration that returns one valid `JobSnapshot 0.2.1-draft`, while preserving every frozen shared contract and keeping Group B behavior entirely out of scope.

The batch mechanism must work before the exact real Batch 01 vacancy list is approved. Do not choose or invent real postings.

## Implementation context to read

Read only:

- `docs/agent/tasks/A02_GREENHOUSE_ROTHESAY_TASK.md`
- `src/oi/io/greenhouse.py`
- `src/oi/io/snapshot.py`
- only the `SourceManifestEntry`, `QuarantineSummary` and `JobSnapshot` definitions in `src/oi/contracts.py`
- `tests/test_greenhouse.py`
- `tests/test_io.py`

Inspect direct imports/dependencies only if needed.

## Allowed files

- `PROJECT_CONTEXT.md`
- `docs/agent/tasks/A02_GREENHOUSE_BATCH01.md` (new)
- `src/oi/io/greenhouse_batch.py` (new)
- `tests/test_greenhouse_batch.py` (new)
- `src/oi/io/__init__.py`, only if a narrow export/integration need genuinely requires it
- `docs/agent/tasks/A02_BATCH01_AGENT_TASK.md`, deletion only; superseded by this brief and not recreated

`src/oi/io/greenhouse.py` must not be modified. If the existing single-job adapter prevents safe reuse, stop and report the blocker before changing it. Everything else is read-only.

## Batch behavior

Use a local input shape only. Do not create a shared `SourceConfig` contract. Each target contains exactly:

- `board_token`
- `job_id`

Preserve caller input order.

For each target call the existing boundaries:

- `fetch_greenhouse_job(...)`
- `greenhouse_job_to_record(...)`

Use one caller-supplied timezone-aware `observed_at` for the entire batch.

### Partial failure

- Process targets independently.
- `GreenhouseFetchError`: continue and aggregate the stable quarantine reason `greenhouse_fetch_error`.
- `GreenhouseNormalizationError`: continue and aggregate the stable quarantine reason `greenhouse_normalization_error`.
- Do not store failed/raw payloads in the shared snapshot.
- Do not use dynamic exception strings as quarantine reasons.
- Unexpected exceptions and Pydantic/contract failures propagate.
- If all configured targets fail, return a contract-valid zero-job snapshot with the observed quarantine summaries if the frozen `JobSnapshot` permits it. If the frozen contract rejects that shape, stop and report the exact contract evidence instead of inventing a workaround.

### Manifest

For every successfully fetched and normalized posting create exactly one `SourceManifestEntry`:

- `source="greenhouse"`
- exact public API posting endpoint as `source_ref`
- `retrieved_at=observed_at`
- `record_count=1`
- `redistribution_allowed=None`

No successful manifest entry for failed targets. Reuse the endpoint semantics already present in the existing Greenhouse adapter. Do not invent board-level manifest entries.

### Documents

Build the top-level `documents` registry from each successful job's primary `description` plus all `source_documents`.

- Registry key must equal `document.document_id`.
- The registered object must be exactly equal to the embedded object.
- If two successful jobs attempt to register the same document ID with different content, fail visibly.

### Duplicate input

Reject duplicate `(board_token, job_id)` targets before any network call. This is an input defect, not quarantine.

### Snapshot identity

Require a caller-provided `snapshot_id`. Do not generate random, time-derived or content-derived IDs.

Return one `JobSnapshot` with:

- `schema_version="0.2.1-draft"`
- caller `snapshot_id`
- `created_at=observed_at`
- successful jobs in input order
- complete canonical document registry
- one manifest entry per successful job in input order
- aggregated stable quarantine summaries

Let `JobSnapshot` enforce frozen reference integrity. Do not repair invalid snapshots after construction.

A public function of this shape is acceptable:

```python
def build_greenhouse_snapshot(
    targets: Sequence[tuple[str, str]],
    *,
    snapshot_id: str,
    observed_at: datetime,
    timeout_s: float = 15.0,
) -> JobSnapshot:
    ...
```

A small local immutable target helper is also acceptable. Do not add a shared configuration model or dependency.

## Explicitly out of scope

- choosing the real Batch 01 vacancy list
- changes to frozen contracts
- `JobFacts` semantic extraction
- LLM/provider work
- candidate extraction
- eligibility/hard constraints
- ranking/weights/embeddings/freshness scoring
- UI/Streamlit
- OCR
- workbook annotations as runtime source truth
- second ATS support
- persistence-format changes
- new dependencies
- Pierpaolo branch/work
- Git publication actions

## Required tests

Deterministic and network-free, covering at least:

1. two valid targets;
2. valid + fetch failure;
3. valid + normalization failure;
4. two fetch failures aggregate to count 2;
5. two normalization failures aggregate to count 2;
6. fetch and normalization failures create separate quarantine summaries;
7. duplicate input rejects before fetch invocation;
8. output preserves input order;
9. document registry is complete and exact;
10. manifest source refs match the exact Greenhouse posting endpoints;
11. unexpected exception propagates;
12. conflicting duplicate document IDs fail visibly;
13. all targets fail and behavior matches the frozen contract;
14. mixed-success snapshot round-trips through JSON serialization with equality preserved.

Do not perform live HTTP requests in automated tests.

## Verification

```
PYTHONPATH=src pytest tests/test_greenhouse_batch.py -q
PYTHONPATH=src pytest tests/test_greenhouse.py tests/test_io.py -q
PYTHONPATH=src pytest -q
npm test
git diff --check
git status --short
```

Then inspect the complete allowed-file change set relative to `HEAD`. Untracked files are not shown by normal `git diff` and must be inspected explicitly. Confirm no file outside the allowed set changed.

## Stop conditions

Stop and report the smallest blocker if:

- context version or decision IDs do not match the expected state;
- the workspace is not clean at task start;
- the task branch already exists and its safety is ambiguous;
- the batch implementation requires changing `src/oi/contracts.py`;
- the existing single-job adapter must change;
- the frozen `JobSnapshot` cannot represent the approved partial-success behavior;
- a new dependency is required;
- implementation requires choosing real vacancy targets;
- a failure category cannot be represented truthfully by `QuarantineSummary`;
- any required change falls outside the allowed files.

## Git constraints

Do not stage, commit, push, merge, rebase, cherry-pick, reset, or rewrite history.
