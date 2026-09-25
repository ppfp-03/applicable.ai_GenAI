"""Deterministic ranking primitives for the opportunity-intelligence engine.

This module holds the internal building blocks of the ranking engine: factor
validation, weighted scoring with renormalization over available factors,
stable ordering, and the deadline-urgency, freshness and preference-fit
primitives. It does not decide eligibility, does not group eligible and
uncertain opportunities, and does not define the shared RankingItem /
RankingResponse envelopes, which are not frozen yet. Integration will consume
eligibility results and wrap these primitives once those interfaces exist.

Conventions:

- Every non-null factor value is a float in the closed range [0.0, 1.0].
  Values outside that range, NaN, infinities, booleans and non-numbers are
  rejected with ``InvalidFactorValue``; nothing is clipped.
- A missing factor is ``None``. It is never read as zero: its weight is
  redistributed proportionally over the factors that are present.
- Weights come from the caller. No weight lives in this module.
- Time-based primitives take an explicit, timezone-aware ``now``. Nothing here
  reads the system clock.
- Ranking consumes already enriched jobs. Nothing here triggers ingestion,
  extraction or a model call.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Callable, Iterable, Literal, Mapping, Protocol

from oi.contracts import (
    ActiveState,
    CandidatePreferences,
    CandidateProfile,
    DiscoveryKind,
    JobRecord,
)


FACTOR_NAMES: tuple[str, ...] = (
    "profile_fit",
    "preference_fit",
    "deadline_urgency",
    "freshness",
)

WEIGHT_SUM_TOLERANCE = 1e-9

# Decimal places compared when ordering. Scores that are mathematically equal
# but reached through different available factors can differ by float noise
# (0.1 vs 0.09999999999999999); rounding makes them a tie so job_id decides.
ORDERING_PRECISION = 12

SECONDS_PER_DAY = 86_400.0


class InvalidFactorValue(ValueError):
    """A factor or sub-factor value is outside the documented [0, 1] range."""


class InvalidWeights(ValueError):
    """A weight configuration is incomplete, unknown or does not sum to one."""


class InvalidTimestamp(ValueError):
    """A timestamp is naive, so it cannot be compared with an explicit ``now``."""


# --- Factor values ---------------------------------------------------------


def validate_factor_value(name: str, value: object) -> float | None:
    """Return ``value`` as a float in [0, 1], or ``None`` when missing.

    Booleans are rejected even though Python treats them as integers: a
    ``True`` fit score is a bug upstream, not a score of 1.
    """

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidFactorValue(f"{name} must be a number or None, got {value!r}")
    try:
        number = float(value)
    except OverflowError as error:
        raise InvalidFactorValue(f"{name} is too large to be a score") from error
    if not math.isfinite(number):
        raise InvalidFactorValue(f"{name} must be finite, got {value!r}")
    if not 0.0 <= number <= 1.0:
        raise InvalidFactorValue(f"{name} must be within [0, 1], got {value!r}")
    return number


@dataclass(frozen=True)
class FactorScores:
    """The four ranking factors for one job; ``None`` means missing."""

    profile_fit: float | None = None
    preference_fit: float | None = None
    deadline_urgency: float | None = None
    freshness: float | None = None

    def __post_init__(self) -> None:
        for name in FACTOR_NAMES:
            object.__setattr__(
                self, name, validate_factor_value(name, getattr(self, name))
            )

    def as_dict(self) -> dict[str, float | None]:
        return {name: getattr(self, name) for name in FACTOR_NAMES}


# --- Weighted score --------------------------------------------------------


def validate_weights(weights: Mapping[str, object]) -> Mapping[str, float]:
    """Check a weight configuration and return it as a read-only mapping.

    The configuration must name exactly the four factors, each with a finite
    non-negative weight, and the weights must sum to one. A zero weight keeps
    the factor visible in the breakdown without letting it move the score.
    """

    names = set(weights)
    missing = set(FACTOR_NAMES) - names
    unknown = names - set(FACTOR_NAMES)
    if missing or unknown:
        raise InvalidWeights(
            f"weights must name exactly {FACTOR_NAMES}; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )

    checked: dict[str, float] = {}
    for name in FACTOR_NAMES:
        value = weights[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidWeights(f"weight {name} must be a number, got {value!r}")
        try:
            number = float(value)
        except OverflowError as error:
            raise InvalidWeights(f"weight {name} is too large") from error
        if not math.isfinite(number) or number < 0.0:
            raise InvalidWeights(f"weight {name} must be finite and >= 0, got {value!r}")
        checked[name] = number

    total = math.fsum(checked.values())
    if total == 0.0:
        raise InvalidWeights("at least one weight must be > 0")
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise InvalidWeights(f"weights must sum to 1, got {total!r}")
    return MappingProxyType(checked)


@dataclass(frozen=True)
class ScoreBreakdown:
    """Everything needed to inspect how one priority score was produced.

    ``effective_weights`` covers only the available factors and sums to one;
    missing factors are listed in ``missing`` and have no effective weight.
    ``score`` is ``None`` when every factor is missing, or when every
    available factor has a configured weight of zero.
    """

    factors: Mapping[str, float | None]
    missing: tuple[str, ...]
    configured_weights: Mapping[str, float]
    effective_weights: Mapping[str, float]
    score: float | None


def compute_priority_score(
    factors: FactorScores, weights: Mapping[str, object]
) -> ScoreBreakdown:
    """Weight the available factors, renormalizing over the ones present.

    With every factor present the score is the plain weighted sum. When some
    are missing, each available factor's effective weight is its configured
    weight divided by the sum of configured weights of available factors.
    """

    configured = validate_weights(weights)
    values = factors.as_dict()
    available = [name for name in FACTOR_NAMES if values[name] is not None]
    missing = tuple(name for name in FACTOR_NAMES if values[name] is None)

    available_total = math.fsum(configured[name] for name in available)
    if available_total == 0.0:
        return ScoreBreakdown(
            factors=MappingProxyType(values),
            missing=missing,
            configured_weights=configured,
            effective_weights=MappingProxyType({}),
            score=None,
        )

    effective = {name: configured[name] / available_total for name in available}
    score = math.fsum(effective[name] * values[name] for name in available)
    return ScoreBreakdown(
        factors=MappingProxyType(values),
        missing=missing,
        configured_weights=configured,
        effective_weights=MappingProxyType(effective),
        score=score,
    )


# --- Stable ordering -------------------------------------------------------


@dataclass(frozen=True)
class ScoredJob:
    """A job ID paired with the breakdown of its priority score."""

    job_id: str
    breakdown: ScoreBreakdown

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, str) or not self.job_id:
            raise ValueError("job_id must be a non-empty string")

    @property
    def score(self) -> float | None:
        return self.breakdown.score


@dataclass(frozen=True)
class OrderedJobs:
    """Scored jobs in priority order, plus jobs with no computable score.

    Unscored jobs are kept, never dropped and never given a stand-in score;
    where they appear in a shortlist is an integration decision.
    """

    ranked: tuple[ScoredJob, ...]
    unscored: tuple[ScoredJob, ...]


def order_by_priority(jobs: Iterable[ScoredJob]) -> OrderedJobs:
    """Sort by descending score, breaking ties by ascending ``job_id``.

    Scores are compared at ``ORDERING_PRECISION`` decimal places; the stored
    score is left untouched. The result does not depend on input order.
    Duplicate job IDs are rejected because they would make the order ambiguous.
    """

    items = list(jobs)
    seen: set[str] = set()
    for item in items:
        if item.job_id in seen:
            raise ValueError(f"duplicate job_id {item.job_id!r}")
        seen.add(item.job_id)

    ranked = sorted(
        (item for item in items if item.score is not None),
        key=lambda item: (-round(item.score, ORDERING_PRECISION), item.job_id),
    )
    unscored = sorted(
        (item for item in items if item.score is None),
        key=lambda item: item.job_id,
    )
    return OrderedJobs(ranked=tuple(ranked), unscored=tuple(unscored))


# --- Time helpers ----------------------------------------------------------


def _require_aware(name: str, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidTimestamp(f"{name} must be timezone-aware, got {value!r}")
    return value


def _require_horizon(horizon_days: float) -> float:
    message = "horizon_days must be a finite number > 0"
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, (int, float)):
        raise ValueError(f"{message}, got {horizon_days!r}")
    try:
        horizon = float(horizon_days)
    except OverflowError as error:
        raise ValueError(f"{message}; value is too large") from error
    if not math.isfinite(horizon) or horizon <= 0:
        raise ValueError(f"{message}, got {horizon_days!r}")
    return horizon


def _linear_decay(days: float, horizon_days: float) -> float:
    """1.0 at zero days, falling linearly to 0.0 at the horizon and beyond."""

    return max(0.0, 1.0 - days / horizon_days)


# --- Deadline urgency ------------------------------------------------------


DeadlineStatus = Literal["missing", "open", "expired"]


@dataclass(frozen=True)
class DeadlineAssessment:
    """Deadline urgency for one job at an explicit ``now``.

    ``expired`` is an availability signal, separate from candidate
    eligibility; an expired job has no urgency score.
    """

    status: DeadlineStatus
    urgency: float | None
    days_remaining: float | None


def assess_deadline_urgency(
    deadline_at: datetime | None, now: datetime, *, horizon_days: float
) -> DeadlineAssessment:
    """Score urgency from an explicit deadline.

    Development heuristic, shape still TO VALIDATE: urgency falls linearly
    from 1.0 as the deadline arrives to 0.0 at ``horizon_days`` away or more.
    A deadline at or before ``now`` is expired, not maximally urgent.
    """

    _require_aware("now", now)
    horizon = _require_horizon(horizon_days)
    if deadline_at is None:
        return DeadlineAssessment(status="missing", urgency=None, days_remaining=None)

    _require_aware("deadline_at", deadline_at)
    days_remaining = (deadline_at - now).total_seconds() / SECONDS_PER_DAY
    if days_remaining <= 0:
        return DeadlineAssessment(
            status="expired", urgency=None, days_remaining=days_remaining
        )
    return DeadlineAssessment(
        status="open",
        urgency=_linear_decay(days_remaining, horizon),
        days_remaining=days_remaining,
    )


# --- Freshness -------------------------------------------------------------


FreshnessBasis = Literal[
    "publication",
    "discovery",
    "simulated_discovery",
    "missing",
    "invalid_future_timestamp",
]


@dataclass(frozen=True)
class FreshnessAssessment:
    """Freshness for one job, labeled with the timestamp it rests on.

    ``publication`` rests on ``source_published_at``. ``discovery`` rests on
    ``first_seen_at`` for a posting first observed after the initial snapshot
    and says nothing about posting age. ``simulated_discovery`` is the same
    signal for a controlled synthetic scenario and must be shown as simulated.
    """

    basis: FreshnessBasis
    freshness: float | None
    reference_at: datetime | None
    age_days: float | None


def assess_freshness(
    *,
    source_published_at: datetime | None,
    first_seen_at: datetime | None,
    discovery_kind: DiscoveryKind | str | None,
    now: datetime,
    horizon_days: float,
) -> FreshnessAssessment:
    """Score freshness from publication time, else from discovery time.

    ``source_updated_at`` is deliberately not a parameter: an update is not a
    publication. ``first_seen_at`` counts only for ``later_observation`` or
    ``synthetic_scenario`` postings; for the initial snapshot it only records
    when the system first looked, so freshness stays missing. A timestamp in
    the future of ``now`` is flagged and yields no score, with no fallback.

    Development heuristic, shape still TO VALIDATE: freshness falls linearly
    from 1.0 at age zero to 0.0 at ``horizon_days`` or older.
    """

    _require_aware("now", now)
    horizon = _require_horizon(horizon_days)

    if source_published_at is not None:
        return _freshness_from("publication", source_published_at, now, horizon)

    kind = DiscoveryKind(discovery_kind) if discovery_kind is not None else None
    if first_seen_at is not None and kind == DiscoveryKind.LATER_OBSERVATION:
        return _freshness_from("discovery", first_seen_at, now, horizon)
    if first_seen_at is not None and kind == DiscoveryKind.SYNTHETIC_SCENARIO:
        return _freshness_from("simulated_discovery", first_seen_at, now, horizon)

    return FreshnessAssessment(
        basis="missing", freshness=None, reference_at=None, age_days=None
    )


def _freshness_from(
    basis: FreshnessBasis, reference_at: datetime, now: datetime, horizon: float
) -> FreshnessAssessment:
    _require_aware(basis, reference_at)
    age_days = (now - reference_at).total_seconds() / SECONDS_PER_DAY
    if age_days < 0:
        return FreshnessAssessment(
            basis="invalid_future_timestamp",
            freshness=None,
            reference_at=reference_at,
            age_days=age_days,
        )
    return FreshnessAssessment(
        basis=basis,
        freshness=_linear_decay(age_days, horizon),
        reference_at=reference_at,
        age_days=age_days,
    )


# --- Preference fit --------------------------------------------------------


PREFERENCE_SUBFACTORS: tuple[str, ...] = ("location", "role_family", "industry")


@dataclass(frozen=True)
class PreferenceFitAssessment:
    """Preference fit and its sub-factors; unavailable ones carry a reason.

    ``score`` is the unweighted mean of available sub-factors, or ``None``
    when none is available.
    """

    score: float | None
    subfactors: Mapping[str, float | None]
    unavailable: Mapping[str, str] = field(default_factory=dict)


def _normalize_label(value: str) -> str:
    return value.strip().casefold()


def _location_fit(
    preferences: CandidatePreferences, job: JobRecord
) -> tuple[float | None, str | None]:
    """1.0 if any job country is preferred, 0.0 if every job country is known
    and none is preferred, else unavailable.

    ``allowed_country_codes`` is an eligibility input and is not read here.
    """

    if not preferences.preferred_country_codes:
        return None, "candidate_has_no_country_preference"
    if not job.locations:
        return None, "job_has_no_locations"

    preferred = set(preferences.preferred_country_codes)
    codes = [location.country_code for location in job.locations]
    known = [code.upper() for code in codes if code is not None]
    if any(code in preferred for code in known):
        return 1.0, None
    if not known:
        return None, "job_country_unknown"
    if len(known) < len(codes):
        return None, "job_country_partly_unknown"
    return 0.0, None


def _role_family_fit(
    preferences: CandidatePreferences, job: JobRecord
) -> tuple[float | None, str | None]:
    # Labels that are blank after normalization carry no fact: they are
    # ignored on the candidate side and count as not stated on the job side.
    wanted = {_normalize_label(item) for item in preferences.preferred_role_families}
    wanted.discard("")
    if not wanted:
        return None, "candidate_has_no_role_family_preference"
    if job.facts is None:
        return None, "job_facts_not_extracted"
    if job.facts.role_family is None:
        return None, "job_role_family_not_stated"
    role_family = _normalize_label(job.facts.role_family.value)
    if not role_family:
        return None, "job_role_family_not_stated"
    return (1.0 if role_family in wanted else 0.0), None


def _industry_fit(
    preferences: CandidatePreferences, job: JobRecord
) -> tuple[float | None, str | None]:
    # JobFacts 0.2.0-draft has no industry field, so there is nothing
    # structured to compare against; free text is not interpreted here.
    if not preferences.preferred_industries:
        return None, "candidate_has_no_industry_preference"
    if job.facts is None:
        return None, "job_facts_not_extracted"
    return None, "job_facts_have_no_industry_field"


def assess_preference_fit(
    preferences: CandidatePreferences, job: JobRecord
) -> PreferenceFitAssessment:
    """Match structured candidate preferences against structured job facts."""

    checks = {
        "location": _location_fit,
        "role_family": _role_family_fit,
        "industry": _industry_fit,
    }
    subfactors: dict[str, float | None] = {}
    unavailable: dict[str, str] = {}
    for name in PREFERENCE_SUBFACTORS:
        value, reason = checks[name](preferences, job)
        subfactors[name] = validate_factor_value(f"preference_fit.{name}", value)
        if reason is not None:
            unavailable[name] = reason

    available = [value for value in subfactors.values() if value is not None]
    score = math.fsum(available) / len(available) if available else None
    return PreferenceFitAssessment(
        score=score,
        subfactors=MappingProxyType(subfactors),
        unavailable=MappingProxyType(unavailable),
    )


# --- Profile fit boundary --------------------------------------------------


class ProfileFitScorer(Protocol):
    """Anything that returns an already computed profile-fit score.

    The embedding model and the exact skills/education/experience combination
    are not decided; this boundary only fixes what the ranking side accepts.
    """

    def __call__(self, candidate: CandidateProfile, job: JobRecord) -> float | None: ...


def profile_fit_from(
    scorer: ProfileFitScorer | Callable[[CandidateProfile, JobRecord], float | None],
    candidate: CandidateProfile,
    job: JobRecord,
) -> float | None:
    """Call ``scorer`` and validate its result like any other factor."""

    return validate_factor_value("profile_fit", scorer(candidate, job))


# --- Availability ----------------------------------------------------------


AvailabilityExclusion = Literal["closed", "expired"]


def availability_exclusion(
    job: JobRecord, now: datetime
) -> AvailabilityExclusion | None:
    """Return why a job is unavailable, or ``None`` if nothing rules it out.

    This is about the posting, not the candidate. An unknown active state or
    a missing deadline does not imply the posting is closed or expired.
    """

    _require_aware("now", now)
    if job.active_state == ActiveState.CLOSED:
        return "closed"
    if job.deadline_at is not None and job.deadline_at <= now:
        return "expired"
    return None


# --- Internal pipeline -----------------------------------------------------
#
# Everything below is a private orchestration layer, not the shared ranking
# contract. RankingConfig, RankingItem and RankingResponse are not frozen, so
# these types are deliberately named Pipeline* and may change freely. Once the
# shared envelopes and the eligibility interface are frozen, an adapter maps
# them onto AssessedJob and PipelineResult without touching scoring behavior.


EligibilityStanding = Literal["eligible", "uncertain", "ineligible"]

ExclusionReason = Literal["closed", "expired", "ineligible"]

# Local default for this pipeline only; the shared shortlist size is not frozen.
PIPELINE_DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class AssessedJob:
    """A job whose eligibility the caller has already decided.

    ``eligibility`` comes from the eligibility engine; ranking never computes
    it. ``eligibility_note`` is free diagnostic text passed through untouched.
    ``profile_fit`` is an already computed score, or ``None`` when absent.
    """

    job: JobRecord
    eligibility: EligibilityStanding
    eligibility_note: str | None = None
    profile_fit: float | None = None

    def __post_init__(self) -> None:
        if self.eligibility not in ("eligible", "uncertain", "ineligible"):
            raise ValueError(f"unknown eligibility {self.eligibility!r}")
        object.__setattr__(
            self, "profile_fit", validate_factor_value("profile_fit", self.profile_fit)
        )

    @property
    def job_id(self) -> str:
        return self.job.job_id


@dataclass(frozen=True)
class PipelineEntry:
    """One scored-or-unscored job in a ranked group, with every assessment."""

    assessed: AssessedJob
    breakdown: ScoreBreakdown
    preference: PreferenceFitAssessment
    deadline: DeadlineAssessment
    freshness: FreshnessAssessment

    @property
    def job_id(self) -> str:
        return self.assessed.job_id

    @property
    def score(self) -> float | None:
        return self.breakdown.score


@dataclass(frozen=True)
class PipelineExclusion:
    """A job kept out of every ranked group, and why.

    ``availability`` is the posting-level reason (closed or expired) and is
    reported before ``ineligible``; the caller's eligibility is kept as given,
    so a closed posting is never relabelled as candidate ineligibility.
    """

    assessed: AssessedJob
    reason: ExclusionReason
    availability: AvailabilityExclusion | None

    @property
    def job_id(self) -> str:
        return self.assessed.job_id


@dataclass(frozen=True)
class PipelineGroup:
    """One eligibility group: the top of the order, the rest, and unscored jobs.

    ``top`` holds at most the pipeline limit and is never padded. ``rest``
    keeps the scored jobs beyond the limit so none is lost. ``unscored`` holds
    jobs with no computable score, ordered by job ID and never given one.
    """

    top: tuple[PipelineEntry, ...]
    rest: tuple[PipelineEntry, ...]
    unscored: tuple[PipelineEntry, ...]


@dataclass(frozen=True)
class PipelineResult:
    """Internal outcome of one ranking run; not the shared RankingResponse."""

    eligible: PipelineGroup
    uncertain: PipelineGroup
    excluded: tuple[PipelineExclusion, ...]
    limit: int


def _require_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError(f"limit must be an integer >= 1, got {limit!r}")
    return limit


def _score_entry(
    assessed: AssessedJob,
    candidate: CandidateProfile,
    *,
    weights: Mapping[str, float],
    now: datetime,
    deadline_horizon_days: float,
    freshness_horizon_days: float,
    profile_fit_scorer: ProfileFitScorer | None,
) -> PipelineEntry:
    job = assessed.job
    if profile_fit_scorer is None:
        profile_fit = assessed.profile_fit
    elif assessed.profile_fit is not None:
        raise ValueError(
            f"job {job.job_id!r} has a supplied profile_fit and a scorer was "
            "also given; pass one or the other"
        )
    else:
        profile_fit = profile_fit_from(profile_fit_scorer, candidate, job)

    preference = assess_preference_fit(candidate.preferences, job)
    deadline = assess_deadline_urgency(
        job.deadline_at, now, horizon_days=deadline_horizon_days
    )
    freshness = assess_freshness(
        source_published_at=job.source_published_at,
        first_seen_at=job.first_seen_at,
        discovery_kind=job.discovery_kind,
        now=now,
        horizon_days=freshness_horizon_days,
    )
    breakdown = compute_priority_score(
        FactorScores(
            profile_fit=profile_fit,
            preference_fit=preference.score,
            deadline_urgency=deadline.urgency,
            freshness=freshness.freshness,
        ),
        weights,
    )
    return PipelineEntry(assessed, breakdown, preference, deadline, freshness)


def _group(entries: list[PipelineEntry], limit: int) -> PipelineGroup:
    by_id = {entry.job_id: entry for entry in entries}
    ordered = order_by_priority(ScoredJob(entry.job_id, entry.breakdown) for entry in entries)
    ranked = [by_id[item.job_id] for item in ordered.ranked]
    return PipelineGroup(
        top=tuple(ranked[:limit]),
        rest=tuple(ranked[limit:]),
        unscored=tuple(by_id[item.job_id] for item in ordered.unscored),
    )


def run_ranking_pipeline(
    candidate: CandidateProfile,
    jobs: Iterable[AssessedJob],
    *,
    weights: Mapping[str, object],
    now: datetime,
    deadline_horizon_days: float,
    freshness_horizon_days: float,
    profile_fit_scorer: ProfileFitScorer | None = None,
    limit: int = PIPELINE_DEFAULT_LIMIT,
) -> PipelineResult:
    """Score already-assessed jobs and split them into ranked groups.

    Closed or expired postings are excluded for availability, then
    ineligible jobs are excluded; neither is scored. Eligible and uncertain
    jobs are scored with the same rules and no penalty, then ordered
    separately. Profile fit comes either from each job's supplied value or
    from ``profile_fit_scorer``, never both. Nothing here calls a model.

    Raises:
        ValueError: On a duplicate job ID, an invalid limit or horizon, or a
            job carrying a profile fit when a scorer is also given.
        InvalidWeights, InvalidTimestamp, InvalidFactorValue: As raised by
            the primitives above.
    """

    checked_weights = validate_weights(weights)
    _require_aware("now", now)
    _require_horizon(deadline_horizon_days)
    _require_horizon(freshness_horizon_days)
    limit = _require_limit(limit)

    items = list(jobs)
    seen: set[str] = set()
    for assessed in items:
        if assessed.job_id in seen:
            raise ValueError(f"duplicate job_id {assessed.job_id!r}")
        seen.add(assessed.job_id)

    excluded: list[PipelineExclusion] = []
    groups: dict[str, list[PipelineEntry]] = {"eligible": [], "uncertain": []}
    for assessed in items:
        availability = availability_exclusion(assessed.job, now)
        if availability is not None:
            excluded.append(PipelineExclusion(assessed, availability, availability))
            continue
        if assessed.eligibility == "ineligible":
            excluded.append(PipelineExclusion(assessed, "ineligible", None))
            continue
        groups[assessed.eligibility].append(
            _score_entry(
                assessed,
                candidate,
                weights=checked_weights,
                now=now,
                deadline_horizon_days=deadline_horizon_days,
                freshness_horizon_days=freshness_horizon_days,
                profile_fit_scorer=profile_fit_scorer,
            )
        )

    return PipelineResult(
        eligible=_group(groups["eligible"], limit),
        uncertain=_group(groups["uncertain"], limit),
        excluded=tuple(sorted(excluded, key=lambda item: item.job_id)),
        limit=limit,
    )
