"""Home's "Next best action" shows right to work as HC_WORK_AUTH decides it now.

The card used to pin "UK permission confirmed" and "Eligible" whatever the
user answered. Both now follow the canonical outcome for the current answers:
MET -> confirmed, UNKNOWN -> needs verification, CONFLICT -> conflict.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import eligibility, store
from oi.intelligence.eligibility import RuleStatus
from ui import parts

D = store.data()
APP = str(Path(__file__).resolve().parents[1] / "app.py")
NEXT = next(w for w in D.week if w["kind"] == "next")
ROLE = D.role(NEXT["role"])  # Replai, London, does not sponsor

#: UK answer -> (canonical status, row kind, row text, standing label)
CASES = {
    "yes": (RuleStatus.MET, "ok", "Right to work in London · confirmed", "Eligible"),
    "no": (RuleStatus.CONFLICT, "gap", "Right to work in London · conflict", "Excluded"),
    "unsure": (RuleStatus.UNKNOWN, "gap", "Right to work in London · needs verification", "To verify"),
    None: (RuleStatus.UNKNOWN, "gap", "Right to work in London · needs verification", "To verify"),
}


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def test_the_card_has_no_pinned_work_auth_copy():
    assert ["work_auth", ""] in NEXT["checks"]
    assert "permission confirmed" not in str(NEXT).lower()
    assert "Eligible" not in NEXT["sub"]


@pytest.mark.parametrize("uk", list(CASES))
def test_row_follows_the_canonical_outcome(uk):
    status, kind, text, _ = CASES[uk]
    assert eligibility.work_auth(ROLE.raw, {"uk_work": uk}).status is status
    assert parts.work_auth_check(store.view(ROLE, {"uk_work": uk})) == (kind, text)


def test_citizenship_does_not_confirm_it(monkeypatch):
    profile = {**D.profile, "citizenship": "GB"}
    monkeypatch.setattr(D, "profile", profile)
    assert parts.work_auth_check(store.view(ROLE, {"uk_work": None}))[0] == "gap"


@pytest.mark.parametrize("uk", list(CASES))
def test_home_renders_the_current_state(uk):
    _, _, text, standing = CASES[uk]
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    at.session_state[store.ANSWERS] = {"uk_work": uk}
    at.session_state["home_card"] = [w["kind"] for w in D.week].index("next")
    at.run()
    assert not at.exception
    page = "".join(m.value for m in at.markdown)
    assert text in page
    assert f'{NEXT["sub"]} · {standing}' in page
    assert "UK permission confirmed" not in page
    others = {t for _, _, t, _ in CASES.values()} - {text}
    assert not any(t in page for t in others)
