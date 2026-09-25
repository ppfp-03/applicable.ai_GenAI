"""Applicable.ai — entry point.

Sets up the page, links the shared stylesheet, and hands over to
`st.navigation`. Navigation is hidden: the capsule in the top bar
(ui/shell.py) is the only way around, as in the mockups. The question,
role and onboarding screens are reached from inside the product rather than
from the capsule.

The five capsule tabs share one host (ui/tabs.py) that runs them all, so
switching tab happens in the browser. Each still has its own URL: one page
per tab, each bringing its own tab to the front.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# The ingestion packages (oi.*) live under src/.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core import store  # noqa: E402  (after sys.path setup)
from ui import tabs  # noqa: E402
from ui.theme import inject  # noqa: E402

st.set_page_config(
    page_title="Applicable.ai",
    page_icon="static/applicable-mark.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject()
# KIMI_API_KEY and friends, for CV extraction. Variables already set in the
# environment win; a missing .env leaves extraction to fail visibly.
load_dotenv(Path(__file__).resolve().parent / ".env")
store.init()



def _tab(name: str):
    """A page that runs the tab host with `name` in front."""

    def run() -> None:
        tabs.host(name)

    run.__name__ = f"tab_{name}"
    return run


tabs.PAGES.update(
    home=st.Page(_tab("home"), title="Home", url_path="home", default=True),
    matches=st.Page(_tab("matches"), title="Matches", url_path="matches"),
    applications=st.Page(_tab("applications"), title="Applications", url_path="applications"),
    explore=st.Page(_tab("explore"), title="Explore", url_path="explore"),
    profile=st.Page(_tab("profile"), title="Profile", url_path="profile"),
    question=st.Page("views/question.py", title="One quick question", url_path="question"),
    role=st.Page("views/role.py", title="Role", url_path="role"),
    onboarding=st.Page("views/onboarding.py", title="Onboarding", url_path="onboarding"),
)

st.navigation(list(tabs.PAGES.values()), position="hidden").run()
