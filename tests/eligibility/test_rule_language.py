"""HC_LANGUAGE."""

from __future__ import annotations

from typing import Any

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import outcomes_for, single

CID = "HC_LANGUAGE"


def requires(language: str, scale: str, level: str) -> dict[str, str]:
    return {"kind": "language", "language": language, "scale": scale, "min_level": level}


GERMAN_B2 = requires("de", "CEFR", "B2")


def speaks(**levels: Any):
    return b.candidate(answers={(CID, f"level_{lang}"): lvl for lang, lvl in levels.items()})


# --- same scale -----------------------------------------------------------


@pytest.mark.parametrize("level", ["CEFR:B2", "CEFR:C1", "CEFR:C2"])
def test_cefr_level_at_or_above_requirement_is_met(level: str) -> None:
    outcome = single(CID, speaks(de=level), GERMAN_B2)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(CID, "level_de")]


@pytest.mark.parametrize("level", ["CEFR:A1", "CEFR:B1"])
def test_cefr_level_below_requirement_is_conflict(level: str) -> None:
    outcome = single(CID, speaks(de=level), GERMAN_B2)
    assert outcome.status is RuleStatus.CONFLICT
    assert outcome.reason == f"DE B2 required; you have {level[5:]}."


@pytest.mark.parametrize(
    ("level", "status"),
    [("HSK:4", RuleStatus.MET), ("HSK:6", RuleStatus.MET), ("HSK:3", RuleStatus.CONFLICT)],
)
def test_hsk_levels_compare_on_the_hsk_scale(level: str, status: RuleStatus) -> None:
    outcome = single(CID, speaks(zh=level), requires("zh", "HSK", "4"))
    assert outcome.status is status
    assert outcome.reason.startswith("ZH HSK 4 required; you have HSK ")


@pytest.mark.parametrize(
    ("level", "status"),
    [("JLPT:N3", RuleStatus.MET), ("JLPT:N1", RuleStatus.MET), ("JLPT:N4", RuleStatus.CONFLICT)],
)
def test_jlpt_levels_compare_on_the_jlpt_scale(level: str, status: RuleStatus) -> None:
    # JLPT runs downwards: N1 is the highest level.
    assert single(CID, speaks(ja=level), requires("ja", "JLPT", "N3")).status is status


# --- different scales -----------------------------------------------------


@pytest.mark.parametrize(
    ("language", "have", "need"),
    [
        ("it", "SELF:fluent", ("CEFR", "B2")),
        ("it", "CEFR:C2", ("SELF", "fluent")),
        ("de", "CEFR:B1", ("SELF", "fluent")),
    ],
)
def test_levels_on_different_scales_are_unknown(
    language: str, have: str, need: tuple[str, str]
) -> None:
    outcome = single(CID, speaks(**{language: have}), requires(language, *need))
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.POLICY_UNDECIDED
    assert outcome.missing_field_paths == []
    assert outcome.reason.endswith("Levels on different scales are not compared.")
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(CID, f"level_{language}")]


# --- fluent ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "need", "status", "counted"),
    [
        ("en", ("CEFR", "C1"), RuleStatus.MET, "C1"),
        ("en", ("CEFR", "C2"), RuleStatus.CONFLICT, "C1"),
        ("zh", ("HSK", "5"), RuleStatus.MET, "HSK 5"),
        ("zh", ("HSK", "6"), RuleStatus.CONFLICT, "HSK 5"),
        ("ja", ("JLPT", "N1"), RuleStatus.MET, "JLPT N1"),
    ],
)
def test_fluent_counts_as_its_approved_level(
    language: str, need: tuple[str, str], status: RuleStatus, counted: str
) -> None:
    outcome = single(CID, speaks(**{language: "SELF:fluent"}), requires(language, *need))
    assert outcome.status is status
    assert outcome.reason.endswith(f"you have fluent (counted as {counted}).")


def test_fluent_requirement_is_normalized_too() -> None:
    outcome = single(CID, speaks(en="CEFR:B2"), requires("en", "SELF", "fluent"))
    assert outcome.status is RuleStatus.CONFLICT
    assert outcome.reason == "EN fluent (counted as C1) required; you have B2."


def test_fluent_without_an_approved_mapping_is_not_converted() -> None:
    outcome = single(CID, speaks(it="SELF:fluent"), requires("it", "CEFR", "B2"))
    assert outcome.unknown_cause is UnknownCause.POLICY_UNDECIDED
    assert outcome.reason.startswith("IT B2 required; you have fluent.")


def test_fluent_meets_fluent_on_the_self_scale() -> None:
    outcome = single(CID, speaks(it="SELF:fluent"), requires("it", "SELF", "fluent"))
    assert outcome.status is RuleStatus.MET


# --- native ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "need"),
    [
        ("de", ("CEFR", "C2")),
        ("zh", ("HSK", "6")),
        ("ja", ("JLPT", "N1")),
        ("it", ("SELF", "fluent")),
        ("en", ("SELF", "fluent")),
        ("en", ("SELF", "native")),
    ],
)
def test_native_meets_every_level_of_its_language(language: str, need: tuple[str, str]) -> None:
    outcome = single(CID, speaks(**{language: "SELF:native"}), requires(language, *need))
    assert outcome.status is RuleStatus.MET


@pytest.mark.parametrize(
    ("language", "have"),
    [
        ("en", "CEFR:C2"),
        ("en", "SELF:fluent"),
        ("it", "SELF:fluent"),
        ("zh", "HSK:6"),
        ("zh", "SELF:fluent"),
        ("ja", "JLPT:N1"),
    ],
)
def test_only_native_meets_a_native_requirement(language: str, have: str) -> None:
    outcome = single(CID, speaks(**{language: have}), requires(language, "SELF", "native"))
    assert outcome.status is RuleStatus.CONFLICT
    assert outcome.reason.startswith(f"{language.upper()} native required; you have ")


def test_native_in_another_language_does_not_count() -> None:
    outcome = single(CID, speaks(en="SELF:native", it="SELF:native"), GERMAN_B2)
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == ["eligibility_answers.HC_LANGUAGE.level_de"]


# --- invalid values -------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["B2", "native", "CEFR:D1", "cefr:B2", "HSK:4", "JLPT:N2", "SELF:good", "", 5, True],
)
def test_unreadable_candidate_level_is_unknown_not_a_crash(value: Any) -> None:
    # "HSK:4" and "JLPT:N2" are real levels, but not in German's vocabulary.
    outcome = single(CID, speaks(de=value), GERMAN_B2)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == ["eligibility_answers.HC_LANGUAGE.level_de"]
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(CID, "level_de")]


@pytest.mark.parametrize(
    ("language", "have"), [("zh", "CEFR:C1"), ("ja", "CEFR:B2"), ("zh", "JLPT:N1")]
)
def test_mandarin_and_japanese_take_only_their_own_scale(language: str, have: str) -> None:
    need = ("HSK", "4") if language == "zh" else ("JLPT", "N3")
    outcome = single(CID, speaks(**{language: have}), requires(language, *need))
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == [f"eligibility_answers.HC_LANGUAGE.level_{language}"]


@pytest.mark.parametrize(
    ("language", "need"),
    [("en", ("HSK", "4")), ("zh", ("CEFR", "B2")), ("ja", ("CEFR", "B1"))],
)
def test_requirement_on_a_scale_the_language_does_not_take_is_not_compared(
    language: str, need: tuple[str, str]
) -> None:
    outcome = single(CID, speaks(**{language: "SELF:native"}), requires(language, *need))
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING


# --- requirements ---------------------------------------------------------


def test_missing_parameters_are_unknown() -> None:
    assert single(CID, speaks(de="CEFR:A1")).unknown_cause is UnknownCause.JOB_PARAMETER_MISSING


def test_two_languages_give_two_outcomes() -> None:
    job = b.job(
        requirements=[("req-1", CID, "mandatory"), ("req-2", CID, "mandatory")]
    )
    layer = b.parameters(
        ("req-1", CID, requires("en", "CEFR", "C1")),
        ("req-2", CID, GERMAN_B2),
    )
    outcomes = outcomes_for(CID, speaks(en="CEFR:C2", de="CEFR:B1"), job, layer)
    assert [(o.requirement_id, o.status) for o in outcomes] == [
        ("req-1", RuleStatus.MET),
        ("req-2", RuleStatus.CONFLICT),
    ]
