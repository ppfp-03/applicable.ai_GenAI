"""Applicable.ai — entry point.

Sets up the page, injects the design system's stylesheet once, and hands over
to `st.navigation`. Pages live in `pages/` and are declared here so the sidebar
order is explicit rather than alphabetical.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# The ingestion packages (oi.*) live under src/.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ui.theme import inject, is_dark  # noqa: E402  (after sys.path setup)

st.set_page_config(
    page_title="Applicable.ai",
    page_icon="static/applicable-mark.svg",
    layout="centered",
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

pages = [
    st.Page("pages/your_week.py", title="Your week", default=True),
    st.Page("pages/explore.py", title="Explore"),
    st.Page("pages/tracker.py", title="Tracker"),
    st.Page("pages/compare.py", title="Compare"),
    st.Page("pages/profile.py", title="My profile"),
]

page = st.navigation(pages, position="sidebar")

# Inject after navigation resolves: anything written before `.run()` belongs
# to no page and is discarded, which leaves the markup unstyled.
inject()

page.run()
