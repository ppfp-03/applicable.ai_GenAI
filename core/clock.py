"""The demo clock.

The demo is pinned to Thursday 24 Sep 2026, 10:55, the moment the mockups
show. Every "closes in 3 days" is computed from this date, never from the
machine's, so the demo reads the same whenever it is run.
"""

from __future__ import annotations

from datetime import date, datetime

from core import store


def today() -> date:
    """The demo's today."""
    return date.fromisoformat(store.data().today)


def now() -> datetime:
    """The demo's now, at the start of the session."""
    d = store.data()
    return datetime.fromisoformat(f"{d.today}T{d.now}")


def days_until(iso: str) -> int:
    """Whole days from today to an ISO date."""
    return (date.fromisoformat(iso) - today()).days


def closes_line(role) -> tuple[str, bool]:
    """The deadline as the cards phrase it, and whether it is urgent.

    Within ten days it counts down ("Closes in 3 d"); later it shows the
    date ("Closes 15 Oct").
    """
    n = days_until(role.closes)
    if n <= 9:
        return f"Closes in {n} d", True
    return f"Closes {role.closes_label}", False


def posted_line(role) -> str:
    """"Posted today", "2 days ago" ..."""
    n = role.posted_days_ago
    return "Posted today" if n == 0 else "Posted yesterday" if n == 1 else f"{n} days ago"
