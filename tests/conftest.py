"""Shared test setup.

The app's clock follows the machine's (core/clock.py). Tests hold it at the
moment the demo data was written for, `today` and `now` in data/demo.json, so
their deadlines and counts read the same whenever they run.
"""

from __future__ import annotations

import os

import pytest

from core import clock, store


@pytest.fixture(autouse=True, scope="session")
def demo_clock():
    """Session-wide, so module fixtures that run the app see it too."""
    d = store.data()
    before = os.environ.get(clock.PIN)
    os.environ[clock.PIN] = f"{d.today}T{d.now}"
    yield
    if before is None:
        del os.environ[clock.PIN]
    else:
        os.environ[clock.PIN] = before
