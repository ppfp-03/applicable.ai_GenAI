"""HC_GRAD_WINDOW."""

from __future__ import annotations

from datetime import date

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import single

CID = "HC_GRAD_WINDOW"
KEY = (CID, "expected_graduation_date")
WINDOW = {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}


def grad(value: date):
    return b.candidate(answers={KEY: value})


@pytest.mark.parametrize("day", [date(2027, 1, 1), date(2027, 7, 15), date(2027, 12, 31)])
def test_inside_window_including_both_ends_is_met(day: date) -> None:
    outcome = single(CID, grad(day), WINDOW)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(*KEY)]
    assert outcome.job_evidence_ids == ["ev-job-req-1"]


@pytest.mark.parametrize("day", [date(2026, 12, 31), date(2028, 1, 1)])
def test_outside_window_is_conflict(day: date) -> None:
    assert single(CID, grad(day), WINDOW).status is RuleStatus.CONFLICT


def test_missing_date_asks_the_candidate() -> None:
    outcome = single(CID, b.candidate(), WINDOW)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_GRAD_WINDOW.expected_graduation_date"
    ]


def test_unknown_state_answer_asks_the_candidate() -> None:
    candidate = b.candidate(unknown_answers=[(*KEY, "date")])
    assert single(CID, candidate, WINDOW).unknown_cause is UnknownCause.CANDIDATE_MISSING


def test_missing_window_is_unknown_not_conflict() -> None:
    outcome = single(CID, grad(date(2030, 1, 1)))
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING
    assert outcome.missing_field_paths == []


def test_unspecified_modality_softens_the_conflict() -> None:
    outcome = single(CID, grad(date(2030, 1, 1)), WINDOW, modality="unspecified")
    assert outcome.unknown_cause is UnknownCause.NON_MANDATORY_MISMATCH


def test_preferred_window_is_not_applicable() -> None:
    outcome = single(CID, grad(date(2030, 1, 1)), WINDOW, modality="preferred")
    assert outcome.status is RuleStatus.NOT_APPLICABLE
