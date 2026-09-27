"""Unresolved job evidence is reported, never silently dropped.

Regression for acceptance T-019 / FR-06: an evidence ID that does not resolve
in job.evidence used to disappear from outcomes with no warning. It is still
not cited (nothing may be cited that a reader cannot open), but each one now
raises an UNRESOLVED_EVIDENCE warning. Warnings never change the status.
"""

from __future__ import annotations

from datetime import date

from oi.contracts import JobRecord
from oi.intelligence.eligibility import (
    EligibilityStatus,
    WarningCode,
    assess_eligibility,
    load_rule_catalogue,
)
from oi.intelligence.eligibility.inputs import unresolved_evidence_warnings

from . import builders as b

CATALOGUE = load_rule_catalogue()
GRAD_PARAMS = {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}
NO_SPONSORSHIP = {"kind": "work_auth", "employer_sponsorship": "not_offered"}


def with_dangling(job: JobRecord, *, requirement: int | None = None, location: int | None = None) -> JobRecord:
    """The same job with 'ev-dangling' added to one requirement or location."""

    data = job.model_dump(mode="json")
    if requirement is not None:
        data["facts"]["requirements"][requirement]["evidence_ids"].append("ev-dangling")
    if location is not None:
        data["locations"][location]["evidence_ids"].append("ev-dangling")
    return JobRecord.model_validate(data)


def unresolved(result):
    return [w for w in result.warnings if w.code is WarningCode.UNRESOLVED_EVIDENCE]


def cited(result) -> set[str]:
    return {eid for outcome in result.outcomes for eid in outcome.job_evidence_ids}


def grad_job(**locations):
    return b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")], **locations)


def assess(candidate, job, layer=None):
    layer = layer or b.parameters(("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS))
    return assess_eligibility(candidate, job, CATALOGUE, job_parameters=layer)


GRADUATE = b.candidate(
    answers={("HC_GRAD_WINDOW", "expected_graduation_date"): date(2027, 7, 15)}
)


def test_dangling_requirement_evidence_produces_a_warning() -> None:
    result = assess(GRADUATE, with_dangling(grad_job(), requirement=0))
    (warning,) = unresolved(result)
    assert warning.evidence_id == "ev-dangling"
    assert warning.requirement_id == "req-1"
    assert warning.constraint_id == "HC_GRAD_WINDOW"
    assert "ev-dangling" not in cited(result)


def test_dangling_location_evidence_produces_a_warning() -> None:
    result = assess(GRADUATE, with_dangling(grad_job(), location=0))
    (warning,) = unresolved(result)
    assert warning.evidence_id == "ev-dangling"
    assert warning.requirement_id is None
    assert "ev-dangling" not in cited(result)


def test_multiple_locations_do_not_duplicate_warnings() -> None:
    job = b.job(
        locations=[("GB", "London"), ("NL", "Amsterdam")],
        requirements=[
            ("req-1", "HC_GRAD_WINDOW", "mandatory"),
            ("r-auth", "HC_WORK_AUTH", "mandatory"),
        ],
    )
    job = with_dangling(job, requirement=0)
    layer = b.parameters(
        ("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS),
        ("r-auth", "HC_WORK_AUTH", NO_SPONSORSHIP),
    )
    result = assess(GRADUATE, job, layer)
    assert len(result.locations) == 2
    assert [(w.requirement_id, w.evidence_id) for w in unresolved(result)] == [
        ("req-1", "ev-dangling")
    ]


def test_each_dangling_reference_is_reported_once() -> None:
    job = with_dangling(with_dangling(grad_job(), requirement=0, location=0), requirement=0)
    warnings = unresolved_evidence_warnings(job)
    # The repeated requirement reference counts once; the location one separately.
    assert [(w.requirement_id, w.evidence_id) for w in warnings] == [
        ("req-1", "ev-dangling"),
        (None, "ev-dangling"),
    ]


def test_valid_evidence_produces_no_warning() -> None:
    job = b.job(
        locations=[("GB", "London"), ("NL", "Amsterdam")],
        requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")],
    )
    assert unresolved_evidence_warnings(job) == []
    assert unresolved(assess(GRADUATE, job)) == []


def test_status_and_outcomes_are_unchanged_by_dangling_evidence() -> None:
    cases = [
        (GRADUATE, EligibilityStatus.ELIGIBLE),
        (
            b.candidate(answers={("HC_GRAD_WINDOW", "expected_graduation_date"): date(2030, 1, 1)}),
            EligibilityStatus.INELIGIBLE,
        ),
        (b.candidate(), EligibilityStatus.UNCERTAIN),
    ]
    for candidate, expected in cases:
        clean = assess(candidate, grad_job())
        dirty = assess(candidate, with_dangling(grad_job(), requirement=0, location=0))
        assert clean.status is dirty.status is expected
        assert clean.outcomes == dirty.outcomes
        assert clean.missing_field_paths == dirty.missing_field_paths
        assert unresolved(clean) == []
        assert len(unresolved(dirty)) == 2


def test_unsupported_requirement_evidence_is_also_checked() -> None:
    # The engine reads every hard-constraint requirement, catalogued or not.
    job = with_dangling(
        b.job(requirements=[("req-x", "work_authorization_nl", "mandatory")]), requirement=0
    )
    result = assess_eligibility(GRADUATE, job, CATALOGUE)
    codes = sorted(w.code.value for w in result.warnings)
    assert codes == ["unresolved_evidence", "unsupported_constraint"]
    assert result.status is EligibilityStatus.ELIGIBLE
