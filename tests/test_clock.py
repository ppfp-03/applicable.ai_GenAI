"""The app's clock follows the real date (core/clock.py).

A posting past its closing date stays visible as closed, but rankings,
counts, the onboarding shortlist and Home's widgets take the open ones only.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import clock, store

APP = str(Path(__file__).resolve().parents[1] / "app.py")
#: The day after Nestella's Strategy Intern closed (Sat 3 Oct), the first demo role to close.
AFTER_NESTELLA = "2026-10-04T09:00"


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()


def at(monkeypatch, moment: str) -> None:
    monkeypatch.setenv(clock.PIN, moment)


def run_home() -> str:
    app = AppTest.from_file(APP, default_timeout=120)
    app.session_state["stage"] = "app"
    app.session_state["home_guide_seen"] = True
    app.run()
    assert not app.exception
    return "".join(x.value for x in app.markdown)


def test_without_a_pin_the_clock_is_the_machines(monkeypatch):
    monkeypatch.delenv(clock.PIN, raising=False)
    assert clock.today() == date.today()
    assert abs((clock.now() - datetime.now()).total_seconds()) < 5


def test_no_demo_posting_closes_in_september():
    assert not [r.id for r in store.data().roles if r.closes.startswith("2026-09")]
    assert store.data().role("replai-pa").closes == "2026-10-31"


@pytest.mark.parametrize("moment, line, urgent", [
    ("2026-09-30T10:00", "Closes in 3 d", True),
    ("2026-10-01T10:00", "Closes in 2 d", True),
    ("2026-10-03T23:00", "Closes today", True),
    ("2026-10-04T09:00", "Closed yesterday", False),
    ("2026-10-06T09:00", "Closed 3 d ago", False),
])
def test_the_deadline_is_counted_from_today(monkeypatch, moment, line, urgent):
    at(monkeypatch, moment)
    assert clock.closes_line(store.data().role("nestella-strategy")) == (line, urgent)


def test_in_days():
    assert [clock.in_days(n) for n in (0, 1, 3)] == ["today", "in 1 day", "in 3 days"]


def test_a_closed_posting_stays_visible_but_is_never_ranked(monkeypatch):
    at(monkeypatch, AFTER_NESTELLA)
    assert "nestella-strategy" in {v.id for v in store.views()}
    assert [v.id for v in store.closed_views()] == ["nestella-strategy"]
    assert "nestella-strategy" not in {v.id for v in store.open_views()}
    assert "nestella-strategy" not in {v.id for v in store.ranked(as_of=store.data().profile["onboarded"])}
    assert "nestella-strategy" not in {v.id for v in store.top_matches()}
    assert store.matches().get("nestella-strategy") not in store.matches().ordered


def test_an_unsent_application_to_a_closed_role_leaves_the_live_ones(monkeypatch):
    at(monkeypatch, AFTER_NESTELLA)
    live = {a["role"] for a in store.live_applications()}
    assert "nestella-strategy" not in live  # saved, never sent
    assert {"lazarde-ba", "jpmorrow-strategy"} <= live  # sent: they stay
    assert "nestella-strategy" in {a["role"] for a in store.applications()}


def test_no_ranked_role_ever_counts_down_below_zero(monkeypatch):
    at(monkeypatch, "2026-10-19T09:00")
    assert all(clock.days_until(v.closes) >= 0 for v in store.ranked(include_new=True))


def test_home_widgets_show_open_postings_only(monkeypatch):
    at(monkeypatch, AFTER_NESTELLA)
    page = run_home()
    assert "Sunday 4 Oct" in page
    assert "1 closed, not shown" in page
    strip = page[page.index('<div class="trk">'):page.index("Applications</b>")]
    assert "Strategy Intern</div><div class=\"m\">Nestella" not in strip


def test_the_next_action_card_goes_once_its_role_has_closed(monkeypatch):
    at(monkeypatch, "2026-10-30T09:00")
    assert "Finish your Replai application" in run_home()
    at(monkeypatch, "2026-11-01T09:00")
    assert "Finish your Replai application" not in run_home()
