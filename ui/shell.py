"""The frame every screen shares: background glow, top bar, page header.

The top bar is the mockups' capsule navigation. Each tab is a native
`st.page_link`; the badge counts come from state, so "Matches 49" follows the
current eligible count.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st

from ui.html import BELL, MARK, SEARCH, html, md_icon

#: Four blurred glows, positioned as on the mockups' 1600 x 1000 stage.
_GLOW = (
    '<div class="bgx">'
    '<i style="width:620px;height:420px;left:-120px;top:-140px;background:#CFE3FB"></i>'
    '<i style="width:560px;height:380px;right:-100px;top:60px;background:#E4DDF7"></i>'
    '<i style="width:640px;height:360px;left:420px;bottom:-200px;background:#DDF0E6"></i>'
    '<i style="width:420px;height:300px;right:260px;bottom:-120px;background:#FBEBD5;opacity:.7"></i>'
    "</div>"
)

#: (key, label, page file). Order is the mockups' order.
NAV = [
    ("home", "Home", "views/home.py"),
    ("matches", "Matches", "views/matches.py"),
    ("applications", "Applications", "views/applications.py"),
    ("explore", "Explore", "views/explore.py"),
    ("profile", "Profile", "views/profile.py"),
]


def background() -> None:
    """Paint the glow behind the page."""
    html(_GLOW)


def brand() -> None:
    """The Applicable.ai lockup."""
    html(f'<div class="brand">{MARK}Applicable.ai</div>')


def topbar(active: str, counts: dict[str, int] | None = None) -> None:
    """Draw the top bar.

    Args:
        active: Key of the current tab in NAV ("" for none).
        counts: Badge per tab key, e.g. {"matches": 49}.
    """
    counts = counts or {}
    if st.session_state.get("flash"):
        st.toast(st.session_state.pop("flash"))
    background()
    with st.container(key="topbar"):
        brand()
        with st.container(key="cap"):
            for key, label, page in NAV:
                text = f"{label} *{counts[key]}*" if key in counts else label
                on = "-on" if key == active else ""
                with st.container(key=f"nav{on}-{key}"):
                    st.page_link(page, label=text)
        with st.container(key="tr"):
            _search()
            with st.popover(md_icon(BELL, "Notifications"), key="ib-bell"):
                html('<div style="font-size:13px;font-weight:560;padding:4px 2px">No new notifications</div>')
            with st.popover("GR", key="ib-av"):
                html(
                    '<div style="font-size:13px;font-weight:650">Giulia Rossi</div>'
                    '<div style="font-size:12px;color:#6E6E73;margin:2px 0 10px">Synthetic demo profile</div>'
                )
                st.page_link("views/profile.py", label="Your profile")
                st.page_link("views/onboarding.py", label="Restart onboarding")


def _search() -> None:
    """Search · ⌘K: jump straight to any role in the catalogue."""
    from core import store  # local: the shell must not import data at module load

    with st.popover(md_icon(SEARCH, "Search"), key="ib-search"):
        data = store.data()
        q = st.text_input("Search roles", placeholder="Company, role or city", key="search-q")
        hits = [
            o for o in data.roles
            if not q or q.lower() in f"{o.company} {o.title} {o.city}".lower()
        ][:8]
        for o in hits:
            st.page_link(
                "views/role.py",
                label=f"{o.title} · {o.company} · {o.city}",
                query_params={"id": o.id},
            )


@contextmanager
def header(title: str, meta: str) -> Iterator[None]:
    """The page title block (`.hi`). Widgets created inside go on the right.

    Args:
        title: The H1.
        meta: The grey line under it, as markup. The SYNTHETIC tag is added.
    """
    with st.container(key="hi"):
        html(
            f'<div class="hi-l"><h1>{title}</h1>'
            f'<div class="m"><span class="syn">SYNTHETIC</span>{meta}</div></div>'
        )
        with st.container(key="acts"):
            yield
