"""Tests for deterministic eligibility.

Work authorisation is never judged by a model, and never inferred from
citizenship: PROJECT_CONTEXT.md treats the two separately until a
country-specific inference is approved (Q-04). These tests pin that.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.rules import RULES_VERSION, evaluate, verdict

_DEMO = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "demo.json").read_text("utf-8")
)
PROFILE = _DEMO["profile"]
ROLES = {role["id"]: role for role in _DEMO["roles"]}


def permission(role: dict, answers: dict | None = None, profile: dict = PROFILE):
    return next(c for c in evaluate(profile, answers or {}, role) if c.id == "permission")


def in_country(country: str, **extra) -> dict:
    """A demo role moved to `country`, everything else unchanged."""
    return {**ROLES["deutsch-frankfurt"], "country": country, **extra}


class TestCitizenshipIsNotWorkAuthorisation:
    @pytest.mark.parametrize("country", ["IT", "DE", "FR", "NL", "CH", "JP"])
    def test_eu_citizen_is_asked_not_assumed(self, country):
        assert PROFILE["citizenship"] == "IT"
        c = permission(in_country(country))
        assert c.status == "check"
        assert c.rule == f"{country}_right_to_work = unknown → ask"

    def test_own_country_is_asked_too(self):
        c = permission(in_country("IT"), profile={**PROFILE, "citizenship": "IT"})
        assert c.status == "check"

    @pytest.mark.parametrize("months", [None, 3, 6, 18])
    def test_contract_length_no_longer_picks_a_swiss_permit(self, months):
        c = permission(in_country("CH", contract_months=months))
        assert c.status == "check"
        assert "permit" not in c.value.lower()

    def test_the_answer_says_why_it_asks(self):
        c = permission(in_country("DE"))
        assert "Citizenship alone does not settle it" in c.detail

    @pytest.mark.parametrize("role_id", ["mediobanco-growth", "roshe-basel", "deutsch-frankfurt"])
    def test_demo_eu_roles_need_verifying(self, role_id):
        assert verdict(evaluate(PROFILE, {"uk_work": "yes"}, ROLES[role_id])) == "verify"


class TestSingaporeDoesNotAssumeAnEmploymentPass:
    """Nothing in the profile says whether the user needs a pass.

    An employer that sponsors one covers either case, so the role stays open.
    Without sponsorship the answer depends on that unknown, so ask; never
    exclude on an assumption about the user's status.
    """

    def test_employer_sponsorship_covers_either_case(self):
        c = permission(in_country("SG", sponsors_visa=True))
        assert c.status == "met"
        assert "if you need one" in c.detail

    def test_no_sponsorship_asks_instead_of_excluding(self):
        c = permission(in_country("SG", sponsors_visa=False))
        assert c.status == "check"
        assert c.rule == "SG_right_to_work = unknown + no_sponsorship → ask"

    @pytest.mark.parametrize("sponsors", [True, False])
    def test_never_states_that_the_user_needs_a_pass(self, sponsors):
        c = permission(in_country("SG", sponsors_visa=sponsors))
        assert "You need an Employment Pass" not in c.detail
        assert "SG_EP_required" not in c.rule

    @pytest.mark.parametrize("role_id", ["nestella-strategy", "jpmorrow-strategy", "unicreda-pa"])
    def test_demo_singapore_roles_all_sponsor_and_stay_eligible(self, role_id):
        assert ROLES[role_id]["sponsors_visa"] is True
        assert verdict(evaluate(PROFILE, {"uk_work": "yes"}, ROLES[role_id])) == "eligible"


class TestExplicitAnswersStillDecide:
    def test_uk_yes_is_met(self):
        assert permission(in_country("GB"), {"uk_work": "yes"}).status == "met"

    def test_uk_unknown_asks(self):
        assert permission(in_country("GB"), {"uk_work": None}).status == "check"


def test_rules_are_versioned():
    # Rules change with the law; an outcome must be traceable to a version.
    assert RULES_VERSION
