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
#: The day after Replai's Product Analyst Intern closed (Sun 27 Sep).
AFTER_REPLAI = "2026-09-28T09:00"


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()


def at(monkeypatch, moment: str) -> None:
    monkeypatch.setenv(clock.PIN, moment)


def test_without_a_pin_the_clock_is_the_machines(monkeypatch):
    monkeypatch.delenv(clock.PIN, raising=False)
    assert clock.today() == date.today()
    assert abs((clock.now() - datetime.now()).total_seconds()) < 5


@pytest.mark.parametrize("moment, line, urgent", [
    ("2026-09-24T10:00", "Closes in 3 d", True),
    ("2026-09-25T10:00", "Closes in 2 d", True),
    ("2026-09-27T23:00", "Closes today", True),
    ("2026-09-28T09:00", "Closed yesterday", False),
    ("2026-09-30T09:00", "Closed 3 d ago", False),
])
def test_the_deadline_is_counted_from_today(monkeypatch, moment, line, urgent):
    at(monkeypatch, moment)
    assert clock.closes_line(store.data().role("replai-pa")) == (line, urgent)


def test_in_days():
    assert [clock.in_days(n) for n in (0, 1, 3)] == ["today", "in 1 day", "in 3 days"]


def test_a_closed_posting_stays_visible_but_is_never_ranked(monkeypatch):
    at(monkeypatch, AFTER_REPLAI)
    assert "replai-pa" in {v.id for v in store.views()}
    assert [v.id for v in store.closed_views()] == ["replai-pa"]
    assert "replai-pa" not in {v.id for v in store.open_views()}
    assert "replai-pa" not in {v.id for v in store.ranked(as_of=store.data().profile["onboarded"])}
    assert "replai-pa" not in {v.id for v in store.top_matches()}
    assert store.matches().get("replai-pa") not in store.matches().ordered


def test_an_unsent_application_to_a_closed_role_leaves_the_live_ones(monkeypatch):
    at(monkeypatch, AFTER_REPLAI)
    live = {a["role"] for a in store.live_applications()}
    assert "replai-pa" not in live  # in progress, never sent
    assert {"lazarde-ba", "jpmorrow-strategy"} <= live  # sent: they stay
    assert "replai-pa" in {a["role"] for a in store.applications()}


def test_no_ranked_role_ever_counts_down_below_zero(monkeypatch):
    at(monkeypatch, "2026-10-19T09:00")
    assert all(clock.days_until(v.closes) >= 0 for v in store.ranked(include_new=True))


def test_home_widgets_show_open_postings_only(monkeypatch):
    at(monkeypatch, AFTER_REPLAI)
    app = AppTest.from_file(APP, default_timeout=120)
    app.session_state["stage"] = "app"
    app.session_state["home_guide_seen"] = True
    app.run()
    assert not app.exception
    page = "".join(x.value for x in app.markdown)
    assert "Monday 28 Sep" in page
    assert "Finish your Replai application" not in page  # carousel
    assert "1 closed, not shown" in page  # top matches
    strip = page[page.index('<div class="trk">'):]
    assert "Replai" not in strip[:strip.index("</div></div></div>", strip.rindex('class="mc"'))]
