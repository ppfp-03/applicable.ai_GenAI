"""HC_LOCATION: active only with an explicit allowed_country_codes perimeter."""

from __future__ import annotations

import pytest

from oi.intelligence.eligibility import (
    EligibilityStatus,
    RuleStatus,
    UnknownCause,
    assess_eligibility,
)

from . import builders as b
from .rule_helpers import CATALOGUE, outcomes_for

CID = "HC_LOCATION"


def location(allowed, locations, requirements=()):
    job = b.job(locations=locations, requirements=requirements)
    (outcome,) = outcomes_for(CID, b.candidate(allowed_countries=allowed), job)
    return outcome


def test_no_perimeter_is_not_applicable() -> None:
    outcome = location(None, [("US", "New York")])
    assert outcome.status is RuleStatus.NOT_APPLICABLE
    assert outcome.requirement_id is None


def test_job_country_inside_perimeter_is_met() -> None:
    outcome = location(["IT", "NL"], [("NL", "Amsterdam")])
    assert outcome.status is RuleStatus.MET
    assert outcome.job_evidence_ids == ["ev-job-location-0"]
    assert outcome.candidate_evidence_ids == []


def per_location(allowed, locations):
    """{location_key: HC_LOCATION status} plus the job's aggregate status."""

    job = b.job(locations=locations)
    result = assess_eligibility(
        b.candidate(allowed_countries=allowed), job, CATALOGUE
    )
    statuses = {o.location_key: o.status for o in result.outcomes if o.rule_id == CID}
    return statuses, result.status


def test_each_location_is_judged_on_its_own_country() -> None:
    statuses, overall = per_location(["DE"], [("GB", "London"), ("DE", "Berlin")])
    assert statuses == {"DE": RuleStatus.MET, "GB": RuleStatus.CONFLICT}
    assert overall is EligibilityStatus.ELIGIBLE


def test_all_locations_outside_perimeter_is_conflict_everywhere() -> None:
    statuses, overall = per_location(["IT"], [("GB", "London"), ("US", "New York")])
    assert statuses == {"GB": RuleStatus.CONFLICT, "US": RuleStatus.CONFLICT}
    assert overall is EligibilityStatus.INELIGIBLE


def test_a_location_cites_only_its_own_evidence() -> None:
    job = b.job(locations=[("GB", "London"), ("US", "New York")])
    outcomes = outcomes_for(CID, b.candidate(allowed_countries=["IT"]), job)
    assert [(o.location_key, o.job_evidence_ids) for o in outcomes] == [
        ("GB", ["ev-job-location-0"]),
        ("US", ["ev-job-location-1"]),
    ]


@pytest.mark.parametrize("locations", [[], [(None, "Remote")]])
def test_unresolvable_job_country_is_unknown(locations) -> None:
    outcome = location(["IT"], locations)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.JOB_DATA_AMBIGUOUS
    assert outcome.location_key == "unresolved"


def test_outside_resolved_but_one_unresolved_location_is_uncertain() -> None:
    statuses, overall = per_location(["IT"], [("GB", "London"), (None, "Remote")])
    assert statuses == {"GB": RuleStatus.CONFLICT, "unresolved": RuleStatus.UNKNOWN}
    assert overall is EligibilityStatus.UNCERTAIN


def test_inside_resolved_wins_over_unresolved_location() -> None:
    statuses, overall = per_location(["IT"], [("IT", "Milan"), (None, "Remote")])
    assert statuses == {"IT": RuleStatus.MET, "unresolved": RuleStatus.UNKNOWN}
    assert overall is EligibilityStatus.ELIGIBLE


def test_location_does_not_depend_on_a_requirement() -> None:
    # Evaluated from job.locations even when the posting lists no location requirement.
    outcome = location(["IT"], [("GB", "London")], requirements=[])
    assert outcome.status is RuleStatus.CONFLICT
