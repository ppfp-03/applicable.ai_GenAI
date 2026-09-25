"""HC_DEGREE_LEVEL: the candidate's degree level meets the minimum.

Whether a degree still in progress satisfies the minimum is a policy, not a
fact, so it is configured rather than decided here: the job's parameter
`in_progress_policy` wins, otherwise the catalogue setting (default
"undecided") applies.
"""

from __future__ import annotations

from oi.intelligence.eligibility.catalogue import DEGREE_LEVELS
from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.models import UnknownCause
from oi.intelligence.eligibility.parameters import DegreeLevelParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
    unknown,
)

LEVEL_KEY = "degree_level"
STATUS_KEY = "degree_status"
DEFAULT_POLICY = "undecided"


def effective_policy(context: RuleContext, params: DegreeLevelParams) -> str:
    """Per-job override, else catalogue setting, else undecided."""

    if params.in_progress_policy is not None:
        return params.in_progress_policy
    return context.spec.settings.get("in_progress_policy", DEFAULT_POLICY)


def evaluate(context: RuleContext) -> Finding:
    """Compare levels on bachelor < master < phd, then apply the policy."""

    params = context.parameters
    if not isinstance(params, DegreeLevelParams):
        return missing_parameters(context.spec)

    cid = context.spec.constraint_id
    level = known_answer(context.candidate, cid, LEVEL_KEY)
    status = known_answer(context.candidate, cid, STATUS_KEY)

    if level is None:
        missing = [LEVEL_KEY] + ([STATUS_KEY] if status is None else [])
        return missing_answers(context.spec, *missing)

    need = params.min_level
    if DEGREE_LEVELS.index(level.value) < DEGREE_LEVELS.index(need):
        return conflict(
            f"A {need} degree is required; your highest level is {level.value}.",
            level.evidence_ids,
        )

    if status is None:
        return missing_answers(context.spec, STATUS_KEY)

    evidence = [*level.evidence_ids, *status.evidence_ids]
    if status.value == "completed":
        return met(f"A {need} degree is required; you hold a {level.value}.", evidence)

    policy = effective_policy(context, params)
    in_progress = f"A {need} degree is required; your {level.value} is in progress"
    if policy == "counts":
        return met(f"{in_progress}, which this posting accepts.", evidence)
    if policy == "does_not_count":
        return conflict(f"{in_progress}, and this posting requires it completed.", evidence)
    return unknown(
        UnknownCause.POLICY_UNDECIDED,
        f"{in_progress}; whether that counts is not decided for this posting.",
        evidence,
    )
