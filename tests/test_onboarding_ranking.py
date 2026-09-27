"""Onboarding step 6, Updated ranking: each role opens on its job description.

Every row's "Open" only opens the role in full (ui/js/expand.js): nothing on
the server changes and the wizard stays open. The opened role shows its job
description, each requirement against the CV with advice on the ones not
covered, and "Start application", which presses a hidden native button.
"""

import re

from streamlit.testing.v1 import AppTest

from core import store
from oi.intelligence.extraction import extract_candidate
from tests.test_candidate_extraction import FakeModelClient, make_cv, make_fields
from tests.test_jd_match import REACHABLE
from tests.test_onboarding_work_auth import ALL, EU, at_step, chosen, decl, page
from ui import tabs


def at_ranking(authorized=("GB",)):
    at = at_step("6", authorized=list(authorized))
    at.session_state[store.APPS] = []  # app.py's store.init() keeps the applications
    # The CV read in step 1: Python, and a Summer Analyst internship.
    at.session_state[store.CANDIDATE] = extract_candidate(make_cv(), FakeModelClient(fields=make_fields()))
    at.run()
    assert not at.exception
    return at


def test_every_row_only_opens_its_role() -> None:
    at = at_ranking()
    html = page(at)
    rows = re.findall(r'<div class="it xp[^"]*"', html)
    assert len(rows) == 5
    assert html.count('<div class="btn">Open</div>') == 5
    assert '<div class="btn">Start application</div>' not in html
    # No native button lies over a row any more: a press reaches the row.
    assert not [b for b in at.button if b.key and b.key.startswith("oo-it")]


def test_each_role_carries_its_description_gaps_and_apply_button() -> None:
    at = at_ranking()
    html = page(at)
    top = store.ranked(at.session_state[store.ANSWERS] | {store.WORK_AUTH: at.session_state[store.WORK_AUTH]})
    fulls = re.findall(r'<div class="xp-full">(.*?)<div class="jd-act">', html, re.S)
    assert len(fulls) == 5
    for i, full in enumerate(fulls):
        assert 'class="p-h xp-head"' in full
        assert "About the role" in full and "Requirements" in full
        assert f'data-apply="ap{i}"' in html
    # Lazarde & Co. asks for payments experience, which the CV does not show.
    if any(v.id == "lazarde-ba" for v in top[:5]):
        assert re.search(r'<li class="gap">.*?Experience in payments', html, re.S)
    # Deutsch Bank's HSK 6 is a level no rule checks: to verify, never covered.
    if any(v.id == "deutsch-shanghai" for v in top[:5]):
        assert re.search(r'<li class="verify">(?:(?!</li>).)*?HSK 6', html, re.S)


def test_start_application_in_the_opened_role_applies_to_that_role(monkeypatch) -> None:
    # Alone, the page has no registered pages to switch to (app.py adds them): record where it goes.
    went = []
    monkeypatch.setattr(tabs, "go", lambda name, **params: went.append((name, params)))
    at = at_ranking()
    ids = [v.id for v in store.ranked(at.session_state[store.ANSWERS] | {store.WORK_AUTH: at.session_state[store.WORK_AUTH]})[:5]]
    at.button(key="ap2").click().run()
    assert not at.exception
    assert [a["role"] for a in at.session_state[store.APPS]] == [ids[2]]
    assert went == [("applications", {"id": ids[2]})]
    assert at.session_state["flash"].startswith("Application started")


def _top5_script():
    import streamlit as st

    from core import store

    store.init()
    out = set()
    for declaration in st.session_state["cases"]:
        store.set_work_auth(declaration)
        for choice in ("yes", "no", "unsure"):
            store.set_uk(choice)
            out |= {v.id for v in store.ranked(store.answers())[:5]}
    st.session_state["out"] = sorted(out)


def test_every_role_the_ranking_can_show_has_a_written_description() -> None:
    cases = [decl(not_authorized=ALL), chosen(*EU), chosen(*ALL), chosen("GB"), chosen("CN"), chosen("SG"),
             chosen("HK"), chosen("CH"), chosen(*EU, "CN"), chosen("CN", "HK", "SG"), decl()]
    at = AppTest.from_function(_top5_script, default_timeout=120)
    at.session_state["cases"] = cases
    at.run()
    assert not at.exception
    assert set(at.session_state["out"]) <= set(REACHABLE)
    assert all(store.data().role(rid).get("description") for rid in REACHABLE)
