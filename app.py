"""Applicable.ai — entry point.

Sets up the page, injects the design system's stylesheet once, and hands over
to `st.navigation`. Pages are declared here, grouped the way the information
architecture groups them: decide, track, you. The order is explicit rather
than alphabetical, because it is the order of the work.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# The ingestion packages (oi.*) live under src/.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core import demo, state  # noqa: E402  (after sys.path setup)
from ui.components import set_monograms  # noqa: E402
from ui.theme import inject, is_dark  # noqa: E402

st.set_page_config(
    page_title="Applicable.ai",
    page_icon="static/applicable-mark.svg",
    # The opportunities list and its detail pane need the width; every page
    # caps its own content, so wide here does not mean sprawling there.
    layout="wide",
    initial_sidebar_state="expanded",
)

# The wordmark is dark ink, so on a dark sidebar it needs the light variant.
st.logo(
    "static/applicable-lockup-on-dark.svg"
    if is_dark()
    else "static/applicable-lockup.svg",
    icon_image="static/applicable-mark.svg",
    size="large",
)

data = demo.load()
set_monograms(data.company_monograms)
state.init(data)

pages = {
    "Decide": [
        st.Page("views/today.py", title="Today", icon=":material/today:", default=True),
        st.Page(
            "views/opportunities.py",
            title="Opportunities",
            icon=":material/explore:",
        ),
    ],
    "Track": [
        st.Page("views/tracker.py", title="Tracker", icon=":material/view_kanban:"),
    ],
    "You": [
        st.Page("views/profile.py", title="Profile", icon=":material/person:"),
        st.Page("views/preferences.py", title="Preferences", icon=":material/tune:"),
        st.Page("views/onboarding.py", title="Set up", icon=":material/upload_file:"),
    ],
}

page = st.navigation(pages, position="sidebar")

# Inject after navigation resolves: anything written before `.run()` belongs
# to no page and is discarded, which leaves the markup unstyled.
inject()

page.run()
