"""Tests for core/rules.py now that it no longer decides work authorisation.

Permission to work comes only from the canonical HC_WORK_AUTH rule
(core/eligibility.py; see tests/test_canonical_work_auth.py). core/rules.py
takes that outcome as given and has no fallback of its own, so a second,
conflicting work-authorisation implementation cannot come back unnoticed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import rules
from core.rules import RULES_VERSION, Criterion, evaluate, verdict

_DEMO = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "demo.json").read_text("utf-8")
)
PROFILE = _DEMO["profile"]
ROLES = {role["id"]: role for role in _DEMO["roles"]}

GIVEN = Criterion("permission", "Permission to work", "check", "given", "given", "given")


def test_there_is_no_legacy_permission_rule():
    assert not hasattr(rules, "_permission")
    assert not hasattr(rules, "work_authorisation")


def test_evaluate_requires_the_permission_outcome():
    with pytest.raises(TypeError):
        evaluate(PROFILE, {"uk_work": "yes"}, ROLES["replai-pa"])  # type: ignore[call-arg]


@pytest.mark.parametrize("role_id", sorted(ROLES))
def test_the_permission_outcome_is_used_unchanged(role_id):
    crit = evaluate(PROFILE, {"uk_work": "yes"}, ROLES[role_id], permission=GIVEN)
    assert [c.id for c in crit] == list(rules.CRITERIA)
    assert crit[1] is GIVEN


def test_rules_are_versioned():
    # Rules change with the law; an outcome must be traceable to a version.
    assert RULES_VERSION


def test_verdict_order():
    met = Criterion("x", "x", "met", "", "", "")
    check = Criterion("x", "x", "check", "", "", "")
    no = Criterion("x", "x", "not_met", "", "", "")
    assert verdict([met, met]) == "eligible"
    assert verdict([met, check]) == "verify"
    assert verdict([check, no, met]) == "excluded"
