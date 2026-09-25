"""HC_LANGUAGE: the candidate's level meets the required CEFR level.

One requirement names one language; a posting that needs two languages has two
requirements and gets two outcomes. "native" satisfies every CEFR level.
"""

from __future__ import annotations

from oi.intelligence.eligibility.catalogue import CEFR_LEVELS
from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.parameters import LanguageParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
)


def _rank(level: str) -> int:
    return len(CEFR_LEVELS) if level == "native" else CEFR_LEVELS.index(level)


def evaluate(context: RuleContext) -> Finding:
    """Candidate level >= required level on the CEFR scale."""

    params = context.parameters
    if not isinstance(params, LanguageParams):
        return missing_parameters(context.spec)

    key = f"level_{params.language}"
    answer = known_answer(context.candidate, context.spec.constraint_id, key)
    if answer is None:
        return missing_answers(context.spec, key)

    have, need = answer.value, params.min_level
    language = params.language.upper()
    if _rank(have) >= _rank(need):
        return met(f"{language} {need} required; you have {have}.", answer.evidence_ids)
    return conflict(f"{language} {need} required; you have {have}.", answer.evidence_ids)
