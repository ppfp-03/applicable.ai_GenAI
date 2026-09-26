"""Visible demo numbers and work-authorisation copy match the demo data.

Counts are taken from the roles actually available (8 in the baseline, 12
after the simulated ingestion event) under the canonical checks; there is no
larger catalogue behind them. Citizenship is never presented as permission to
work.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
import streamlit as st

from core import store

D = store.data()
RAW = json.loads((Path(__file__).resolve().parents[1] / "data" / "demo.json").read_text("utf-8"))


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def test_no_static_catalogue_numbers_remain():
    assert "catalog" not in RAW


@pytest.mark.parametrize("ran, total", [(False, 8), (True, 12)])
@pytest.mark.parametrize("uk", ["current", None, "yes", "no", "unsure"])
def test_counts_are_the_available_roles(ran, total, uk):
    if ran:
        store.run_simulated_event()
    ans = store.answers() if uk == "current" else {**store.answers(), "uk_work": uk}
    got = store.counts(uk)
    assert sum(got.values()) == total
    assert got == {"eligible": 0, "verify": 0, "excluded": 0,
                   **Counter(v.standing for v in store.views(ans))}
    assert store.nav_counts()["matches"] == store.counts()["eligible"]


def test_uk_roles_are_the_available_uk_roles():
    assert [v.id for v in store.uk_roles()] == [r.id for r in D.roles if r.country == "GB"]


def test_profile_never_presents_citizenship_as_work_authorisation():
    sections = {s["id"]: s for s in D.sections}
    shown = json.dumps([sections["auth"], sections["spons"]], ensure_ascii=False)
    shown = shown.replace(sections["auth"]["q"], "")  # the CV's own words stay quoted as evidence
    for phrase in ["EU citizen", "European Union", "inferred them", "Nationality matches",
                   "Not required", "Required"]:
        assert phrase not in shown, phrase
    labels = [label for label, _ in sections["auth"]["vals"]]
    assert "Citizenship" in labels  # citizenship is shown, labelled as citizenship
