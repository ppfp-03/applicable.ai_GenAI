"""HC_MIN_EXPERIENCE, by boolean key (D-040) or by months."""

from __future__ import annotations

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import single

CID = "HC_MIN_EXPERIENCE"
CORP_FIN = {"kind": "min_experience", "answer_key": "has_corporate_finance_experience"}
SIX_MONTHS = {"kind": "min_experience", "min_months": 6}


def declares(**answers):
    return b.candidate(answers={(CID, key): value for key, value in answers.items()})


def test_approved_boolean_key_true_is_met() -> None:
    outcome = single(CID, declares(has_corporate_finance_experience=True), CORP_FIN)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [
        b.answer_evidence_id(CID, "has_corporate_finance_experience")
    ]


def test_approved_boolean_key_false_is_conflict() -> None:
    outcome = single(CID, declares(has_corporate_finance_experience=False), CORP_FIN)
    assert outcome.status is RuleStatus.CONFLICT


def test_missing_boolean_answer_uses_the_d040_path() -> None:
    outcome = single(CID, b.candidate(), CORP_FIN)
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_MIN_EXPERIENCE.has_corporate_finance_experience"
    ]


@pytest.mark.parametrize(("months", "expected"), [(6, RuleStatus.MET), (12, RuleStatus.MET), (5, RuleStatus.CONFLICT), (0, RuleStatus.CONFLICT)])
def test_months_against_minimum(months: int, expected: RuleStatus) -> None:
    assert single(CID, declares(prior_experience_months=months), SIX_MONTHS).status is expected


def test_boolean_key_does_not_satisfy_a_months_minimum() -> None:
    outcome = single(CID, declares(has_corporate_finance_experience=True), SIX_MONTHS)
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_MIN_EXPERIENCE.prior_experience_months"
    ]


def test_missing_parameters_are_unknown() -> None:
    outcome = single(CID, declares(prior_experience_months=0))
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING
