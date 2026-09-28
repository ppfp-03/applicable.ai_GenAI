"""HC_GRAD_WINDOW: the graduation date falls inside the posting's window."""

from __future__ import annotations

from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.parameters import GradWindowParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
)

ANSWER_KEY = "expected_graduation_date"


def evaluate(context: RuleContext) -> Finding:
    """start <= graduation date <= end, both ends inclusive."""

    params = context.parameters
    if not isinstance(params, GradWindowParams):
        return missing_parameters(context.spec)

    answer = known_answer(context.candidate, context.spec.constraint_id, ANSWER_KEY)
    if answer is None:
        return missing_answers(context.spec, ANSWER_KEY)

    graduation = answer.value
    window = f"{params.start.isoformat()} to {params.end.isoformat()}"
    if params.start <= graduation <= params.end:
        return met(
            f"Graduation {graduation.isoformat()} is inside the window {window}.",
            answer.evidence_ids,
        )
    return conflict(
        f"Graduation {graduation.isoformat()} is outside the window {window}.",
        answer.evidence_ids,
    )
