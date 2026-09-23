"""Deterministic multi-job Greenhouse batch ingestion for Group A.

This module orchestrates the already-verified single-job Greenhouse boundary
across several configured postings and returns one `JobSnapshot 0.2.1-draft`.
It adds no shared contract, no configuration model and no semantic extraction.

Approved behavior:

- D-038: batch ingestion is partial-success. A posting that fails with an
  expected Greenhouse fetch or normalization failure is omitted from `jobs`
  and summarized through a stable `JobSnapshot.quarantine` reason, while the
  other valid postings remain in the snapshot. Unexpected programming and
  contract failures propagate.
- D-039: one `SourceManifestEntry` per successfully fetched-and-normalized
  posting, preserving the exact Greenhouse public API posting endpoint as
  `source_ref`, the batch observation time as `retrieved_at`, and
  `record_count=1`. Failed targets create no successful manifest entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence, Union

from oi.contracts import (
    SNAPSHOT_CONTRACT_VERSION,
    JobRecord,
    JobSnapshot,
    QuarantineSummary,
    SourceDocument,
    SourceManifestEntry,
)
from oi.io.greenhouse import (
    GreenhouseFetchError,
    GreenhouseNormalizationError,
    fetch_greenhouse_job,
    greenhouse_job_to_record,
)

GREENHOUSE_SOURCE = "greenhouse"

FETCH_QUARANTINE_REASON = "greenhouse_fetch_error"
"""Stable quarantine reason for an expected Greenhouse fetch failure."""

NORMALIZATION_QUARANTINE_REASON = "greenhouse_normalization_error"
"""Stable quarantine reason for an expected Greenhouse normalization failure."""


class DuplicateTargetError(ValueError):
    """Raised when the same (board_token, job_id) is configured twice.

    A repeated target is a caller input defect, not a source-quality problem,
    so it is rejected before any network call instead of being quarantined.
    """


class DocumentRegistryConflictError(ValueError):
    """Raised when one document ID would register two different documents."""


@dataclass(frozen=True, slots=True)
class GreenhouseTarget:
    """One configured Greenhouse posting to ingest.

    Local batch input only: deliberately not a shared configuration contract.
    """

    board_token: str
    job_id: str


TargetInput = Union[GreenhouseTarget, tuple[str, str]]


def _as_target(value: TargetInput) -> GreenhouseTarget:
    """Normalize one configured target and reject unusable identifiers.

    Surrounding whitespace is trimmed first so whitespace-equivalent targets
    resolve to the same identity for duplicate detection. An empty identifier
    is a caller input defect, not a source-quality problem.
    """

    if isinstance(value, GreenhouseTarget):
        board_token, job_id = value.board_token, value.job_id
    else:
        board_token, job_id = value

    token = board_token.strip()
    post_id = job_id.strip()
    if not token:
        raise ValueError("board_token must be non-empty")
    if not post_id:
        raise ValueError("job_id must be non-empty")
    return GreenhouseTarget(board_token=token, job_id=post_id)


def _normalize_targets(targets: Sequence[TargetInput]) -> list[GreenhouseTarget]:
    """Preserve caller order and reject duplicates before any network call."""

    normalized: list[GreenhouseTarget] = []
    seen: set[tuple[str, str]] = set()
    for value in targets:
        target = _as_target(value)
        key = (target.board_token, target.job_id)
        if key in seen:
            raise DuplicateTargetError(
                f"duplicate Greenhouse target board '{target.board_token}' "
                f"job '{target.job_id}'"
            )
        seen.add(key)
        normalized.append(target)
    return normalized


def _register_documents(
    registry: dict[str, SourceDocument],
    record: JobRecord,
) -> None:
    """Register a job's own documents, failing visibly on a content conflict."""

    documents = [record.description, *record.source_documents]
    for document in documents:
        registered = registry.get(document.document_id)
        if registered is not None and registered != document:
            raise DocumentRegistryConflictError(
                f"document '{document.document_id}' is registered with "
                f"different content by job '{record.job_id}'"
            )
        registry[document.document_id] = document


def _manifest_entry(
    record: JobRecord,
    *,
    observed_at: datetime,
) -> SourceManifestEntry:
    # The single-job adapter already stores the exact public API posting
    # endpoint on the normalized description document, so the manifest reuses
    # that endpoint instead of re-deriving one here.
    return SourceManifestEntry(
        source=GREENHOUSE_SOURCE,
        source_ref=record.description.source_ref,
        retrieved_at=observed_at,
        record_count=1,
        redistribution_allowed=None,
    )


def _quarantine_summaries(counts: dict[str, int]) -> list[QuarantineSummary]:
    return [
        QuarantineSummary(reason=reason, count=count)
        for reason, count in counts.items()
        if count > 0
    ]


def build_greenhouse_snapshot(
    targets: Sequence[TargetInput],
    *,
    snapshot_id: str,
    observed_at: datetime,
    timeout_s: float = 15.0,
) -> JobSnapshot:
    """Ingest several Greenhouse postings into one JobSnapshot.

    Args:
        targets: Configured postings, as `GreenhouseTarget` values or
            `(board_token, job_id)` pairs. Caller order is preserved.
        snapshot_id: Caller-provided snapshot identity. Nothing is generated
            from randomness, time or content.
        observed_at: One timezone-aware observation time for the whole batch.
        timeout_s: Per-request fetch timeout passed to the single-job adapter.

    Returns:
        One `JobSnapshot 0.2.1-draft` holding the successfully ingested jobs in
        input order, the canonical document registry, one manifest entry per
        successful job, and aggregated quarantine summaries for the expected
        failures observed during the batch.

    Raises:
        ValueError: If `observed_at` is not timezone-aware, or a target
            identifier is empty after trimming. Both are caller input defects
            and are rejected before any fetch rather than quarantined.
        DuplicateTargetError: If the same (board_token, job_id) appears twice
            after trimming surrounding whitespace.
        DocumentRegistryConflictError: If one document ID would register two
            different documents.
        Exception: Any unexpected failure from the single-job boundary, and any
            contract failure raised while constructing the snapshot, propagates
            unchanged.
    """

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")

    ordered_targets = _normalize_targets(targets)

    jobs: list[JobRecord] = []
    documents: dict[str, SourceDocument] = {}
    manifest: list[SourceManifestEntry] = []
    quarantine_counts: dict[str, int] = {}

    for target in ordered_targets:
        try:
            payload = fetch_greenhouse_job(
                target.board_token,
                target.job_id,
                timeout_s=timeout_s,
            )
        except GreenhouseFetchError:
            quarantine_counts[FETCH_QUARANTINE_REASON] = (
                quarantine_counts.get(FETCH_QUARANTINE_REASON, 0) + 1
            )
            continue

        try:
            record = greenhouse_job_to_record(
                payload,
                board_token=target.board_token,
                observed_at=observed_at,
            )
        except GreenhouseNormalizationError:
            quarantine_counts[NORMALIZATION_QUARANTINE_REASON] = (
                quarantine_counts.get(NORMALIZATION_QUARANTINE_REASON, 0) + 1
            )
            continue

        _register_documents(documents, record)
        jobs.append(record)
        manifest.append(_manifest_entry(record, observed_at=observed_at))

    return JobSnapshot(
        schema_version=SNAPSHOT_CONTRACT_VERSION,
        snapshot_id=snapshot_id,
        created_at=observed_at,
        jobs=jobs,
        documents=documents,
        source_manifest=manifest,
        quarantine=_quarantine_summaries(quarantine_counts),
    )
