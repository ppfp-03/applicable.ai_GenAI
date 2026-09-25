"""Read-only accessors over the frozen contracts and the parameter layer."""

from __future__ import annotations

from datetime import date

import pytest

from oi.contracts import CandidateProfile
from oi.intelligence.eligibility.catalogue import load_rule_catalogue
from oi.intelligence.eligibility.inputs import (
    answer_key_warnings,
    hard_requirements,
    job_countries,
    known_answer,
    orphan_parameter_warnings,
    resolvable_job_evidence,
    resolve_parameters,
    work_authorization,
)
from oi.intelligence.eligibility.models import WarningCode

from . import builders as b

CATALOGUE = load_rule_catalogue()
GRAD = ("HC_GRAD_WINDOW", "expected_graduation_date")
GRAD_PARAMS = {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}


def spec(constraint_id: str):
    found = CATALOGUE.get(constraint_id)
    assert found is not None
    return found


# ── candidate side ──


def test_known_answer_returns_the_value() -> None:
    c = b.candidate(answers={GRAD: date(2027, 7, 15)})
    answer = known_answer(c, *GRAD)
    assert answer is not None and answer.value == date(2027, 7, 15)


def test_unknown_state_counts_as_missing() -> None:
    c = b.candidate(unknown_answers=[(*GRAD, "date")])
    assert known_answer(c, *GRAD) is None


def test_absent_answer_is_missing() -> None:
    assert known_answer(b.candidate(), *GRAD) is None


def test_conflicting_duplicate_answers_are_not_used() -> None:
    c = b.candidate(answers={GRAD: date(2027, 7, 15)})
    data = c.model_dump(mode="json")
    duplicate = dict(data["eligibility_answers"]["HC_GRAD_WINDOW"][0], value="2028-01-01")
    data["eligibility_answers"]["HC_GRAD_WINDOW"].append(duplicate)
    assert known_answer(CandidateProfile.model_validate(data), *GRAD) is None


def test_work_authorization_is_looked_up_by_country_only() -> None:
    c = b.candidate(work_auth=[("NL", True, False)], citizenships=["IT"])
    assert work_authorization(c, "NL") is not None
    # Italian citizenship is declared, but it is not an IT work declaration.
    assert work_authorization(c, "IT") is None


def test_answers_outside_the_catalogue_raise_warnings() -> None:
    c = b.candidate(
        answers={
            ("graduation_window", "expected_graduation_date"): date(2027, 7, 15),
            ("HC_GRAD_WINDOW", "graduation_year"): 2027,
            GRAD: date(2027, 7, 15),
        }
    )
    warnings = answer_key_warnings(c, CATALOGUE)
    assert [w.code for w in warnings] == [WarningCode.UNKNOWN_ANSWER_KEY] * 2
    assert {w.constraint_id for w in warnings} == {"graduation_window", "HC_GRAD_WINDOW"}


# ── job side ──


def test_job_countries_are_distinct_and_sorted() -> None:
    j = b.job(locations=[("NL", "Amsterdam"), ("DE", "Berlin"), ("NL", "Utrecht")])
    countries = job_countries(j)
    assert countries.codes == ["DE", "NL"]
    assert not countries.has_unresolved
    assert len(countries.evidence_ids) == 3


@pytest.mark.parametrize(
    "locations", [[], [(None, "Remote")], [("NL", "Amsterdam"), (None, "Remote")]]
)
def test_missing_country_is_flagged_unresolved(locations) -> None:
    assert job_countries(b.job(locations=locations)).has_unresolved


def test_hard_requirements_skip_fit_and_sort_by_id() -> None:
    j = b.job(
        requirements=[
            ("req-2", "HC_LANGUAGE", "mandatory"),
            ("req-1", "HC_GRAD_WINDOW", "mandatory"),
            ("req-3", None, "preferred", "fit"),
        ]
    )
    assert [r.requirement_id for r in hard_requirements(j)] == ["req-1", "req-2"]


def test_only_resolvable_job_evidence_is_cited() -> None:
    j = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")])
    ids = ["ev-job-req-1", "ev-missing", "ev-job-req-1"]
    assert resolvable_job_evidence(j, ids) == ["ev-job-req-1"]


# ── parameter layer ──


def _req(j, requirement_id="req-1"):
    return next(r for r in hard_requirements(j) if r.requirement_id == requirement_id)


def test_resolve_returns_parameters_and_their_evidence() -> None:
    j = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")])
    layer = b.parameters(("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS))
    resolved = resolve_parameters(j, _req(j), spec("HC_GRAD_WINDOW"), layer)
    assert resolved.parameters is not None
    assert resolved.evidence_ids == ["ev-job-req-1"]
    assert resolved.warnings == []


def test_absent_entry_is_silent() -> None:
    j = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")])
    for layer in (None, b.parameters()):
        resolved = resolve_parameters(j, _req(j), spec("HC_GRAD_WINDOW"), layer)
        assert resolved.parameters is None and resolved.warnings == []


@pytest.mark.parametrize(
    ("constraint_id", "requirement_constraint", "params", "evidence"),
    [
        # Entry filed under another constraint.
        ("HC_LANGUAGE", "HC_GRAD_WINDOW", GRAD_PARAMS, None),
        # Kind does not match the constraint.
        (
            "HC_GRAD_WINDOW",
            "HC_GRAD_WINDOW",
            {"kind": "degree_level", "min_level": "master"},
            None,
        ),
        # Evidence does not resolve in the job.
        ("HC_GRAD_WINDOW", "HC_GRAD_WINDOW", GRAD_PARAMS, ["ev-nowhere"]),
        # Language without an answer key.
        (
            "HC_LANGUAGE",
            "HC_LANGUAGE",
            {"kind": "language", "language": "ja", "min_level": "B2"},
            None,
        ),
        # Field outside the vocabulary.
        (
            "HC_FIELD_OF_STUDY",
            "HC_FIELD_OF_STUDY",
            {"kind": "field_of_study", "accepted": ["astrology"], "related_accepted": False},
            None,
        ),
        # Experience key that is not a boolean key of the constraint.
        (
            "HC_MIN_EXPERIENCE",
            "HC_MIN_EXPERIENCE",
            {"kind": "min_experience", "answer_key": "prior_experience_months"},
            None,
        ),
    ],
)
def test_unusable_entries_are_ignored_with_a_warning(
    constraint_id, requirement_constraint, params, evidence
) -> None:
    j = b.job(requirements=[("req-1", requirement_constraint, "mandatory")])
    layer = b.parameters(("req-1", constraint_id, params), evidence_ids=evidence)
    resolved = resolve_parameters(j, _req(j), spec(requirement_constraint), layer)
    assert resolved.parameters is None
    assert [w.code for w in resolved.warnings] == [WarningCode.INVALID_JOB_PARAMETER]


def test_entries_without_a_matching_hard_requirement_are_orphans() -> None:
    j = b.job(
        requirements=[
            ("req-1", "HC_GRAD_WINDOW", "mandatory"),
            ("req-2", None, "preferred", "fit"),
        ]
    )
    layer = b.parameters(
        ("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS),
        ("req-2", "HC_GRAD_WINDOW", GRAD_PARAMS),
        ("req-9", "HC_GRAD_WINDOW", GRAD_PARAMS),
        evidence_ids=["ev-job-req-1"],
    )
    warnings = orphan_parameter_warnings(j, layer)
    assert [w.requirement_id for w in warnings] == ["req-2", "req-9"]
    assert {w.code for w in warnings} == {WarningCode.ORPHAN_JOB_PARAMETER}
