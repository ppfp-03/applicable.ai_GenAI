"""HC_LANGUAGE."""

from __future__ import annotations

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import outcomes_for, single

CID = "HC_LANGUAGE"
GERMAN_B2 = {"kind": "language", "language": "de", "min_level": "B2"}


def speaks(**levels: str):
    return b.candidate(answers={(CID, f"level_{lang}"): lvl for lang, lvl in levels.items()})


@pytest.mark.parametrize("level", ["B2", "C1", "C2", "native"])
def test_level_at_or_above_requirement_is_met(level: str) -> None:
    outcome = single(CID, speaks(de=level), GERMAN_B2)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [b.answer_evidence_id(CID, "level_de")]


@pytest.mark.parametrize("level", ["A1", "B1"])
def test_level_below_requirement_is_conflict(level: str) -> None:
    assert single(CID, speaks(de=level), GERMAN_B2).status is RuleStatus.CONFLICT


def test_other_languages_do_not_count() -> None:
    outcome = single(CID, speaks(en="native", it="native"), GERMAN_B2)
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == ["eligibility_answers.HC_LANGUAGE.level_de"]


def test_missing_parameters_are_unknown() -> None:
    assert single(CID, speaks(de="A1")).unknown_cause is UnknownCause.JOB_PARAMETER_MISSING


def test_two_languages_give_two_outcomes() -> None:
    job = b.job(
        requirements=[("req-1", CID, "mandatory"), ("req-2", CID, "mandatory")]
    )
    layer = b.parameters(
        ("req-1", CID, {"kind": "language", "language": "en", "min_level": "C1"}),
        ("req-2", CID, GERMAN_B2),
    )
    outcomes = outcomes_for(CID, speaks(en="C2", de="B1"), job, layer)
    assert [(o.requirement_id, o.status) for o in outcomes] == [
        ("req-1", RuleStatus.MET),
        ("req-2", RuleStatus.CONFLICT),
    ]
