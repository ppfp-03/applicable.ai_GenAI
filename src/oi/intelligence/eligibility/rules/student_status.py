"""HC_STUDENT_STATUS: the candidate's status is one the programme accepts."""

from __future__ import annotations

from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.parameters import StudentStatusParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
)

ANSWER_KEY = "current_status"

_LABEL = {
    "enrolled_student": "an enrolled student",
    "recent_graduate": "a recent graduate",
    "neither": "neither a student nor a recent graduate",
}


def evaluate(context: RuleContext) -> Finding:
    """Declared status in the accepted set is MET, otherwise CONFLICT."""

    params = context.parameters
    if not isinstance(params, StudentStatusParams):
        return missing_parameters(context.spec)

    answer = known_answer(context.candidate, context.spec.constraint_id, ANSWER_KEY)
    if answer is None:
        return missing_answers(context.spec, ANSWER_KEY)

    accepted = " or ".join(_LABEL[status] for status in params.accepted)
    reason = f"The programme is for {accepted}; you are {_LABEL[answer.value]}."
    if answer.value in params.accepted:
        return met(reason, answer.evidence_ids)
    return conflict(reason, answer.evidence_ids)
