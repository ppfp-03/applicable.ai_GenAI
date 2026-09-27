"""The Calendar tab's layout, organised as Outlook's calendar.

Views/calendar.py draws the page; the helpers here are pure, so the views,
the navigation and the grouping can be tested without a browser.

The events are Home's (`home_expand.calendar_events`). Most carry no time of
day: a close date or a decision is a date, so, as in Outlook, those sit in
the all-day band. An event whose label names a time ("interview 15:00") is
placed on the time grid. No time is ever made up.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from ui.home_expand import CalEvent, shift_month, week_of

#: The view switch, in Outlook's order.
VIEWS = ("Day", "Work week", "Week", "Month")

#: Calendars in the side pane: (key, label, swatch).
CATS = (
    ("interview", "Interviews", "#0071E3"),
    ("close", "Close dates", "#E3A03A"),
    ("application", "Applications", "#30A14E"),
    ("other", "Other", "#8E8E93"),
)

#: The time grid's default hours, widened to fit any timed event and now.
DAY_START, DAY_END = 8, 20

_TIME = re.compile(r"\s*\b([01]?\d|2[0-3]):([0-5]\d)\b")


def time_of(e: CalEvent) -> time | None:
    """The time of day the label names, if any."""
    m = _TIME.search(e.label)
    return time(int(m.group(1)), int(m.group(2))) if m else None


def title_of(e: CalEvent) -> str:
    """The label without its time, which the grid shows on its own."""
    return _TIME.sub("", e.label).strip()


def category(e: CalEvent) -> str:
    """Which calendar in the side pane an event belongs to."""
    label = e.label.lower()
    if "interview" in label:
        return "interview"
    if label.endswith("closes"):
        return "close"
    if label.startswith("applied"):
        return "application"
    return "other"


def view_days(view: str, picked: date) -> list[date]:
    """The columns of the Day, Work week and Week views."""
    if view == "Day":
        return [picked]
    week = week_of(picked)
    return week[:5] if view == "Work week" else week


def step(view: str, picked: date, first: date, n: int) -> tuple[date, date]:
    """‹ and ›: the day picked and the month shown, `n` pages on.

    Month moves the month and keeps the day picked; the other views move the
    day, and the month follows it.
    """
    if view == "Month":
        return picked, shift_month(first, n)
    picked = picked + timedelta(days=n if view == "Day" else 7 * n)
    return picked, picked.replace(day=1)


def title(view: str, picked: date, first: date) -> tuple[str, str]:
    """The command bar's title, as (bold part, light part)."""
    if view == "Month":
        return first.strftime("%B"), str(first.year)
    if view == "Day":
        return f"{picked:%A} {picked.day} {picked:%B}", str(picked.year)
    days = view_days(view, picked)
    a, b = days[0], days[-1]
    if a.month == b.month:
        return f"{a.day} – {b.day} {b.strftime('%B')}", str(b.year)
    return f"{a.day} {a:%b} – {b.day} {b:%b}", str(b.year)


def hours(events: list[CalEvent], now: datetime | None = None) -> tuple[int, int]:
    """First and last hour of the time grid: the working day, widened to
    show every timed event (one hour long) and the current time."""
    start, end = DAY_START, DAY_END
    for t in filter(None, (time_of(e) for e in events)):
        start, end = min(start, t.hour), max(end, min(t.hour + 1 + (t.minute > 0), 24))
    if now is not None:
        start, end = min(start, now.hour), max(end, now.hour + 1)
    return start, end
