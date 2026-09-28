"""HC_FIELD_OF_STUDY."""

from __future__ import annotations

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import single

CID = "HC_FIELD_OF_STUDY"
FINANCE_ONLY = {
    "kind": "field_of_study",
    "accepted": ["economics", "finance"],
    "related_accepted": False,
}
FINANCE_OR_RELATED = {**FINANCE_ONLY, "related_accepted": True}


def studied(field: str):
    return b.candidate(answers={(CID, "field_of_study"): field})


def test_accepted_field_is_met() -> None:
    outcome = single(CID, studied("finance"), FINANCE_ONLY)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(CID, "field_of_study")]


def test_unlisted_field_is_conflict() -> None:
    assert single(CID, studied("law"), FINANCE_ONLY).status is RuleStatus.CONFLICT


def test_other_is_conflict_when_only_listed_fields_count() -> None:
    assert single(CID, studied("other"), FINANCE_ONLY).status is RuleStatus.CONFLICT


def test_related_field_clause_leaves_unlisted_fields_undecided() -> None:
    outcome = single(CID, studied("mathematics"), FINANCE_OR_RELATED)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.POLICY_UNDECIDED


def test_listed_field_is_met_even_with_related_clause() -> None:
    assert single(CID, studied("economics"), FINANCE_OR_RELATED).status is RuleStatus.MET


def test_missing_answer_asks_the_candidate() -> None:
    outcome = single(CID, b.candidate(), FINANCE_ONLY)
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_FIELD_OF_STUDY.field_of_study"
    ]


def test_missing_parameters_are_unknown() -> None:
    outcome = single(CID, studied("law"))
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING
