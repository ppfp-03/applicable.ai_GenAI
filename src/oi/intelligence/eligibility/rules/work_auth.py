"""HC_WORK_AUTH: the candidate may work in the job's country.

Evaluated only when the job explicitly states a work-authorization requirement
(the engine returns NOT_APPLICABLE otherwise). It reads the candidate's
country-specific declaration and nothing else: citizenship is never treated as
work authorization, and no legal status is inferred.

| authorized_to_work | requires_sponsorship | employer_sponsorship | outcome       |
|--------------------|----------------------|----------------------|---------------|
| true               | any                  | any                  | MET           |
| false / null       | true                 | offered              | MET           |
| false / null       | true                 | not_offered          | CONFLICT      |
| false / null       | true                 | not_stated / none    | UNKNOWN (job) |
| false              | false                | any                  | UNKNOWN (ask) |
| null               | false                | any                  | UNKNOWN (ask) |
| false / null       | null                 | any                  | UNKNOWN (ask) |
| no declaration     |                      |                      | UNKNOWN (ask) |
"""

from __future__ import annotations

from oi.intelligence.eligibility.inputs import job_countries, work_authorization
from oi.intelligence.eligibility.models import UnknownCause
from oi.intelligence.eligibility.parameters import WorkAuthParams
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    unknown,
)


def _path(country: str, leaf: str) -> str:
    return f"declarations.work_authorizations.{country}.{leaf}"


def _ask(country: str, reason: str, leaves: list[str], evidence=()) -> Finding:
    return unknown(
        UnknownCause.CANDIDATE_MISSING,
        reason,
        evidence,
        missing=[_path(country, leaf) for leaf in leaves],
    )


def _country(context: RuleContext) -> tuple[str | None, list[str]]:
    """The parameter's country, else the job's single resolved country."""

    params = context.parameters
    if isinstance(params, WorkAuthParams) and params.country_code is not None:
        return params.country_code, []
    countries = job_countries(context.job)
    if len(countries.codes) == 1 and not countries.has_unresolved:
        return countries.codes[0], countries.evidence_ids
    return None, countries.evidence_ids


def evaluate(context: RuleContext) -> Finding:
    """Apply the declaration table above for the job's country."""

    country, location_evidence = _country(context)
    if country is None:
        return unknown(
            UnknownCause.JOB_DATA_AMBIGUOUS,
            "The posting requires work authorization, but not for one clear country.",
            job=location_evidence,
        )

    declaration = work_authorization(context.candidate, country)
    if declaration is None:
        return _ask(
            country,
            f"You have not told us whether you can work in {country}.",
            ["authorized_to_work", "requires_sponsorship"],
        )

    evidence = declaration.evidence_ids
    authorized = declaration.authorized_to_work
    sponsorship = declaration.requires_sponsorship

    if authorized is True:
        return met(f"You declared you can work in {country}.", evidence, location_evidence)

    if sponsorship is None:
        leaves = ["requires_sponsorship"]
        if authorized is None:
            leaves.insert(0, "authorized_to_work")
        return _ask(
            country,
            f"Whether you need visa sponsorship for {country} is not stated.",
            leaves,
            evidence,
        )

    if sponsorship is False:
        # Not authorized (or not stated) yet needing no sponsorship: the pair
        # does not settle anything, so ask rather than pick a reading.
        return _ask(
            country,
            f"Your {country} declaration does not say whether you can work there.",
            ["authorized_to_work"],
            evidence,
        )

    policy = (
        context.parameters.employer_sponsorship
        if isinstance(context.parameters, WorkAuthParams)
        else "not_stated"
    )
    if policy == "offered":
        return met(
            f"You need sponsorship for {country}, and this employer offers it.",
            evidence,
            location_evidence,
        )
    if policy == "not_offered":
        return conflict(
            f"You need sponsorship for {country}, and this employer does not offer it.",
            evidence,
            location_evidence,
        )
    return unknown(
        UnknownCause.JOB_PARAMETER_MISSING,
        f"You need sponsorship for {country}; the posting does not say whether "
        "the employer sponsors.",
        evidence,
        location_evidence,
    )
