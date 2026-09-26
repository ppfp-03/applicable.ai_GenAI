"""HC_LANGUAGE: the candidate's level meets the required level on its scale.

One requirement names one language; a posting that needs two languages has two
requirements and gets two outcomes.

Levels keep the scale they were stated on (CEFR, HSK, JLPT, or SELF for
"fluent" and "native") and are compared only within one scale. Two levels on
different scales are never converted into each other: the outcome is UNKNOWN.
"Fluent" counts as a fixed level for the languages in FLUENT_LEVELS, on the
candidate and the job side alike, and stays on the SELF scale for every other
language. "Native" is the highest level of a language: it meets any
requirement for that language, and a native requirement is met by nothing
else, whatever the scale.
"""

from __future__ import annotations

from oi.intelligence.eligibility.catalogue import LanguageLevel, language_level_key
from oi.intelligence.eligibility.inputs import known_answer
from oi.intelligence.eligibility.models import UnknownCause
from oi.intelligence.eligibility.parameters import LanguageParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    missing_answers,
    missing_parameters,
    unknown,
)

#: What "fluent" counts as, by ISO 639-1 language code.
FLUENT_LEVELS = {
    "en": LanguageLevel("CEFR", "C1"),
    "zh": LanguageLevel("HSK", "5"),
    "ja": LanguageLevel("JLPT", "N1"),
}
FLUENT = LanguageLevel("SELF", "fluent")
NATIVE = LanguageLevel("SELF", "native")


def normalize(language: str, level: LanguageLevel) -> LanguageLevel:
    """"Fluent" as its fixed level for `language`, if it has one; else unchanged."""

    return FLUENT_LEVELS.get(language, level) if level == FLUENT else level


def meets(language: str, have: LanguageLevel, need: LanguageLevel) -> bool | None:
    """Whether `have` reaches `need`, or None when they cannot be compared."""

    have, need = normalize(language, have), normalize(language, need)
    if have == NATIVE:
        return True
    if need == NATIVE:
        return False
    if have.scale != need.scale:
        return None
    return have.rank >= need.rank


def describe(language: str, level: LanguageLevel) -> str:
    """The level as stated, with what it counts as when that differs."""

    counted = normalize(language, level)
    return level.label if counted == level else f"{level.label} (counted as {counted.label})"


def evaluate(context: RuleContext) -> Finding:
    """Candidate level >= required level, on the same scale."""

    params = context.parameters
    if not isinstance(params, LanguageParams):
        return missing_parameters(context.spec)

    spec = context.spec
    key = language_level_key(params.language)
    answer = known_answer(context.candidate, spec.constraint_id, key)
    if answer is None:
        return missing_answers(spec, key)

    language = params.language.upper()
    key_spec = spec.answer_key(key)
    allowed = key_spec.allowed_values if key_spec is not None else None
    have = LanguageLevel.parse(answer.value) if answer.value in (allowed or ()) else None
    if have is None:
        return unknown(
            UnknownCause.CANDIDATE_MISSING,
            f"{spec.label}: your {language} level '{answer.value}' is not a level "
            "we can compare.",
            candidate=answer.evidence_ids,
            missing=[spec.field_path(key)],
        )

    need = params.required
    reason = (
        f"{language} {describe(params.language, need)} required; "
        f"you have {describe(params.language, have)}."
    )
    result = meets(params.language, have, need)
    if result is None:
        return unknown(
            UnknownCause.POLICY_UNDECIDED,
            f"{reason} Levels on different scales are not compared.",
            candidate=answer.evidence_ids,
        )
    if result:
        return met(reason, answer.evidence_ids)
    return conflict(reason, answer.evidence_ids)
