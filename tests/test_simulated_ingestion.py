"""T-020 / FR-10: the controlled "Simulated ingestion event".

The baseline shows no scenario posting. Running the event (the one controlled
action) makes the predefined synthetic postings available; the same canonical
checks and ranking then run over them, and every screen that shows one says
"Simulated ingestion event". Nothing claims real monitoring, a real newly
published posting, or a measured detection latency.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import eligibility, ranking, store
from oi.contracts import DiscoveryKind
from oi.intelligence.ranking import assess_freshness
from ui import parts

D = store.data()
EVENT = D.simulated_event
LABEL = "Simulated ingestion event"
SCENARIO = {"unicreda-pa", "mediobanco-growth", "roshe-basel", "deutsch-frankfurt"}
APP = str(Path(__file__).resolve().parents[1] / "app.py")

#: Phrases that would pass a scripted event off as real discovery.
REAL_DISCOVERY_CLAIMS = ["LinkedIn", "career pages", "Found on", "New today", "Posted yesterday",
                         "Posted today", "Verified today", "verified today", "checked today",
                         "detected in", "detection latency:", "real-time"]


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def ids(items) -> set[str]:
    return {v.id for v in items}


# ─────────────────────────── Scenario data ───────────────────────────


def test_the_scenario_is_the_predefined_roles_and_is_labelled() -> None:
    assert EVENT["label"] == LABEL
    assert {r.id for r in D.roles if store.is_simulated(r)} == SCENARIO


def test_scenario_postings_are_not_pre_saved_or_applied_to() -> None:
    assert not SCENARIO & {a["role"] for a in D.applications}


# ─────────────────────────── 1. Baseline ───────────────────────────


def test_baseline_has_no_scenario_posting() -> None:
    assert not store.simulated_event_ran()
    assert not ids(store.views()) & SCENARIO
    assert not ids(store.ranked(include_new=True)) & SCENARIO
    assert not ids(store.top_matches()) & SCENARIO
    assert store.new_matches() == []


# ─────────────────── 2 + 3. Controlled action, postings appear ───────────────────


def test_running_the_event_makes_the_scenario_postings_available() -> None:
    before = ids(store.views())

    store.run_simulated_event()

    assert store.simulated_event_ran()
    assert ids(store.views()) == before | SCENARIO
    assert ids(store.new_matches()) == SCENARIO


def test_the_event_is_idempotent_and_leaves_new_postings_unreviewed() -> None:
    store.run_simulated_event()
    st.session_state[store.REVIEWED] = True

    store.run_simulated_event()

    assert store.reviewed()
    assert len(store.views()) == len(D.roles)


def test_a_fresh_session_starts_from_the_baseline_again() -> None:
    store.run_simulated_event()

    store.log_in()

    assert not store.simulated_event_ran()
    assert not ids(store.views()) & SCENARIO


def test_eligible_scenario_postings_join_the_ranking_once_reviewed() -> None:
    store.run_simulated_event()
    assert not ids(store.ranked()) & SCENARIO

    st.session_state[store.REVIEWED] = True

    eligible = {v.id for v in store.new_matches() if v.standing != "excluded"}
    assert eligible and eligible <= ids(store.ranked())


# ─────────────────────────── 4. Provenance ───────────────────────────


@pytest.mark.parametrize("role_id", sorted(SCENARIO))
def test_scenario_job_record_carries_truthful_provenance(role_id: str) -> None:
    role = D.role(role_id).raw
    record = eligibility.job(role)

    assert role["scenario"] == EVENT["id"]
    assert record.discovery_kind is DiscoveryKind.SYNTHETIC_SCENARIO
    assert record.source_published_at is None
    assert record.first_seen_at == datetime.fromisoformat(role["first_seen_at"])
    assert role["posted_days_ago"] is None
    assert "Posted" not in role["factors"]["freshness"][1]


@pytest.mark.parametrize("role_id", sorted(SCENARIO))
def test_canonical_freshness_treats_it_as_simulated_discovery(role_id: str) -> None:
    record = eligibility.job(D.role(role_id).raw)

    result = assess_freshness(source_published_at=record.source_published_at,
                              first_seen_at=record.first_seen_at,
                              discovery_kind=record.discovery_kind,
                              now=record.first_seen_at, horizon_days=30)

    assert result.basis == "simulated_discovery"


# ─────────────────── 6. Recomputation through canonical paths ───────────────────


def test_the_event_recomputes_through_the_canonical_checks_and_ranking(monkeypatch) -> None:
    checked: list[str] = []
    assess = eligibility.assess

    def spy(role, profile, answers):
        checked.append(role["id"])
        return assess(role, profile, answers)

    monkeypatch.setattr(store.eligibility, "assess", spy)

    store.views()
    assert not set(checked) & SCENARIO

    store.run_simulated_event()
    checked.clear()
    new = store.new_matches()

    assert set(checked) >= SCENARIO
    for v in new:
        raw = ranking.raw_score(v.factors, D.weights)
        assert v.score == ranking.priority(raw, v.standing, D.penalty)
        assert v.criterion("permission").rule.startswith(f"{eligibility.WORK_AUTH} v")


# ─────────────────── 5 + 7. What the screens say ───────────────────


def app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    return at


def page(at: AppTest) -> str:
    assert not at.exception
    return "".join(m.value for m in at.markdown)


def cards_for(text: str, company: str) -> list[str]:
    """Each match card (class "mc") that names `company`."""
    return [c for c in re.split(r'(?=<div class="mc)', text) if f"{company} ·" in c and c.startswith('<div class="mc')]


def assert_no_real_discovery_claim(text: str) -> None:
    for phrase in REAL_DISCOVERY_CLAIMS:
        assert phrase not in text, phrase
    for m in re.finditer(r"monitoring", text):
        assert text[max(0, m.start() - 9):m.start()] == "not live ", text[m.start() - 40:m.end()]
    for m in re.finditer(r"latency", text):
        assert text[max(0, m.start() - 13):m.start()] == "no detection ", text[m.start() - 40:m.end()]


def test_explore_runs_the_event_and_labels_every_new_posting() -> None:
    at = app()
    at.run()
    before = page(at)
    assert "simulated ingestion event not run" in before
    assert not cards_for(before, "UniCreda")

    at.button(key="x-sim").click().run()
    after = page(at)

    assert "4 added by a simulated ingestion event" in after
    for company in ("UniCreda", "Mediobanco", "Roshe", "Deutsch Bank"):
        sim_cards = [c for c in cards_for(after, company) if "<small>Simulated</small>" in c]
        assert sim_cards, company
        assert all(LABEL in c for c in sim_cards)
    assert_no_real_discovery_claim(after)


def test_home_card_runs_the_event_and_lists_what_it_added() -> None:
    at = app()
    # Before the event the Hong Kong question is not in the carousel.
    at.session_state["home_card"] = [w["kind"] for w in D.week if w["kind"] != "question"].index("new")
    at.run()
    before = page(at)
    assert LABEL in before and "not live monitoring" in before
    assert "Review 4 matches" not in [b.label for b in at.button]

    at.button(key="uc-sim").click().run()
    after = page(at)

    assert "Review 4 matches" in [b.label for b in at.button]
    assert f"<b>{LABEL}</b>" in after
    assert_no_real_discovery_claim(after)


def test_home_hong_kong_question_waits_for_the_event_and_claims_no_role_count() -> None:
    question = next(w for w in D.week if w["kind"] == "question")
    # No demo role is in Hong Kong, so the card must not claim any depend on it.
    assert not [r for r in D.roles if r.city == "Hong Kong"]
    copy = " ".join([question["sub"], question["waiting"], *question["results"].values()])
    assert not re.search(r"\b\d+ roles\b", copy), copy

    at = app()
    at.run()
    assert question["title"] not in page(at)
    assert "UniCreda" not in page(at)
    assert_no_real_discovery_claim(page(at))

    at.session_state["home_card"] = [w["kind"] for w in D.week if w["kind"] != "question"].index("new")
    at.run()
    at.button(key="uc-sim").click().run()
    assert question["title"] in page(at)


def test_matches_row_tag_names_the_simulated_event() -> None:
    store.run_simulated_event()

    for v in store.new_matches():
        assert parts.tag(v) == ("", LABEL)
