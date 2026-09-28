"""HC_DEGREE_LEVEL, including the configurable in-progress policy."""

from __future__ import annotations

import copy

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause, assess_eligibility
from oi.intelligence.eligibility.catalogue import RuleCatalogue

from . import builders as b
from .rule_helpers import CATALOGUE, single

CID = "HC_DEGREE_LEVEL"
BACHELOR = {"kind": "degree_level", "min_level": "bachelor"}
MASTER = {"kind": "degree_level", "min_level": "master"}


def degree(level: str | None = None, status: str | None = None):
    answers = {}
    if level:
        answers[(CID, "degree_level")] = level
    if status:
        answers[(CID, "degree_status")] = status
    return b.candidate(answers=answers)


@pytest.mark.parametrize("level", ["master", "phd"])
def test_completed_at_or_above_minimum_is_met(level: str) -> None:
    outcome = single(CID, degree(level, "completed"), MASTER)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [
        b.answer_evidence_id(CID, "degree_level"),
        b.answer_evidence_id(CID, "degree_status"),
    ]


@pytest.mark.parametrize("status", ["completed", "in_progress", None])
def test_below_minimum_is_conflict_whatever_the_status(status) -> None:
    assert single(CID, degree("bachelor", status), MASTER).status is RuleStatus.CONFLICT


def test_in_progress_defaults_to_undecided() -> None:
    outcome = single(CID, degree("bachelor", "in_progress"), BACHELOR)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.POLICY_UNDECIDED


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        ("counts", RuleStatus.MET),
        ("does_not_count", RuleStatus.CONFLICT),
        ("undecided", RuleStatus.UNKNOWN),
    ],
)
def test_per_job_policy_override(policy: str, expected: RuleStatus) -> None:
    params = {**BACHELOR, "in_progress_policy": policy}
    assert single(CID, degree("bachelor", "in_progress"), params).status is expected


def catalogue_with_policy(policy: str) -> RuleCatalogue:
    data = copy.deepcopy(CATALOGUE.model_dump(mode="json"))
    spec = next(c for c in data["constraints"] if c["constraint_id"] == CID)
    spec["settings"]["in_progress_policy"] = policy
    return RuleCatalogue.model_validate(data)


def _degree_outcome(catalogue: RuleCatalogue, params: dict):
    job = b.job(requirements=[("req-1", CID, "mandatory")])
    result = assess_eligibility(
        degree("bachelor", "in_progress"),
        job,
        catalogue,
        job_parameters=b.parameters(("req-1", CID, params)),
    )
    return next(o for o in result.outcomes if o.rule_id == CID)


def test_catalogue_setting_changes_the_default() -> None:
    outcome = _degree_outcome(catalogue_with_policy("counts"), BACHELOR)
    assert outcome.status is RuleStatus.MET


def test_job_override_beats_catalogue_setting() -> None:
    params = {**BACHELOR, "in_progress_policy": "does_not_count"}
    outcome = _degree_outcome(catalogue_with_policy("counts"), params)
    assert outcome.status is RuleStatus.CONFLICT


def test_missing_level_asks_for_both_answers() -> None:
    outcome = single(CID, degree(), BACHELOR)
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_DEGREE_LEVEL.degree_level",
        "eligibility_answers.HC_DEGREE_LEVEL.degree_status",
    ]


def test_sufficient_level_without_status_asks_for_status() -> None:
    outcome = single(CID, degree("master"), BACHELOR)
    assert outcome.missing_field_paths == [
        "eligibility_answers.HC_DEGREE_LEVEL.degree_status"
    ]


def test_missing_parameters_are_unknown() -> None:
    outcome = single(CID, degree("bachelor", "completed"))
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING
