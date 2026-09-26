"""The screens' permission tile comes from the canonical HC_WORK_AUTH rule.

Pins FR-02 / FR-04 for work authorisation: citizenship alone never makes a
role MET, a missing declaration is UNKNOWN ("to verify"), an explicit
declaration is respected, only an explicit "sponsorship not offered" conflicts
(unstated sponsorship is UNKNOWN), and the production
path (core.store) no longer runs the legacy core/rules.py permission rule.
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest
import streamlit as st

from core import eligibility, rules, store
from oi.intelligence.eligibility import RuleStatus

D = store.data()
ROOT = Path(__file__).resolve().parent.parent


def role(role_id: str) -> dict:
    return D.role(role_id).raw


def outcome(role_id: str, uk=None):
    return eligibility.work_auth(role(role_id), {"uk_work": uk})


def tile(role_id: str, uk=None):
    return store.view(D.role(role_id), {"uk_work": uk}).criterion("permission")


@pytest.fixture
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


# ───────────────────────── Canonical semantics ─────────────────────────


def test_citizenship_alone_is_not_work_authorisation():
    # The demo user is an Italian citizen; the Milan role is in Italy.
    assert D.profile["citizenship"] == "IT"
    assert outcome("mediobanco-growth").status is RuleStatus.UNKNOWN
    assert tile("mediobanco-growth").status == "check"


def test_citizenship_of_the_role_country_still_does_not_prove_it(monkeypatch):
    # Even a UK citizen gets no UK permit from citizenship: only a declaration counts.
    profile = copy.deepcopy(D.profile)
    profile["citizenship"] = "GB"
    monkeypatch.setattr(D, "profile", profile)
    assert tile("replai-pa", uk=None).status == "check"
    decl = eligibility.candidate(profile, {}).declarations
    assert decl.work_authorizations == [] and decl.additional_citizenships == []


@pytest.mark.parametrize("uk", [None, "unsure"])
def test_missing_declaration_is_unknown(uk):
    got = outcome("replai-pa", uk)
    assert got.status is RuleStatus.UNKNOWN
    assert got.missing_field_paths == [
        "declarations.work_authorizations.GB.authorized_to_work",
        "declarations.work_authorizations.GB.requires_sponsorship",
    ]
    assert store.view(D.role("replai-pa"), {"uk_work": uk}).standing == "verify"


@pytest.mark.parametrize("role_id", ["nestella-strategy", "roshe-product", "roshe-basel", "deutsch-frankfurt"])
def test_countries_without_a_declaration_are_unknown(role_id):
    assert outcome(role_id, "yes").status is RuleStatus.UNKNOWN


def test_explicit_yes_is_met():
    assert outcome("replai-pa", "yes").status is RuleStatus.MET
    assert store.view(D.role("replai-pa"), {"uk_work": "yes"}).standing == "eligible"


def test_needs_sponsorship_with_a_sponsoring_employer_is_met():
    assert role("bolton-strategy")["sponsorship"] == "offered"
    assert outcome("bolton-strategy", "no").status is RuleStatus.MET


def test_needs_sponsorship_without_one_is_a_conflict_and_excludes():
    assert role("replai-pa")["sponsorship"] == "not_offered"
    assert outcome("replai-pa", "no").status is RuleStatus.CONFLICT
    v = store.view(D.role("replai-pa"), {"uk_work": "no"})
    assert v.criterion("permission").status == "not_met"
    assert v.standing == "excluded"
    assert "replai-pa" not in {x.id for x in store.ranked({"uk_work": "no"}, include_new=True)}


def test_needs_sponsorship_when_it_is_not_stated_is_unknown(monkeypatch):
    monkeypatch.setitem(D.role("replai-pa").raw, "sponsorship", "not_stated")
    got = outcome("replai-pa", "no")
    assert got.status is RuleStatus.UNKNOWN
    assert got.unknown_cause.value == "job_parameter_missing"
    assert store.view(D.role("replai-pa"), {"uk_work": "no"}).standing == "verify"


def test_sponsorship_is_explicit_three_state_never_a_boolean():
    for r in D.roles:
        assert "sponsors_visa" not in r.raw
        assert r.raw["sponsorship"] in eligibility.SPONSORSHIP


def test_a_uk_answer_says_nothing_about_other_countries():
    for uk in ("yes", "no"):
        assert outcome("nestella-strategy", uk).status is RuleStatus.UNKNOWN


# ───────────────────────── Reaching the UI ─────────────────────────


@pytest.mark.parametrize("uk", ["yes", "no", "unsure", None])
def test_tile_renders_the_canonical_outcome(uk):
    for r in D.roles:
        got = outcome(r.id, uk)
        c = store.view(r, {"uk_work": uk}).criterion("permission")
        assert c.status == {"met": "met", "conflict": "not_met", "unknown": "check"}[got.status.value]
        assert c.detail == got.reason
        assert c.rule.startswith("HC_WORK_AUTH")


def test_changing_the_answer_recomputes_through_the_engine(fresh_session):
    r = D.role("replai-pa")
    store.set_uk(None)
    assert store.view(r).criterion("permission").status == "check"
    store.set_uk("yes")
    assert store.view(r).criterion("permission").status == "met"
    store.set_uk("no")
    assert store.view(r).standing == "excluded"


def test_the_legacy_permission_rule_is_gone():
    # core/rules.py has no work-authorisation logic left to fall back on.
    assert not hasattr(rules, "_permission")
    for uk in ("yes", "no", "unsure", None):
        for v in store.views({"uk_work": uk}):
            assert v.criterion("permission").rule.startswith("HC_WORK_AUTH")


def test_ui_modules_do_not_call_legacy_rules_directly():
    files = [ROOT / "app.py", *(ROOT / "views").glob("*.py"), *(ROOT / "ui").glob("*.py")]
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "core":
                assert "rules" not in {a.name for a in node.names}, path
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                assert node.value.id != "rules", f"{path}: rules.{node.attr}"
