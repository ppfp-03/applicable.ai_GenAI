"""The app's clock.

Today is the machine's today, read each time it is asked, so a posting whose
closing date has passed is never shown as open. Every "closes in 3 days" is
computed from it.

Setting APPLICABLE_NOW (an ISO time, e.g. "2026-09-24T10:55") holds the clock
there. Tests hold it at the moment the demo data was written for (`today` and
`now` in data/demo.json, see tests/conftest.py), so they read the same
whenever they run.
"""

from __future__ import annotations

import os
from datetime import date, datetime

#: The environment variable that holds the clock at a fixed moment.
PIN = "APPLICABLE_NOW"


def now() -> datetime:
    """The current local time, or the moment APPLICABLE_NOW holds it at."""
    pinned = os.environ.get(PIN)
    return datetime.fromisoformat(pinned) if pinned else datetime.now()


def today() -> date:
    """Today's date."""
    return now().date()


def days_until(iso: str) -> int:
    """Whole days from today to an ISO date."""
    return (date.fromisoformat(iso) - today()).days


def is_closed(role) -> bool:
    """Whether a role's closing date has passed. It stays open on the day itself."""
    return days_until(role.closes) < 0


def in_days(n: int) -> str:
    """How far off a day is, counted from today: "today", "in 1 day", "in 3 days"."""
    return "today" if n == 0 else f"in {n} day{'s' if n != 1 else ''}"


def closes_line(role) -> tuple[str, bool]:
    """The deadline as the cards phrase it, and whether it is urgent.

    Within ten days it counts down ("Closes in 3 d", "Closes today"); later
    it shows the date ("Closes 15 Oct"). Once passed it says how long ago
    ("Closed yesterday", "Closed 3 d ago"), and is no longer urgent.
    """
    n = days_until(role.closes)
    if n < 0:
        return ("Closed yesterday" if n == -1 else f"Closed {-n} d ago"), False
    if n == 0:
        return "Closes today", True
    if n <= 9:
        return f"Closes in {n} d", True
    return f"Closes {role.closes_label}", False


def posted_line(role) -> str:
    """"Posted today", "2 days ago" ..."""
    n = role.posted_days_ago
    return "Posted today" if n == 0 else "Posted yesterday" if n == 1 else f"{n} days ago"
