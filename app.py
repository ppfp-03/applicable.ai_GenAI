"""Applicable.ai — entry point.

Sets up the page, links the shared stylesheet, and hands over to
`st.navigation`. Navigation is hidden: the capsule in the top bar
(ui/shell.py) is the only way around, as in the mockups. The question,
role and onboarding screens are reached from inside the product rather than
from the capsule.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# The ingestion packages (oi.*) live under src/.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core import store  # noqa: E402  (after sys.path setup)
from ui.theme import inject  # noqa: E402

st.set_page_config(
    page_title="Applicable.ai",
    page_icon="static/applicable-mark.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject()
store.init()

pages = [
    st.Page("views/home.py", title="Home", url_path="home", default=True),
    st.Page("views/matches.py", title="Matches", url_path="matches"),
    st.Page("views/applications.py", title="Applications", url_path="applications"),
    st.Page("views/explore.py", title="Explore", url_path="explore"),
    st.Page("views/profile.py", title="Profile", url_path="profile"),
    st.Page("views/question.py", title="One quick question", url_path="question"),
    st.Page("views/role.py", title="Role", url_path="role"),
    st.Page("views/onboarding.py", title="Onboarding", url_path="onboarding"),
]

st.navigation(pages, position="hidden").run()
