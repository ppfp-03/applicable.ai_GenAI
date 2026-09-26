"""The temporary job-side parameter layer."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from oi.intelligence.eligibility.parameters import (
    DegreeLevelParams,
    GradWindowParams,
    JobParameterSet,
    LanguageParams,
    MinExperienceParams,
    WorkAuthParams,
    load_job_parameters,
)


def entry(parameters: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "job_id": "greenhouse:1",
        "requirement_id": "req-1",
        "constraint_id": "HC_GRAD_WINDOW",
        "parameters": parameters,
        "evidence_ids": ["ev-1"],
        "origin": "curated",
    }
    fields.update(overrides)
    return fields


GRAD = {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}


def parameter_set(*entries: dict[str, Any]) -> JobParameterSet:
    return JobParameterSet.model_validate(
        {"layer_version": "0.1-temporary", "entries": list(entries)}
    )


def test_committed_layer_loads_and_is_empty() -> None:
    layer = load_job_parameters()
    assert layer.layer_version == "0.1-temporary"
    assert layer.entries == []


@pytest.mark.parametrize(
    ("parameters", "expected_type"),
    [
        (GRAD, GradWindowParams),
        ({"kind": "degree_level", "min_level": "master"}, DegreeLevelParams),
        ({"kind": "language", "language": "de", "scale": "CEFR", "min_level": "B2"}, LanguageParams),
        ({"kind": "min_experience", "min_months": 6}, MinExperienceParams),
        ({"kind": "work_auth", "employer_sponsorship": "offered"}, WorkAuthParams),
    ],
)
def test_kind_selects_the_parameter_type(parameters: dict[str, Any], expected_type: type) -> None:
    layer = parameter_set(entry(parameters))
    assert isinstance(layer.entries[0].parameters, expected_type)


def test_degree_policy_override_is_optional_and_closed() -> None:
    assert DegreeLevelParams(kind="degree_level", min_level="bachelor").in_progress_policy is None
    with pytest.raises(ValidationError):
        DegreeLevelParams(kind="degree_level", min_level="bachelor", in_progress_policy="maybe")


@pytest.mark.parametrize(
    "parameters",
    [
        {"kind": "grad_window", "start": "2027-12-31", "end": "2027-01-01"},
        {"kind": "language", "language": "English", "scale": "CEFR", "min_level": "B2"},
        {"kind": "language", "language": "en", "min_level": "B2"},
        {"kind": "language", "language": "en", "scale": "CEFR", "min_level": "fluent"},
        {"kind": "language", "language": "zh", "scale": "HSK", "min_level": "7"},
        {"kind": "language", "language": "ja", "scale": "JLPT", "min_level": "N6"},
        {"kind": "language", "language": "en", "scale": "TOEFL", "min_level": "100"},
        {"kind": "min_experience"},
        {"kind": "min_experience", "min_months": 6, "answer_key": "x"},
        {"kind": "min_experience", "min_months": 0},
        {"kind": "work_auth", "employer_sponsorship": "maybe"},
        {"kind": "work_auth", "country_code": "uk", "employer_sponsorship": "offered"},
        {"kind": "student_status", "accepted": []},
        {"kind": "field_of_study", "accepted": ["finance", "finance"], "related_accepted": False},
        {"kind": "salary", "min": 1},
    ],
)
def test_malformed_parameters_are_rejected(parameters: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parameter_set(entry(parameters))


def test_entries_must_cite_job_evidence() -> None:
    with pytest.raises(ValidationError):
        parameter_set(entry(GRAD, evidence_ids=[]))


def test_entries_are_unique_per_requirement() -> None:
    with pytest.raises(ValidationError, match="unique"):
        parameter_set(entry(GRAD), entry(GRAD))


def test_lookup_by_job_and_requirement() -> None:
    layer = parameter_set(
        entry(GRAD, requirement_id="req-2"),
        entry(GRAD, requirement_id="req-1"),
        entry(GRAD, job_id="greenhouse:2"),
    )
    assert [e.requirement_id for e in layer.for_job("greenhouse:1")] == ["req-1", "req-2"]
    assert layer.get("greenhouse:2", "req-1") is not None
    assert layer.get("greenhouse:2", "req-2") is None
