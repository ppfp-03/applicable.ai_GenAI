"""What a rule receives and what it returns.

A rule is a pure function from a RuleContext to a Finding. It never builds a
RuleOutcome itself: the engine adds the rule ID, version, requirement and the
modality gate, so every rule is judged the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from oi.contracts import CandidateProfile, JobRecord, RequirementFact
from oi.intelligence.eligibility.catalogue import ConstraintSpec
from oi.intelligence.eligibility.models import RuleStatus, UnknownCause
from oi.intelligence.eligibility.parameters import JobParameters


@dataclass(frozen=True)
class RuleContext:
    """Everything one rule may look at for one requirement.

    `requirement` is None for job-location rules. `parameters` is None when
    no usable entry exists in the parameter layer.
    """

    candidate: CandidateProfile
    job: JobRecord
    spec: ConstraintSpec
    requirement: RequirementFact | None = None
    parameters: JobParameters | None = None


@dataclass(frozen=True)
class Finding:
    """A rule's raw conclusion, before the engine wraps it."""

    status: RuleStatus
    reason: str
    candidate_evidence_ids: tuple[str, ...] = ()
    job_evidence_ids: tuple[str, ...] = ()
    unknown_cause: UnknownCause | None = None
    missing_field_paths: tuple[str, ...] = ()


RuleFn = Callable[[RuleContext], Finding]


def met(reason: str, candidate: Iterable[str] = (), job: Iterable[str] = ()) -> Finding:
    return Finding(RuleStatus.MET, reason, tuple(candidate), tuple(job))


def conflict(
    reason: str, candidate: Iterable[str] = (), job: Iterable[str] = ()
) -> Finding:
    return Finding(RuleStatus.CONFLICT, reason, tuple(candidate), tuple(job))


def not_applicable(reason: str, job: Iterable[str] = ()) -> Finding:
    return Finding(RuleStatus.NOT_APPLICABLE, reason, (), tuple(job))


def unknown(
    cause: UnknownCause,
    reason: str,
    candidate: Iterable[str] = (),
    job: Iterable[str] = (),
    missing: Iterable[str] = (),
) -> Finding:
    return Finding(
        RuleStatus.UNKNOWN,
        reason,
        tuple(candidate),
        tuple(job),
        cause,
        tuple(missing),
    )


def missing_answers(spec: ConstraintSpec, *keys: str) -> Finding:
    """UNKNOWN because the candidate has not answered `keys` yet."""

    labels = ", ".join(keys)
    return unknown(
        UnknownCause.CANDIDATE_MISSING,
        f"{spec.label}: your answer is missing ({labels}).",
        missing=[spec.field_path(key) for key in keys],
    )


def missing_parameters(spec: ConstraintSpec) -> Finding:
    """UNKNOWN because the job-side values for this requirement are not recorded."""

    return unknown(
        UnknownCause.JOB_PARAMETER_MISSING,
        f"{spec.label}: the posting's exact requirement is not recorded as "
        "structured parameters, so it cannot be compared.",
    )
