"""The Calendar tab's views, navigation and calendars (ui/calendar_page.py)."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest
import streamlit as st

from core import store
from ui import calendar_page as cp
from ui import home_expand as hx

D = store.data()
TODAY = date.fromisoformat(D.today)  # Thursday 24 Sep 2026


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def ev(label: str) -> hx.CalEvent:
    return hx.CalEvent(day=TODAY, label=label, color="#000", past=False)


def test_only_a_time_named_in_the_label_puts_an_event_on_the_time_grid() -> None:
    assert cp.time_of(ev("J.P. Morrow interview 15:00")) == time(15, 0)
    assert cp.title_of(ev("J.P. Morrow interview 15:00")) == "J.P. Morrow interview"
    assert cp.time_of(ev("Replai closes")) is None
    timed = [e for e in hx.calendar_events(D.timeline, store.applications(), TODAY) if cp.time_of(e)]
    assert [e.label for e in timed] == ["J.P. Morrow interview 15:00"]


def test_every_event_belongs_to_one_calendar() -> None:
    assert cp.category(ev("J.P. Morrow interview 15:00")) == "interview"
    assert cp.category(ev("Replai closes")) == "close"
    assert cp.category(ev("Applied · Lazarde")) == "application"
    assert cp.category(ev("J.P. Morrow · decision expected")) == "other"
    keys = {k for k, _, _ in cp.CATS}
    for e in hx.calendar_events(D.timeline, store.applications(), TODAY):
        assert cp.category(e) in keys


def test_views_show_one_day_five_weekdays_or_the_week() -> None:
    assert cp.view_days("Day", TODAY) == [TODAY]
    work = cp.view_days("Work week", TODAY)
    assert [d.strftime("%a") for d in work] == ["Mon", "Tue", "Wed", "Thu", "Fri"]
    week = cp.view_days("Week", TODAY)
    assert len(week) == 7 and week[0] == date(2026, 9, 21) and week[-1] == date(2026, 9, 27)


def test_arrows_move_a_page_of_the_view() -> None:
    first = TODAY.replace(day=1)
    assert cp.step("Day", TODAY, first, 1) == (date(2026, 9, 25), first)
    assert cp.step("Week", TODAY, first, 1) == (date(2026, 10, 1), date(2026, 10, 1))
    assert cp.step("Work week", TODAY, first, -1) == (date(2026, 9, 17), first)
    assert cp.step("Month", TODAY, first, 1) == (TODAY, date(2026, 10, 1))


def test_titles_name_the_range_shown() -> None:
    first = TODAY.replace(day=1)
    assert cp.title("Month", TODAY, first) == ("September", "2026")
    assert cp.title("Week", TODAY, first) == ("21 – 27 September", "2026")
    assert cp.title("Day", TODAY, first) == ("Thursday 24 September", "2026")
    assert cp.title("Week", date(2026, 10, 1), first) == ("28 Sep – 4 Oct", "2026")


def test_the_time_grid_widens_to_fit_events_and_now() -> None:
    assert cp.hours([ev("Call 15:00")]) == (8, 20)
    assert cp.hours([ev("Call 07:30"), ev("Dinner 21:15")]) == (7, 23)
    assert cp.hours([], datetime(2026, 9, 24, 22, 5)) == (8, 23)
