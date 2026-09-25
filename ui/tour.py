"""The guided tour: the first look at the app after onboarding.

It runs on the real screens. Each step brings one tab forward, dims the page
around one part of it and explains, in a small card beside it, what that
part is for and how to make it yours. The card's buttons are native; the dim
and the card's position are drawn in the browser by `ui/js/tour.js`, which
follows a marker this module renders (`.aa-tour-mark`) and does nothing once
the marker is gone.

The tour shows while the session is at the "tour" stage (core/store.py).
Finishing or skipping it opens the app; "Replay the tour" in the avatar menu
starts it again.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core import store
from ui import tabs
from ui.html import esc, html
from ui.theme import page_css

_JS = Path(__file__).resolve().parent / "js" / "tour.js"
STEP = "tour_step"

#: (tab, element to light up, title, what it is, how to make it yours).
STEPS = [
    ("home", ".aa-nav",
     "Five places, one bar",
     "Home is your week. Matches ranks what fits, Applications tracks what you’ve started, "
     "Explore goes beyond your shortlist, Profile is what we know about you.",
     "Swipe across the bar or use it like tabs — it’s always at the top."),
    ("home", ".st-key-tab-home .st-key-car",
     "Your week, one thing at a time",
     "The card in front is the next best action: the application closing soonest, "
     "today’s interview, or a question only you can answer.",
     "Use the arrows to see the rest. “Not now” moves a card back without losing it."),
    ("matches", ".st-key-tab-matches .st-key-gl-top5",
     "Your top five, explained",
     "Only roles you’re eligible for, or could be with one answer, get ranked. "
     "Every score is the same four factors with the same weights for every role.",
     "Open a role to see each check and its source: your CV, the posting, your answers or a rule."),
    ("applications", ".st-key-tab-applications .st-key-ap-main",
     "Everything you’ve started",
     "Saved, in progress, applied, interview: each application moves along as you do.",
     "Move an application to its next stage, or add a note for later."),
    ("explore", ".st-key-tab-explore .st-key-gl-grid",
     "Beyond your shortlist",
     "Every role we’ve checked, including the ones outside your top five, with the same rules applied.",
     "Filter by city or role type and save anything worth a second look."),
    ("profile", ".st-key-tab-profile .st-key-gl-prof",
     "Make it yours",
     "This is everything we read from your CV and everything you told us.",
     "Correct a field, add a country or change what matters to you — your ranking recalculates instantly."),
]


def _to(i: int) -> None:
    st.session_state[STEP] = i


def _done() -> None:
    store.set_stage("app")
    st.session_state.pop(STEP, None)


def render(shown: str) -> None:
    """Draw the current step over the tab host, if the tour is on.

    Args:
        shown: The tab the host brought to the front on this run.
    """
    if store.stage() != "tour":
        return
    i = min(st.session_state.setdefault(STEP, 0), len(STEPS) - 1)
    tab, target, title, body, tip = STEPS[i]
    if tab != shown:
        tabs.go(tab)
        return
    page_css("tour")
    last = i == len(STEPS) - 1
    st.markdown(
        f'<div class="aa-tour-mark" data-sel="{esc(target)}" data-step="{i}"></div>', unsafe_allow_html=True
    )
    with st.container(key="tour"):
        dots = "".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(STEPS)))
        html(
            f'<div class="tr-k"><span>{i + 1} of {len(STEPS)}</span><span class="tr-dots">{dots}</span></div>'
            f'<div class="tr-h">{esc(title)}</div><div class="tr-p">{esc(body)}</div>'
            f'<div class="tr-tip"><b>Make it yours</b>{esc(tip)}</div>'
        )
        with st.container(key="tour-acts"):
            if not last:
                st.button("Skip tour", key="tour-skip", type="tertiary", on_click=_done)
            if i > 0:
                st.button("Back", key="tour-back", on_click=_to, args=(i - 1,))
            if last:
                if st.button("Go to my week", key="tour-end", type="primary"):
                    _done()
                    tabs.go("home")
            else:
                st.button("Next", key="tour-next", type="primary", on_click=_to, args=(i + 1,))
    with st.container(key="tour-js"):
        st.html(f"<script>{_JS.read_text(encoding='utf-8')}</script>", unsafe_allow_javascript=True)
