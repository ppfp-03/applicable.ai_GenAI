"""HC_MIN_EXPERIENCE: an explicit, bounded minimum of prior experience.

A requirement is compared either against months of prior experience, or
against one approved boolean answer key naming a specific kind of experience
(for example `has_corporate_finance_experience`, D-040). Nothing is inferred
from the CV text: equivalent experience is never guessed.
"""

from __future__ import annotations

from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.parameters import MinExperienceParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
)

MONTHS_KEY = "prior_experience_months"


def evaluate(context: RuleContext) -> Finding:
    """Boolean key: true MET, false CONFLICT. Months: have >= need."""

    params = context.parameters
    if not isinstance(params, MinExperienceParams):
        return missing_parameters(context.spec)

    cid = context.spec.constraint_id

    if params.answer_key is not None:
        answer = known_answer(context.candidate, cid, params.answer_key)
        if answer is None:
            return missing_answers(context.spec, params.answer_key)
        label = params.answer_key.removeprefix("has_").replace("_", " ")
        if answer.value:
            return met(f"The posting requires {label}; you declared it.", answer.evidence_ids)
        return conflict(
            f"The posting requires {label}; you declared you do not have it.",
            answer.evidence_ids,
        )

    answer = known_answer(context.candidate, cid, MONTHS_KEY)
    if answer is None:
        return missing_answers(context.spec, MONTHS_KEY)
    reason = (
        f"The posting requires at least {params.min_months} months of experience; "
        f"you have {answer.value}."
    )
    if answer.value >= params.min_months:
        return met(reason, answer.evidence_ids)
    return conflict(reason, answer.evidence_ids)
