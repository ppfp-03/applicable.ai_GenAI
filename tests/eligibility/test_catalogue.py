"""The internal RuleCatalogue v0.1 and its loader."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from oi.intelligence.eligibility.catalogue import (
    DEFAULT_CATALOGUE_PATH,
    DEGREE_LEVELS,
    DEGREE_STATUSES,
    LANGUAGE_SCALES,
    STUDENT_STATUSES,
    LanguageLevel,
    RuleCatalogue,
    load_rule_catalogue,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_IDS = [
    "HC_LOCATION",
    "HC_WORK_AUTH",
    "HC_STUDENT_STATUS",
    "HC_GRAD_WINDOW",
    "HC_DEGREE_LEVEL",
    "HC_FIELD_OF_STUDY",
    "HC_LANGUAGE",
    "HC_MIN_EXPERIENCE",
]


@pytest.fixture(scope="module")
def raw() -> dict[str, Any]:
    return json.loads(DEFAULT_CATALOGUE_PATH.read_text(encoding="utf-8"))


def test_default_catalogue_loads_the_eight_constraints_in_order() -> None:
    catalogue = load_rule_catalogue()
    assert catalogue.catalogue_version == "0.1-internal"
    assert catalogue.contract_status == "internal-not-frozen"
    assert catalogue.constraint_ids == EXPECTED_IDS


def test_shared_hard_constraint_stub_ids_exist_in_the_catalogue() -> None:
    # config/hard_constraints.json is shared and untouched; it must not drift.
    shared = json.loads((REPO_ROOT / "config" / "hard_constraints.json").read_text())
    catalogue_ids = set(load_rule_catalogue().constraint_ids)
    for entry in shared["constraints"]:
        assert entry["id"] in catalogue_ids


def test_only_d040_key_is_marked_approved() -> None:
    approved = {
        (spec.constraint_id, key.answer_key)
        for spec in load_rule_catalogue().constraints
        for key in spec.answer_keys
        if key.approval_ref is not None
    }
    assert approved == {("HC_MIN_EXPERIENCE", "has_corporate_finance_experience")}


def test_degree_in_progress_policy_defaults_to_undecided() -> None:
    spec = load_rule_catalogue().get("HC_DEGREE_LEVEL")
    assert spec is not None
    assert spec.settings == {"in_progress_policy": "undecided"}


def test_vocabularies_match_the_code_constants() -> None:
    catalogue = load_rule_catalogue()

    def values(constraint_id: str, key: str) -> tuple[str, ...]:
        spec = catalogue.get(constraint_id)
        assert spec is not None
        answer = spec.answer_key(key)
        assert answer is not None and answer.allowed_values is not None
        return tuple(answer.allowed_values)

    assert values("HC_DEGREE_LEVEL", "degree_level") == DEGREE_LEVELS
    assert values("HC_DEGREE_LEVEL", "degree_status") == DEGREE_STATUSES
    assert values("HC_STUDENT_STATUS", "current_status") == STUDENT_STATUSES
    language = catalogue.get("HC_LANGUAGE")
    assert language is not None

    def scale(*names: str) -> tuple[str, ...]:
        return tuple(f"{name}:{level}" for name in names for level in LANGUAGE_SCALES[name])

    extra = {"level_zh": scale("HSK"), "level_ja": scale("JLPT")}
    for key in language.answer_keys:
        assert key.answer_key.startswith("level_")
        expected = extra.get(key.answer_key, scale("CEFR")) + scale("SELF")
        assert tuple(key.allowed_values or ()) == expected
        assert all(LanguageLevel.parse(v) is not None for v in expected)


def test_get_returns_none_for_unsupported_ids() -> None:
    assert load_rule_catalogue().get("work_authorization_nl") is None


def test_field_path_uses_the_shared_eligibility_family() -> None:
    spec = load_rule_catalogue().get("HC_GRAD_WINDOW")
    assert spec is not None
    assert (
        spec.field_path("expected_graduation_date")
        == "eligibility_answers.HC_GRAD_WINDOW.expected_graduation_date"
    )


def test_rejects_duplicate_constraint_ids(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    data["constraints"].append(copy.deepcopy(data["constraints"][0]))
    with pytest.raises(ValidationError, match="unique"):
        RuleCatalogue.model_validate(data)


def test_rejects_non_hc_constraint_id(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    data["constraints"][0]["constraint_id"] = "work_authorization_nl"
    with pytest.raises(ValidationError):
        RuleCatalogue.model_validate(data)


def test_rejects_unknown_setting_value(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    degree = next(c for c in data["constraints"] if c["constraint_id"] == "HC_DEGREE_LEVEL")
    degree["settings"]["in_progress_policy"] = "sometimes"
    with pytest.raises(ValidationError, match="in_progress_policy"):
        RuleCatalogue.model_validate(data)


def test_rejects_setting_on_constraint_without_settings(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    data["constraints"][0]["settings"] = {"in_progress_policy": "counts"}
    with pytest.raises(ValidationError, match="unknown setting"):
        RuleCatalogue.model_validate(data)


def test_rejects_choice_key_without_values(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    student = next(
        c for c in data["constraints"] if c["constraint_id"] == "HC_STUDENT_STATUS"
    )
    student["answer_keys"][0]["allowed_values"] = None
    with pytest.raises(ValidationError, match="allowed_values"):
        RuleCatalogue.model_validate(data)


def test_rejects_duplicate_answer_keys(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    degree = next(c for c in data["constraints"] if c["constraint_id"] == "HC_DEGREE_LEVEL")
    degree["answer_keys"].append(copy.deepcopy(degree["answer_keys"][0]))
    with pytest.raises(ValidationError, match="unique"):
        RuleCatalogue.model_validate(data)


def test_rejects_non_internal_version(raw: dict[str, Any]) -> None:
    data = copy.deepcopy(raw)
    data["catalogue_version"] = "1.0"
    with pytest.raises(ValidationError):
        RuleCatalogue.model_validate(data)
