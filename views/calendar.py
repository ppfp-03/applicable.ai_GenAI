"""Calendar — every date that matters, as a month or a week.

No mockup covers this screen. It is Home's calendar (ui/home_expand.py)
drawn as a page: the timeline's events plus the close date of every role
the user saved or started, and the agenda of the day picked.
"""

from __future__ import annotations

import streamlit as st

from core import clock, store
from ui import home_expand, shell, tabs
from ui.theme import page_css

page_css("calendar")

today = clock.today()
events = home_expand.calendar_events(store.data().timeline, store.applications(), today)
ahead = [e for e in events if not e.past]
closing = sum(1 for e in ahead if e.role)


def go_card(i: int) -> None:
    """Bring Home's carousel card `i` forward and open Home."""
    st.session_state["home_card"] = i  # views/home.py CARD
    tabs.go("home")


shell.topbar("calendar", store.nav_counts())
with shell.header(
    "Your calendar",
    f"<b>{len(ahead)} upcoming</b> · {closing} close dates of roles you saved or started",
):
    pass

home_expand.calendar_view("cal", go_card)
