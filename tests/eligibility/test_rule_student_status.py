"""HC_STUDENT_STATUS."""

from __future__ import annotations

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import single

CID = "HC_STUDENT_STATUS"
STUDENTS_OR_GRADUATES = {
    "kind": "student_status",
    "accepted": ["enrolled_student", "recent_graduate"],
}


def status(value: str):
    return b.candidate(answers={(CID, "current_status"): value})


@pytest.mark.parametrize("value", ["enrolled_student", "recent_graduate"])
def test_accepted_status_is_met(value: str) -> None:
    outcome = single(CID, status(value), STUDENTS_OR_GRADUATES)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(CID, "current_status")]


def test_other_status_is_conflict() -> None:
    assert single(CID, status("neither"), STUDENTS_OR_GRADUATES).status is (
        RuleStatus.CONFLICT
    )


def test_students_only_excludes_graduates() -> None:
    params = {"kind": "student_status", "accepted": ["enrolled_student"]}
    assert single(CID, status("recent_graduate"), params).status is RuleStatus.CONFLICT


def test_missing_answer_asks_the_candidate() -> None:
    outcome = single(CID, b.candidate(), STUDENTS_OR_GRADUATES)
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_STUDENT_STATUS.current_status"
    ]


def test_missing_parameters_are_unknown() -> None:
    outcome = single(CID, status("neither"))
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING
