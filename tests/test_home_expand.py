"""Home's full views: the calendar's events and grid, the sort orders, the
board, and the ⤢ button on every widget."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import store
from ui import home_expand as hx

D = store.data()
TODAY = date.fromisoformat(D.today)
APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def events() -> list[hx.CalEvent]:
    return hx.calendar_events(D.timeline, store.applications(), TODAY)


def test_the_calendar_keeps_every_timeline_event() -> None:
    labels = [e.label for e in events()]
    for e in D.timeline["events"]:
        assert e["label"] in labels


def test_the_calendar_adds_the_close_date_of_saved_and_started_roles() -> None:
    evs = events()
    for a in store.applications():
        r = a["r"]
        day = date.fromisoformat(r.closes)
        named = [e for e in evs if e.day == day and e.label.startswith(r.company)]
        if a["stage"] in hx.OPEN:
            assert len(named) == 1, r.company  # once, even when the timeline has it too
        elif not any(e["label"].startswith(r.company) and e["date"] == r.closes for e in D.timeline["events"]):
            assert not named, r.company


def test_role_closes_open_the_role_and_come_in_date_order() -> None:
    evs = events()
    added = [e for e in evs if e.role]
    assert added and all(e.color == hx.CLOSE_COLOR for e in added)
    assert all(D.role(e.role).closes == e.day.isoformat() for e in added)
    assert [e.day for e in evs] == sorted(e.day for e in evs)


def test_the_month_grid_is_six_monday_first_weeks() -> None:
    weeks = hx.month_weeks(2026, 10)
    assert len(weeks) == 6 and all(len(w) == 7 for w in weeks)
    assert all(w[0].weekday() == 0 for w in weeks)
    assert date(2026, 10, 1) in weeks[0] and date(2026, 10, 31) in [d for w in weeks for d in w]


def test_week_of_and_shift_month() -> None:
    days = hx.week_of(TODAY)
    assert days[0].weekday() == 0 and len(days) == 7 and TODAY in days
    assert hx.shift_month(date(2026, 12, 1), 1) == date(2027, 1, 1)
    assert hx.shift_month(date(2026, 1, 1), -1) == date(2025, 12, 1)


def test_sort_orders() -> None:
    tops = store.top_matches()
    # "Score" sorts by the Priority score the cards show (the one Matches ranking's raw score).
    score = lambda v: store.priority(v.id) or -1  # noqa: E731
    assert [score(v) for v in hx.sort_matches(tops, "Score")] == sorted((score(v) for v in tops), reverse=True)
    assert [v.closes for v in hx.sort_matches(tops, "Closing soon")] == sorted(v.closes for v in tops)
    assert [v.city for v in hx.sort_matches(tops, "City")] == sorted(v.city for v in tops)
    assert hx.sort_matches(tops, None) == hx.sort_matches(tops, "Score")


def test_the_board_holds_every_application_once() -> None:
    apps = store.applications()
    board = hx.by_stage(apps)
    assert list(board) == list(hx.BOARD)
    assert sorted(a["role"] for rows in board.values() for a in rows) == sorted(a["role"] for a in apps)


def test_every_widget_has_its_expand_button() -> None:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    at.session_state["home_guide_seen"] = True
    at.run()
    assert not at.exception
    keys = {b.key for b in at.button if b.key}
    assert {"ib-x-car", "ib-x-tl", "ib-x-top", "ib-x-apps"} <= keys


@pytest.mark.parametrize("key, marker", [
    ("ib-x-tl", "Coming up"),
    ("ib-x-car", "worth your time this week"),
    ("ib-x-top", "same rules for every role"),
    ("ib-x-apps", "from saved to interview"),
])
def test_each_expand_button_opens_its_view(key: str, marker: str) -> None:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    at.session_state["home_guide_seen"] = True
    at.run()
    at.button(key=key).click().run()
    assert not at.exception
    assert marker in "".join(m.value for m in at.markdown)
