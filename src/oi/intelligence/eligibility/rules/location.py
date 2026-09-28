"""HC_LOCATION: the location being evaluated is in a country the candidate accepts.

Active only when the candidate declared an explicit country perimeter
(`preferences.allowed_country_codes`). Without one there is nothing to be
incompatible with, so the rule is NOT_APPLICABLE.

The engine evaluates each alternative job location separately and combines
them; this rule only judges the one location it is given.

`allowed_country_codes` carries no evidence IDs in the frozen contract, so
MET and CONFLICT here cite job evidence only.
"""

from __future__ import annotations

from oi.intelligence.eligibility.models import UnknownCause
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    not_applicable,
    unknown,
)


def evaluate(context: RuleContext) -> Finding:
    """The location's country inside the perimeter is MET, outside is CONFLICT."""

    allowed = context.candidate.preferences.allowed_country_codes
    if allowed is None:
        return not_applicable("You have not restricted the countries you would work in.")

    country = context.country_code
    evidence = context.location_evidence_ids
    if country is None:
        return unknown(
            UnknownCause.JOB_DATA_AMBIGUOUS,
            "This location's country could not be resolved.",
            job=evidence,
        )

    perimeter = ", ".join(allowed)
    if country in allowed:
        return met(f"{country} is within your countries ({perimeter}).", job=evidence)
    return conflict(f"{country} is outside your countries ({perimeter}).", job=evidence)
