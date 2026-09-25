"""HC_LOCATION: active only with an explicit allowed_country_codes perimeter."""

from __future__ import annotations

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import outcomes_for

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


def test_one_matching_location_among_several_is_met() -> None:
    assert location(["DE"], [("GB", "London"), ("DE", "Berlin")]).status is RuleStatus.MET


def test_all_locations_outside_perimeter_is_conflict() -> None:
    outcome = location(["IT"], [("GB", "London"), ("US", "New York")])
    assert outcome.status is RuleStatus.CONFLICT
    assert outcome.job_evidence_ids == ["ev-job-location-0", "ev-job-location-1"]


@pytest.mark.parametrize("locations", [[], [(None, "Remote")]])
def test_unresolvable_job_country_is_unknown(locations) -> None:
    outcome = location(["IT"], locations)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.JOB_DATA_AMBIGUOUS


def test_outside_resolved_but_one_unresolved_location_is_unknown() -> None:
    outcome = location(["IT"], [("GB", "London"), (None, "Remote")])
    assert outcome.unknown_cause is UnknownCause.JOB_DATA_AMBIGUOUS


def test_inside_resolved_wins_over_unresolved_location() -> None:
    assert location(["IT"], [("IT", "Milan"), (None, "Remote")]).status is RuleStatus.MET


def test_location_does_not_depend_on_a_requirement() -> None:
    # Evaluated from job.locations even when the posting lists no location requirement.
    outcome = location(["IT"], [("GB", "London")], requirements=[])
    assert outcome.status is RuleStatus.CONFLICT
