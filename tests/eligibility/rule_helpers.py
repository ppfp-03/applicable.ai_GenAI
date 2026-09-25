"""Run one rule through the real engine and return its outcome(s)."""

from __future__ import annotations

from typing import Any

from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility import RuleOutcome, assess_eligibility, load_rule_catalogue
from oi.intelligence.eligibility.parameters import JobParameterSet

from . import builders as b

CATALOGUE = load_rule_catalogue()


def outcomes_for(
    constraint_id: str,
    candidate: CandidateProfile,
    job: JobRecord,
    layer: JobParameterSet | None = None,
) -> list[RuleOutcome]:
    result = assess_eligibility(candidate, job, CATALOGUE, job_parameters=layer)
    return [o for o in result.outcomes if o.rule_id == constraint_id]


def single(
    constraint_id: str,
    candidate: CandidateProfile,
    params: dict[str, Any] | None = None,
    modality: str = "mandatory",
    locations: Any = (("NL", "Amsterdam"),),
) -> RuleOutcome:
    """Evaluate one requirement `req-1` for `constraint_id` with `params`."""

    job = b.job(locations=locations, requirements=[("req-1", constraint_id, modality)])
    layer = b.parameters(("req-1", constraint_id, params)) if params else None
    (outcome,) = outcomes_for(constraint_id, candidate, job, layer)
    return outcome
