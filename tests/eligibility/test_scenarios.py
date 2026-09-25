"""End-to-end scenarios through the real engine, catalogue and parameter layer.

Three synthetic development personas face one small job set with curated
parameters. They pin the three aggregate outcomes and the recompute after a
clarification answer. All people and companies are fictional.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility import (
    EligibilityStatus,
    JobParameterSet,
    RuleStatus,
    WarningCode,
    assess_eligibility,
    load_rule_catalogue,
)

from . import builders as b

CATALOGUE = load_rule_catalogue()

# ── Jobs ──

# Nestella Amsterdam: finance internship with every requirement parametrised.
AMSTERDAM = b.job(
    job_id="synthetic:nestella-ams",
    locations=[("NL", "Amsterdam")],
    requirements=[
        ("r-auth", "HC_WORK_AUTH", "mandatory"),
        ("r-grad", "HC_GRAD_WINDOW", "mandatory"),
        ("r-degree", "HC_DEGREE_LEVEL", "mandatory"),
        ("r-field", "HC_FIELD_OF_STUDY", "mandatory"),
        ("r-en", "HC_LANGUAGE", "mandatory"),
        ("r-status", "HC_STUDENT_STATUS", "mandatory"),
        ("r-nice", None, "preferred", "fit"),
    ],
)
AMSTERDAM_PARAMS = [
    ("r-auth", "HC_WORK_AUTH", {"kind": "work_auth", "employer_sponsorship": "not_offered"}),
    ("r-grad", "HC_GRAD_WINDOW", {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}),
    ("r-degree", "HC_DEGREE_LEVEL", {"kind": "degree_level", "min_level": "bachelor", "in_progress_policy": "counts"}),
    ("r-field", "HC_FIELD_OF_STUDY", {"kind": "field_of_study", "accepted": ["economics", "finance", "management"], "related_accepted": False}),
    ("r-en", "HC_LANGUAGE", {"kind": "language", "language": "en", "min_level": "C1"}),
    ("r-status", "HC_STUDENT_STATUS", {"kind": "student_status", "accepted": ["enrolled_student"]}),
]

# Bolton Consulting London: sponsors visas, needs Corporate Finance experience.
LONDON = b.job(
    job_id="synthetic:bolton-ldn",
    locations=[("GB", "London")],
    requirements=[
        ("r-auth", "HC_WORK_AUTH", "mandatory"),
        ("r-exp", "HC_MIN_EXPERIENCE", "mandatory"),
    ],
)
LONDON_PARAMS = [
    ("r-auth", "HC_WORK_AUTH", {"kind": "work_auth", "employer_sponsorship": "offered"}),
    ("r-exp", "HC_MIN_EXPERIENCE", {"kind": "min_experience", "answer_key": "has_corporate_finance_experience"}),
]


LAYER = JobParameterSet(
    layer_version="0.1-temporary",
    entries=[
        *b.parameters(*AMSTERDAM_PARAMS, job_id=AMSTERDAM.job_id).entries,
        *b.parameters(*LONDON_PARAMS, job_id=LONDON.job_id).entries,
    ],
)

# ── Personas ──


def persona_a() -> CandidateProfile:
    """Enrolled economics student, may work in NL and GB, C1 English."""

    return b.candidate(
        allowed_countries=["NL", "GB", "IT"],
        work_auth=[("NL", True, False), ("GB", False, True)],
        answers={
            ("HC_GRAD_WINDOW", "expected_graduation_date"): date(2027, 7, 15),
            ("HC_DEGREE_LEVEL", "degree_level"): "bachelor",
            ("HC_DEGREE_LEVEL", "degree_status"): "in_progress",
            ("HC_FIELD_OF_STUDY", "field_of_study"): "economics",
            ("HC_LANGUAGE", "level_en"): "C1",
            ("HC_STUDENT_STATUS", "current_status"): "enrolled_student",
            ("HC_MIN_EXPERIENCE", "has_corporate_finance_experience"): True,
        },
    )


def persona_b() -> CandidateProfile:
    """Recent law graduate; needs sponsorship in NL; only willing to work in NL."""

    return b.candidate(
        allowed_countries=["NL"],
        work_auth=[("NL", False, True)],
        citizenships=["NL"],  # declared, and still never read as authorization
        answers={
            ("HC_GRAD_WINDOW", "expected_graduation_date"): date(2026, 6, 30),
            ("HC_DEGREE_LEVEL", "degree_level"): "bachelor",
            ("HC_DEGREE_LEVEL", "degree_status"): "completed",
            ("HC_FIELD_OF_STUDY", "field_of_study"): "law",
            ("HC_LANGUAGE", "level_en"): "native",
            ("HC_STUDENT_STATUS", "current_status"): "recent_graduate",
        },
    )


def persona_c(experience: bool | None = None) -> CandidateProfile:
    """Finance student with gaps: no graduation date, no experience answer yet."""

    answers = {
        ("HC_DEGREE_LEVEL", "degree_level"): "master",
        ("HC_DEGREE_LEVEL", "degree_status"): "in_progress",
        ("HC_FIELD_OF_STUDY", "field_of_study"): "finance",
        ("HC_LANGUAGE", "level_en"): "C2",
        ("HC_STUDENT_STATUS", "current_status"): "enrolled_student",
    }
    if experience is not None:
        answers[("HC_MIN_EXPERIENCE", "has_corporate_finance_experience")] = experience
    return b.candidate(work_auth=[("NL", True, False), ("GB", True, False)], answers=answers)


def assess(candidate: CandidateProfile, job: JobRecord):
    return assess_eligibility(candidate, job, CATALOGUE, job_parameters=LAYER)


def statuses(result) -> dict[str, RuleStatus]:
    return {o.requirement_id or o.rule_id: o.status for o in result.outcomes}


# ── Scenarios ──


def test_persona_a_is_eligible_in_amsterdam() -> None:
    result = assess(persona_a(), AMSTERDAM)
    assert result.status is EligibilityStatus.ELIGIBLE
    assert statuses(result) == {
        "HC_LOCATION": RuleStatus.MET,
        "r-auth": RuleStatus.MET,
        "r-status": RuleStatus.MET,
        "r-grad": RuleStatus.MET,
        "r-degree": RuleStatus.MET,  # in progress, and this posting counts it
        "r-field": RuleStatus.MET,
        "r-en": RuleStatus.MET,
        "HC_MIN_EXPERIENCE": RuleStatus.NOT_APPLICABLE,
    }
    assert result.missing_field_paths == []
    assert result.warnings == []


def test_persona_a_needs_sponsorship_in_london_and_it_is_offered() -> None:
    result = assess(persona_a(), LONDON)
    assert result.status is EligibilityStatus.ELIGIBLE
    assert statuses(result)["r-auth"] is RuleStatus.MET


def test_persona_b_is_ineligible_in_amsterdam_for_several_reasons() -> None:
    result = assess(persona_b(), AMSTERDAM)
    assert result.status is EligibilityStatus.INELIGIBLE
    conflicts = sorted(k for k, v in statuses(result).items() if v is RuleStatus.CONFLICT)
    # Needs sponsorship (not offered), graduated outside the window, wrong
    # field, and not an enrolled student. Citizenship did not rescue r-auth.
    assert conflicts == ["r-auth", "r-field", "r-grad", "r-status"]


def test_persona_b_london_is_outside_the_declared_countries() -> None:
    result = assess(persona_b(), LONDON)
    s = statuses(result)
    assert s["HC_LOCATION"] is RuleStatus.CONFLICT
    assert result.status is EligibilityStatus.INELIGIBLE


def test_persona_c_is_uncertain_and_says_what_to_ask() -> None:
    result = assess(persona_c(), AMSTERDAM)
    assert result.status is EligibilityStatus.UNCERTAIN
    assert result.missing_field_paths == [
        "eligibility_answers.HC_GRAD_WINDOW.expected_graduation_date"
    ]
    # No perimeter declared, so location does not apply.
    assert statuses(result)["HC_LOCATION"] is RuleStatus.NOT_APPLICABLE


@pytest.mark.parametrize(
    ("answer", "expected"),
    [(None, EligibilityStatus.UNCERTAIN), (True, EligibilityStatus.ELIGIBLE), (False, EligibilityStatus.INELIGIBLE)],
)
def test_clarification_answer_recomputes_the_london_result(answer, expected) -> None:
    result = assess(persona_c(experience=answer), LONDON)
    assert result.status is expected
    if answer is None:
        assert result.missing_field_paths == [
            "eligibility_answers.HC_MIN_EXPERIENCE.has_corporate_finance_experience"
        ]
    else:
        assert result.missing_field_paths == []


def test_without_the_parameter_layer_nothing_becomes_a_conflict() -> None:
    result = assess_eligibility(persona_b(), AMSTERDAM, CATALOGUE)
    assert result.status is EligibilityStatus.UNCERTAIN
    assert RuleStatus.CONFLICT not in statuses(result).values()
    assert result.parameter_layer_version is None


def test_shared_contract_fixtures_run_and_only_warn() -> None:
    # The frozen J01 fixtures use non-HC IDs; they must not crash or exclude.
    root = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / "v0.2.0-draft"
    candidate = CandidateProfile.model_validate(
        json.loads((root / "candidate_profile.json").read_text())
    )
    job = JobRecord.model_validate(json.loads((root / "job_record.json").read_text()))
    result = assess_eligibility(candidate, job, CATALOGUE)
    assert result.status is EligibilityStatus.ELIGIBLE  # NL is inside the perimeter
    codes = {w.code for w in result.warnings}
    assert codes == {WarningCode.UNSUPPORTED_CONSTRAINT, WarningCode.UNKNOWN_ANSWER_KEY}
