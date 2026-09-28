"""Result envelopes: status vocabulary, UNKNOWN invariants and aggregation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from oi.intelligence.eligibility.models import (
    EligibilityResult,
    EligibilityStatus,
    RuleOutcome,
    RuleStatus,
    UnknownCause,
    aggregate_status,
)

GRAD_PATH = "eligibility_answers.HC_GRAD_WINDOW.expected_graduation_date"


def outcome(status: RuleStatus, **overrides: object) -> RuleOutcome:
    fields: dict[str, object] = {
        "rule_id": "HC_GRAD_WINDOW",
        "status": status,
        "candidate_evidence_ids": [],
        "job_evidence_ids": [],
        "reason": "test",
        "rule_version": "0.1",
    }
    if status is RuleStatus.UNKNOWN:
        fields["unknown_cause"] = UnknownCause.JOB_PARAMETER_MISSING
    fields.update(overrides)
    return RuleOutcome(**fields)


def test_statuses_are_exactly_the_four_official_values() -> None:
    assert [s.value for s in RuleStatus] == [
        "met",
        "conflict",
        "unknown",
        "not_applicable",
    ]


def test_unknown_requires_a_cause() -> None:
    with pytest.raises(ValidationError):
        outcome(RuleStatus.UNKNOWN, unknown_cause=None)


@pytest.mark.parametrize(
    "status", [RuleStatus.MET, RuleStatus.CONFLICT, RuleStatus.NOT_APPLICABLE]
)
def test_only_unknown_carries_a_cause(status: RuleStatus) -> None:
    with pytest.raises(ValidationError):
        outcome(status, unknown_cause=UnknownCause.POLICY_UNDECIDED)


def test_candidate_missing_requires_field_paths() -> None:
    with pytest.raises(ValidationError):
        outcome(RuleStatus.UNKNOWN, unknown_cause=UnknownCause.CANDIDATE_MISSING)

    ok = outcome(
        RuleStatus.UNKNOWN,
        unknown_cause=UnknownCause.CANDIDATE_MISSING,
        missing_field_paths=[GRAD_PATH],
    )
    assert ok.missing_field_paths == [GRAD_PATH]


def test_field_paths_only_for_candidate_missing() -> None:
    with pytest.raises(ValidationError):
        outcome(RuleStatus.UNKNOWN, missing_field_paths=[GRAD_PATH])


def test_field_paths_must_be_approved_candidate_paths() -> None:
    with pytest.raises(ValidationError):
        outcome(
            RuleStatus.UNKNOWN,
            unknown_cause=UnknownCause.CANDIDATE_MISSING,
            missing_field_paths=["education"],
        )


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], EligibilityStatus.ELIGIBLE),
        ([RuleStatus.MET, RuleStatus.NOT_APPLICABLE], EligibilityStatus.ELIGIBLE),
        ([RuleStatus.MET, RuleStatus.UNKNOWN], EligibilityStatus.UNCERTAIN),
        ([RuleStatus.UNKNOWN, RuleStatus.CONFLICT], EligibilityStatus.INELIGIBLE),
        ([RuleStatus.MET, RuleStatus.CONFLICT], EligibilityStatus.INELIGIBLE),
    ],
)
def test_aggregation_conflict_beats_unknown_beats_eligible(
    statuses: list[RuleStatus], expected: EligibilityStatus
) -> None:
    assert aggregate_status([outcome(s) for s in statuses]) is expected


def result(**overrides: object) -> EligibilityResult:
    fields: dict[str, object] = {
        "candidate_id": "c",
        "job_id": "j",
        "catalogue_version": "0.1-internal",
        "status": EligibilityStatus.ELIGIBLE,
        "outcomes": [outcome(RuleStatus.MET)],
        "missing_field_paths": [],
        "warnings": [],
    }
    fields.update(overrides)
    return EligibilityResult(**fields)


def test_result_rejects_status_that_disagrees_with_outcomes() -> None:
    with pytest.raises(ValidationError):
        result(status=EligibilityStatus.INELIGIBLE)


def test_result_rejects_missing_paths_that_disagree_with_outcomes() -> None:
    with pytest.raises(ValidationError):
        result(missing_field_paths=[GRAD_PATH])


def test_result_accepts_consistent_derived_fields() -> None:
    unknown = outcome(
        RuleStatus.UNKNOWN,
        unknown_cause=UnknownCause.CANDIDATE_MISSING,
        missing_field_paths=[GRAD_PATH],
    )
    r = result(
        status=EligibilityStatus.UNCERTAIN,
        outcomes=[outcome(RuleStatus.MET), unknown],
        missing_field_paths=[GRAD_PATH],
    )
    assert r.schema_version == "eligibility-0.1-internal"
