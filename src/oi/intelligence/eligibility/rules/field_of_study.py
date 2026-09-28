"""HC_FIELD_OF_STUDY: the candidate's field is one the posting accepts.

Whether a field counts as "related" is a judgement, not a lookup, so a posting
that also accepts related fields leaves any other field UNKNOWN.
"""

from __future__ import annotations

from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.models import UnknownCause
from oi.intelligence.eligibility.parameters import FieldOfStudyParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
    unknown,
)

ANSWER_KEY = "field_of_study"


def evaluate(context: RuleContext) -> Finding:
    """Listed field is MET; unlisted is CONFLICT, or UNKNOWN if related counts."""

    params = context.parameters
    if not isinstance(params, FieldOfStudyParams):
        return missing_parameters(context.spec)

    answer = known_answer(context.candidate, context.spec.constraint_id, ANSWER_KEY)
    if answer is None:
        return missing_answers(context.spec, ANSWER_KEY)

    field = answer.value
    accepted = ", ".join(params.accepted)
    if field in params.accepted:
        return met(f"The posting accepts {accepted}; you studied {field}.", answer.evidence_ids)
    if params.related_accepted:
        return unknown(
            UnknownCause.POLICY_UNDECIDED,
            f"The posting accepts {accepted} or a related field; whether {field} "
            "counts as related is not decided by a rule.",
            answer.evidence_ids,
        )
    return conflict(
        f"The posting accepts only {accepted}; you studied {field}.", answer.evidence_ids
    )
