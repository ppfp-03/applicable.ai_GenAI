"""Home's intro guide: what the dashboard is for, part by part.

Two layers over the Home tab, neither of which moves anything on it:

- the intro sheet: a Liquid Glass panel (the onboarding sheet's look,
  ui/css/guide.css) shown the first time Home opens in a session. It says what
  Home is for and lists its four parts.
- the walkthrough: "Show me around" lights up one part at a time and explains,
  in a card beside it, what it is for and how to use it. The dim and the card's
  position come from the guided tour's script (ui/js/tour.js), which follows
  the `.aa-tour-mark` marker rendered here.

The "?" in Home's header opens the sheet again. Nothing shows before the app
stage: onboarding and the first-run tour have their own guidance.

The copy only restates what Home already does. Nothing here decides anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from core import store
from ui.html import esc, html
from ui.theme import page_css

SEEN = "home_guide_seen"
WALK = "home_guide_walk"
_TOUR_JS = Path(__file__).resolve().parent / "js" / "tour.js"


@dataclass(frozen=True)
class Part:
    #: The keyed container to light up, inside the Home tab.
    key: str
    name: str
    #: One line for the sheet.
    short: str
    #: The walkthrough card: what the part is for, and how to use it.
    what: str
    how: str


PARTS = [
    Part(
        "car",
        "Do this next",
        "The most useful things to do this week, one card at a time.",
        "The card in front is the next best action: an application about to close, today’s interview, "
        "a question only you can answer or new roles worth a look. The most urgent comes first.",
        "Use the arrows or the dots at the top right to see the other cards. Act on the card in front "
        "with its buttons; “Not now” or “Later” moves it back without losing it.",
    ),
    Part(
        "gl-tl",
        "Next two weeks",
        "Deadlines, interviews and events on one timeline.",
        "Everything dated in your search, from application deadlines to interviews, on one line. "
        "The “Now” marker shows where you are, so you can see what is coming before it is urgent.",
        "Click an event to bring its card to the front of the carousel.",
    ),
    Part(
        "gl-top",
        "Your top matches",
        "The roles that fit you best, ranked and explained.",
        "Only roles you are eligible for, or could be with one answer, are ranked, with the same rules "
        "for every role. Each card shows the match score, the main reason it fits or the gap to check, "
        "and when it closes.",
        "Scroll the strip for more roles. Open a card to see every check and where it comes from: "
        "your CV, the posting, your answers or a rule.",
    ),
    Part(
        "gl-apps",
        "Applications",
        "Where every application you started stands.",
        "The stages (saved, in progress, applied, interview) are a filter, each with its count; "
        "the one you pick lists its applications.",
        "Tap a stage to list its applications, tap an application to expand it and use its buttons, "
        "or “See all” for the full board.",
    ),
]


def _num(i: int) -> str:
    return f'<span class="hg-n">{i}</span>'


def _close() -> None:
    st.session_state[SEEN] = True


def _to(i: int | None) -> None:
    st.session_state[SEEN] = True
    st.session_state[WALK] = i


def reopen() -> None:
    """The header's "?": the sheet shows again."""
    st.session_state[SEEN] = False
    st.session_state[WALK] = None


def _sheet() -> None:
    page_css("guide")
    rows = "".join(
        f'<div class="hg-row">{_num(i + 1)}<div><b>{esc(p.name)}</b><span>{esc(p.short)}</span></div></div>'
        for i, p in enumerate(PARTS)
    )
    with st.container(key="guide"):
        with st.container(key="guide-card"):
            html(
                '<div class="gd hg">'
                '<div class="gd-k">Home · your week at a glance</div>'
                '<div class="gd-h">What this page is for</div>'
                '<div class="gd-p">Home brings together what needs you this week, so you can see what to do '
                "next without opening every tab. It has four parts:</div>"
                f'<div class="hg-list">{rows}</div></div>'
            )
            with st.container(key="hg-acts"):
                st.button("I’ll explore on my own", key="hg-close", on_click=_close)
                st.button("Show me around", key="hg-start", type="primary", on_click=_to, args=(0,))


def _walk(i: int) -> None:
    page_css("tour")
    p = PARTS[i]
    last = i == len(PARTS) - 1
    st.markdown(
        f'<div class="aa-tour-mark" data-sel=".st-key-tab-home .st-key-{p.key}" data-step="hg{i}"></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="tour"):
        dots = "".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(PARTS)))
        html(
            f'<div class="tr-k"><span>Home · {i + 1} of {len(PARTS)}</span><span class="tr-dots">{dots}</span></div>'
            f'<div class="tr-h">{esc(p.name)}</div><div class="tr-p">{esc(p.what)}</div>'
            f'<div class="tr-tip"><b>How to use it</b>{esc(p.how)}</div>'
        )
        with st.container(key="tour-acts"):
            if not last:
                st.button("Skip", key="hg-skip", type="tertiary", on_click=_to, args=(None,))
            if i > 0:
                st.button("Back", key="hg-back", on_click=_to, args=(i - 1,))
            if last:
                st.button("Done", key="hg-done", type="primary", on_click=_to, args=(None,))
            else:
                st.button("Next", key="hg-next", type="primary", on_click=_to, args=(i + 1,))
    with st.container(key="tour-js"):
        st.html(f"<script>{_TOUR_JS.read_text(encoding='utf-8')}</script>", unsafe_allow_javascript=True)


def render(shown: str) -> None:
    """Draw the sheet or the current walkthrough step over Home, if due.

    Args:
        shown: The tab the host brought to the front on this run.
    """
    if store.stage() != "app" or shown != "home":
        return
    page_css("home_guide")
    i = st.session_state.get(WALK)
    if i is not None:
        _walk(min(i, len(PARTS) - 1))
    elif not st.session_state.get(SEEN):
        _sheet()
