"""The five capsule screens on one page, so switching between them is instant.

Home, Matches, Applications, Explore and Profile are each a script in
`views/`. Instead of being separate Streamlit pages, which Streamlit tears
down and rebuilds on every switch, all five run on every rerun, each inside
its own container (`.st-key-tab-<name>`). The browser shows one and hides the
others (`ui/js/nav.js`), the way an iOS tab bar keeps every tab alive.

Each tab still has its own URL (/, /matches, ...): `app.py` registers one
page per tab, and every one of them runs `host()` with that tab in front.
Question, Role and Onboarding stay ordinary pages.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st

TABS = ("home", "matches", "applications", "explore", "profile")

#: Every page by name, filled in by app.py before any screen runs.
PAGES: dict = {}

_VIEWS = Path(__file__).resolve().parents[1] / "views"
_RUNNING = "tabs_running"   # the tab whose script is running, while host() runs it
_GOTO = "tabs_goto"         # a tab to bring forward on this run
_NONCE = "tabs_nonce"       # bumped on every go(), so the browser follows it
_PARAMS = "tabs_params"     # {tab: {name: value}} passed by go()


def running() -> str | None:
    """The tab whose script is running, or None outside the tab host."""
    return st.session_state.get(_RUNNING)


def page(name: str):
    """The registered page for a screen name, for `st.page_link`."""
    return PAGES[name]


def param(name: str, default: str | None = None) -> str | None:
    """A value passed to the running tab by go(), else from the URL."""
    tab = running()
    passed = st.session_state.get(_PARAMS, {}).get(tab, {}) if tab else {}
    return passed.get(name) or st.query_params.get(name) or default


def go(name: str, **params: str) -> None:
    """Open a screen.

    A tab is brought forward in place: the page reruns but is not torn down.
    Any other screen is a real page change, with params in its URL.
    """
    if name in TABS:
        st.session_state.setdefault(_PARAMS, {})[name] = params
        st.session_state[_GOTO] = name
        st.session_state[_NONCE] = st.session_state.get(_NONCE, 0) + 1
        if running() is not None:
            st.rerun()
        st.switch_page(PAGES[name])
    st.switch_page(PAGES[name], query_params=params or None)


def host(front: str) -> None:
    """Run the five tabs, with `front` shown unless go() asked for another."""
    from core import store
    from ui import shell
    from ui.html import esc

    shown = st.session_state.pop(_GOTO, None) or front
    st.session_state[_RUNNING] = None

    # Which tab is in front, for nav.js. The nonce tells it when go() asked for
    # a tab; otherwise the browser's own choice stands. Until the script runs,
    # the style keeps the other tabs hidden.
    hidden = ",".join(f"html:not([data-tab]) .st-key-tab-{t}" for t in TABS if t != shown)
    st.markdown(
        f'<div class="aa-tabs" data-active="{esc(shown)}" data-nonce="{st.session_state.get(_NONCE, 0)}"></div>'
        f"<style>{hidden}{{display:none}}</style>",
        unsafe_allow_html=True,
    )
    try:
        shell.topbar(shown, store.nav_counts())
        for tab in TABS:
            st.session_state[_RUNNING] = tab
            with st.container(key=f"tab-{tab}"):
                runpy.run_path(str(_VIEWS / f"{tab}.py"), run_name="__main__")
    finally:
        st.session_state[_RUNNING] = None
