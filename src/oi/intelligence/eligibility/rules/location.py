"""HC_LOCATION: the job is in a country the candidate said they accept.

Active only when the candidate declared an explicit country perimeter
(`preferences.allowed_country_codes`). Without one there is nothing to be
incompatible with, so the rule is NOT_APPLICABLE.

`allowed_country_codes` carries no evidence IDs in the frozen contract, so
MET and CONFLICT here cite job evidence only.
"""

from __future__ import annotations

from oi.intelligence.eligibility.inputs import job_countries
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
    """Any job country inside the perimeter is MET; all outside is CONFLICT."""

    allowed = context.candidate.preferences.allowed_country_codes
    if allowed is None:
        return not_applicable("You have not restricted the countries you would work in.")

    countries = job_countries(context.job)
    if not countries.codes:
        return unknown(
            UnknownCause.JOB_DATA_AMBIGUOUS,
            "The posting's country could not be resolved.",
            job=countries.evidence_ids,
        )

    perimeter = ", ".join(allowed)
    inside = [code for code in countries.codes if code in allowed]
    if inside:
        return met(
            f"The role is in {', '.join(inside)}, within your countries ({perimeter}).",
            job=countries.evidence_ids,
        )

    listed = ", ".join(countries.codes)
    if countries.has_unresolved:
        return unknown(
            UnknownCause.JOB_DATA_AMBIGUOUS,
            f"The resolved locations ({listed}) are outside your countries "
            f"({perimeter}), but at least one location has no country.",
            job=countries.evidence_ids,
        )
    return conflict(
        f"The role is in {listed}, outside your countries ({perimeter}).",
        job=countries.evidence_ids,
    )
