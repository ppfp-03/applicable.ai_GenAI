"""Alternative job locations are evaluated one by one, then combined.

Regression for acceptance T-014 / T-015: a job offered in GB or NL used to get
one job-level HC_WORK_AUTH outcome, UNKNOWN (job_data_ambiguous), before any
declaration was read. PROJECT_CONTEXT "Eligibility aggregation": every rule is
evaluated per location; one compatible location makes the job eligible,
otherwise one uncertain location makes it uncertain, and only all-incompatible
locations make it ineligible.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from oi.intelligence.eligibility import (
    EligibilityStatus,
    RuleStatus,
    UnknownCause,
    assess_eligibility,
    load_rule_catalogue,
)
from oi.intelligence.eligibility.models import EligibilityResult

from . import builders as b

CATALOGUE = load_rule_catalogue()
GB_OR_NL = [("GB", "London"), ("NL", "Amsterdam")]
NO_SPONSORSHIP = {"kind": "work_auth", "employer_sponsorship": "not_offered"}

# (authorized_to_work, requires_sponsorship) per country, against an employer
# that does not sponsor: authorized -> compatible, needs sponsorship ->
# incompatible, undeclared -> uncertain.
COMPATIBLE = (True, False)
INCOMPATIBLE = (False, True)


def work_auth_job():
    return b.job(locations=GB_OR_NL, requirements=[("r-auth", "HC_WORK_AUTH", "mandatory")])


def assess(candidate, job=None, layer=None):
    job = job or work_auth_job()
    layer = layer or b.parameters(("r-auth", "HC_WORK_AUTH", NO_SPONSORSHIP))
    return assess_eligibility(candidate, job, CATALOGUE, job_parameters=layer)


def declarations(**by_country):
    return [(country, *facts) for country, facts in by_country.items()]


def location_statuses(result):
    return {location.location_key: location.status for location in result.locations}


# ── The three required regressions ──


def test_gb_compatible_nl_incompatible_is_eligible() -> None:
    candidate = b.candidate(work_auth=declarations(GB=COMPATIBLE, NL=INCOMPATIBLE))
    result = assess(candidate)
    assert location_statuses(result) == {
        "GB": EligibilityStatus.ELIGIBLE,
        "NL": EligibilityStatus.INELIGIBLE,
    }
    assert result.status is EligibilityStatus.ELIGIBLE


def test_gb_incompatible_nl_incompatible_is_ineligible() -> None:
    candidate = b.candidate(work_auth=declarations(GB=INCOMPATIBLE, NL=INCOMPATIBLE))
    result = assess(candidate)
    assert location_statuses(result) == {
        "GB": EligibilityStatus.INELIGIBLE,
        "NL": EligibilityStatus.INELIGIBLE,
    }
    assert result.status is EligibilityStatus.INELIGIBLE


def test_gb_uncertain_nl_incompatible_is_uncertain() -> None:
    # Nothing declared for GB: that location cannot be decided either way.
    candidate = b.candidate(work_auth=declarations(NL=INCOMPATIBLE))
    result = assess(candidate)
    assert location_statuses(result) == {
        "GB": EligibilityStatus.UNCERTAIN,
        "NL": EligibilityStatus.INELIGIBLE,
    }
    assert result.status is EligibilityStatus.UNCERTAIN
    gb_auth = next(
        o for o in result.outcomes if o.location_key == "GB" and o.rule_id == "HC_WORK_AUTH"
    )
    assert gb_auth.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert result.missing_field_paths == [
        "declarations.work_authorizations.GB.authorized_to_work",
        "declarations.work_authorizations.GB.requires_sponsorship",
    ]


# ── Supporting behaviour ──


def test_work_auth_is_no_longer_job_level_ambiguous() -> None:
    candidate = b.candidate(work_auth=declarations(GB=COMPATIBLE, NL=INCOMPATIBLE))
    auth = [o for o in assess(candidate).outcomes if o.rule_id == "HC_WORK_AUTH"]
    assert [(o.location_key, o.status) for o in auth] == [
        ("GB", RuleStatus.MET),
        ("NL", RuleStatus.CONFLICT),
    ]
    assert all(o.unknown_cause is not UnknownCause.JOB_DATA_AMBIGUOUS for o in auth)


def test_citizenship_does_not_make_a_location_compatible() -> None:
    candidate = b.candidate(
        work_auth=declarations(NL=INCOMPATIBLE), citizenships=["GB"]
    )
    result = assess(candidate)
    assert location_statuses(result)["GB"] is EligibilityStatus.UNCERTAIN
    assert result.status is EligibilityStatus.UNCERTAIN


def test_every_constraint_is_evaluated_for_every_location() -> None:
    candidate = b.candidate(work_auth=declarations(GB=COMPATIBLE, NL=COMPATIBLE))
    result = assess(candidate)
    for location in result.locations:
        assert [o.rule_id for o in location.outcomes] == CATALOGUE.constraint_ids
    assert len(result.outcomes) == 2 * len(CATALOGUE.constraint_ids)


def test_location_and_work_auth_combine_within_a_location() -> None:
    # GB is authorized but outside the perimeter; NL is inside but needs
    # sponsorship that is not offered. No location passes every rule.
    candidate = b.candidate(
        allowed_countries=["NL"],
        work_auth=declarations(GB=COMPATIBLE, NL=INCOMPATIBLE),
    )
    result = assess(candidate)
    assert location_statuses(result) == {
        "GB": EligibilityStatus.INELIGIBLE,
        "NL": EligibilityStatus.INELIGIBLE,
    }
    assert result.status is EligibilityStatus.INELIGIBLE


def test_a_location_independent_conflict_excludes_every_location() -> None:
    job = b.job(
        locations=GB_OR_NL,
        requirements=[
            ("r-auth", "HC_WORK_AUTH", "mandatory"),
            ("r-grad", "HC_GRAD_WINDOW", "mandatory"),
        ],
    )
    layer = b.parameters(
        ("r-auth", "HC_WORK_AUTH", NO_SPONSORSHIP),
        ("r-grad", "HC_GRAD_WINDOW", {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}),
    )
    candidate = b.candidate(
        work_auth=declarations(GB=COMPATIBLE, NL=COMPATIBLE),
        answers={("HC_GRAD_WINDOW", "expected_graduation_date"): date(2029, 7, 1)},
    )
    result = assess(candidate, job, layer)
    assert set(location_statuses(result).values()) == {EligibilityStatus.INELIGIBLE}
    assert result.status is EligibilityStatus.INELIGIBLE


def test_same_country_locations_are_one_alternative() -> None:
    job = b.job(
        locations=[("GB", "London"), ("GB", "Edinburgh")],
        requirements=[("r-auth", "HC_WORK_AUTH", "mandatory")],
    )
    result = assess(b.candidate(work_auth=declarations(GB=COMPATIBLE)), job)
    assert [location.location_key for location in result.locations] == ["GB"]
    auth = next(o for o in result.outcomes if o.rule_id == "HC_WORK_AUTH")
    assert auth.job_evidence_ids[-2:] == ["ev-job-location-0", "ev-job-location-1"]


def test_parameter_warnings_are_reported_once_across_locations() -> None:
    layer = b.parameters(("r-auth", "HC_WORK_AUTH", {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}))
    result = assess(b.candidate(), layer=layer)
    assert len(result.warnings) == 1


def test_result_rejects_status_that_disagrees_with_locations() -> None:
    candidate = b.candidate(work_auth=declarations(GB=COMPATIBLE, NL=INCOMPATIBLE))
    data = assess(candidate).model_dump(mode="json")
    data["status"] = "ineligible"
    with pytest.raises(ValidationError, match="locations"):
        EligibilityResult.model_validate(data)


def test_result_rejects_outcomes_that_are_not_the_locations_outcomes() -> None:
    candidate = b.candidate(work_auth=declarations(GB=COMPATIBLE, NL=INCOMPATIBLE))
    data = assess(candidate).model_dump(mode="json")
    data["outcomes"] = data["outcomes"][:-1]
    with pytest.raises(ValidationError, match="outcomes"):
        EligibilityResult.model_validate(data)
