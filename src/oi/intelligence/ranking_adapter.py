"""Internal adapter from eligibility results to the ranking pipeline.

This joins the merged eligibility engine to ``ranking.run_ranking_pipeline``
without adding behavior of its own: each job's eligibility status is passed
through exactly, the full ``EligibilityResult`` is kept beside the pipeline
result, and scoring, availability, ordering and grouping all stay in
``ranking``. It is not ``rank_opportunities`` and defines no shared contract;
every type here is internal and may change once the shared envelopes freeze.

It lives apart from ``ranking`` so the ranking primitives keep no dependency
on the eligibility package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Iterable, Literal, Mapping

from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility import EligibilityResult, EligibilityStatus
from oi.intelligence.ranking import (
    PIPELINE_DEFAULT_LIMIT,
    AssessedJob,
    PipelineResult,
    ProfileFitScorer,
    run_ranking_pipeline,
)


class EligibilityMappingError(ValueError):
    """Jobs and eligibility results do not pair up one to one."""


AdapterDiagnosticCode = Literal["eligible_without_job_facts"]


@dataclass(frozen=True)
class AdapterDiagnostic:
    """A machine-readable note about the inputs; it never changes a result.

    ``eligible_without_job_facts``: eligibility reported ``eligible`` for a
    job whose ``facts`` is ``None``, so no job requirement was available to
    check. The status is passed through unchanged.
    """

    code: AdapterDiagnosticCode
    job_id: str


@dataclass(frozen=True)
class AdaptedRanking:
    """Pipeline result plus the untouched eligibility result for every job.

    ``eligibility`` holds one entry per supplied job, excluded jobs included.
    """

    pipeline: PipelineResult
    eligibility: Mapping[str, EligibilityResult]
    diagnostics: tuple[AdapterDiagnostic, ...]


def _index_unique(items: Iterable, kind: str) -> dict:
    indexed: dict = {}
    for item in items:
        if item.job_id in indexed:
            raise EligibilityMappingError(f"duplicate {kind} for job_id {item.job_id!r}")
        indexed[item.job_id] = item
    return indexed


def _validate_pairing(
    candidate: CandidateProfile,
    jobs: dict[str, JobRecord],
    results: dict[str, EligibilityResult],
) -> None:
    missing = sorted(set(jobs) - set(results))
    unknown = sorted(set(results) - set(jobs))
    if missing or unknown:
        raise EligibilityMappingError(
            f"jobs and eligibility results differ: without result {missing}, "
            f"result for unknown job {unknown}"
        )
    wrong_candidate = sorted(
        job_id
        for job_id, result in results.items()
        if result.candidate_id != candidate.candidate_id
    )
    if wrong_candidate:
        raise EligibilityMappingError(
            f"eligibility results for another candidate than "
            f"{candidate.candidate_id!r}: {wrong_candidate}"
        )


def _diagnostics(
    jobs: dict[str, JobRecord], results: dict[str, EligibilityResult]
) -> tuple[AdapterDiagnostic, ...]:
    return tuple(
        AdapterDiagnostic("eligible_without_job_facts", job_id)
        for job_id in sorted(jobs)
        if results[job_id].status is EligibilityStatus.ELIGIBLE
        and jobs[job_id].facts is None
    )


def rank_with_eligibility(
    candidate: CandidateProfile,
    jobs: Iterable[JobRecord],
    eligibility_results: Iterable[EligibilityResult],
    *,
    weights: Mapping[str, object],
    now: datetime,
    deadline_horizon_days: float,
    freshness_horizon_days: float,
    profile_fit: Mapping[str, float | None] | None = None,
    profile_fit_scorer: ProfileFitScorer | None = None,
    limit: int = PIPELINE_DEFAULT_LIMIT,
) -> AdaptedRanking:
    """Pair each job with its eligibility result and run the ranking pipeline.

    ``profile_fit`` maps job IDs to already computed scores; jobs it omits
    have no profile fit. It cannot be combined with ``profile_fit_scorer``.

    Raises:
        EligibilityMappingError: If jobs or results repeat a job ID, a job has
            no result, a result names no supplied job, a result belongs to
            another candidate, or ``profile_fit`` names an unknown job.
        ValueError: If both ``profile_fit`` and ``profile_fit_scorer`` are
            given, or as raised by ``run_ranking_pipeline``.
    """

    job_index = _index_unique(jobs, "job")
    result_index = _index_unique(eligibility_results, "eligibility result")
    _validate_pairing(candidate, job_index, result_index)

    if profile_fit is not None and profile_fit_scorer is not None:
        raise ValueError("pass profile_fit or profile_fit_scorer, not both")
    fits = dict(profile_fit or {})
    unknown_fits = sorted(set(fits) - set(job_index))
    if unknown_fits:
        raise EligibilityMappingError(f"profile_fit for unknown job {unknown_fits}")

    assessed = [
        AssessedJob(
            job=job,
            eligibility=result_index[job_id].status.value,
            profile_fit=fits.get(job_id),
        )
        for job_id, job in job_index.items()
    ]
    pipeline = run_ranking_pipeline(
        candidate,
        assessed,
        weights=weights,
        now=now,
        deadline_horizon_days=deadline_horizon_days,
        freshness_horizon_days=freshness_horizon_days,
        profile_fit_scorer=profile_fit_scorer,
        limit=limit,
    )
    return AdaptedRanking(
        pipeline=pipeline,
        eligibility=MappingProxyType({job_id: result_index[job_id] for job_id in sorted(job_index)}),
        diagnostics=_diagnostics(job_index, result_index),
    )
