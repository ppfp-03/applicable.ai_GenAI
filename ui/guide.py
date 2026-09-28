"""Onboarding guidance: what each step is for, before the user does it.

Two layers, drawn over the mockup's stage without moving anything on it:

- the intro sheet: a Liquid Glass panel shown the first time a step opens,
  saying what you'll do there, why it matters and how long it takes. Step 1's
  sheet is the journey map: the whole onboarding in three phases.
- the guidance line: the footer's "Step N of 6 · …", which keeps the why in
  one line once the sheet is closed. Its "?" button opens the sheet again.

The copy only restates what the product already does. Nothing here decides
anything: views/onboarding.py still owns every step and every gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from ui.html import esc, html

SEEN = "ob_seen"
_JS = (Path(__file__).resolve().parent / "js" / "guide.js").read_text(encoding="utf-8")


@dataclass(frozen=True)
class Guide:
    title: str
    what: str
    why: str
    time: str
    #: The footer's short form of `why`.
    line: str


GUIDE = {
    "1": Guide(
        "Start with your CV",
        "Upload your CV as a PDF. We read it for you.",
        "Everything we check comes from it, so there are no forms to fill in.",
        "About 30 seconds",
        "Your CV is the starting point: every check comes from it",
    ),
    "2": Guide(
        "Check what we read",
        "Review your profile and declare where you can work.",
        "Every field links back to your CV. Work authorization decides which roles you’re eligible for.",
        "About 1 minute",
        "Every field links back to your CV · work authorization decides eligibility",
    ),
    "3b": Guide(
        "Tell us what you’d enjoy",
        "Swipe short stories about real work: right if you’d enjoy it, left if not, up if you’re not sure.",
        "Your likes suggest role types and industries. Nothing counts until you confirm it in the next step.",
        "About 1 minute",
        "Your swipes only suggest preferences · you confirm them next",
    ),
    "3a": Guide(
        "Confirm what matters",
        "Set how much each preference matters to you.",
        "Only what you confirm here shapes your ranking.",
        "About 30 seconds",
        "Only what you confirm here shapes your ranking",
    ),
    "4": Guide(
        "Your shortlist takes shape",
        "Your top matches are checked one by one.",
        "Some of them need a single answer from you before they can be confirmed.",
        "About 20 seconds",
        "Some of your top matches need one answer",
    ),
    "5": Guide(
        "One question",
        "Answer the one thing your CV doesn’t say.",
        "One answer updates one field of your profile and can unlock roles.",
        "About 10 seconds",
        "One answer updates one field",
    ),
    "6": Guide(
        "Your ranking is ready",
        "See your roles ranked, each with its score.",
        "Open a role to see why it fits, or start your first application.",
        "Whenever you’re ready",
        "Your shortlist is ready · open a role to see why it fits",
    ),
}

#: The journey map on step 1's sheet: (phase, steps it covers, what happens).
JOURNEY = [
    ("Your CV", ("1", "2"), "We read it, you check it"),
    ("What you enjoy", ("3b", "3a"), "Swipe, then confirm"),
    ("Your shortlist", ("4", "5", "6"), "Ranked and explained"),
]
JOURNEY_TIME = "About 4 minutes"

#: Row icons, drawn in the accent (ui/palette.py maps it to orange).
_ICONS = {
    "what": '<svg width="16" height="16" viewBox="0 0 16 16"><path d="M3 8.5l3 3 7-7" stroke="#0071E3" '
            'stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "why": '<svg width="16" height="16" viewBox="0 0 16 16"><path d="M8 2.2 9.3 6.7 13.8 8 9.3 9.3 8 13.8 6.7 9.3 '
           '2.2 8 6.7 6.7z" fill="#0071E3"/></svg>',
    "time": '<svg width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5.6" stroke="#0071E3" '
            'stroke-width="1.6" fill="none"/><path d="M8 5v3.2l2 1.3" stroke="#0071E3" stroke-width="1.6" '
            'fill="none" stroke-linecap="round"/></svg>',
}


def _seen() -> set[str]:
    return st.session_state.setdefault(SEEN, set())


def is_open(step: str) -> bool:
    """Whether the step's sheet shows: the first time the step opens, or on "?"."""
    return step not in _seen()


def close(step: str) -> None:
    st.session_state[SEEN] = _seen() | {step}


def reopen(step: str) -> None:
    st.session_state[SEEN] = _seen() - {step}


def line(step: str, num: int, total: int) -> str:
    """The footer's guidance line for a step."""
    return f"<b>Step {num} of {total}</b> · {esc(GUIDE[step].line)}"


def _journey(step: str) -> str:
    cur = next(i for i, (_, steps, _) in enumerate(JOURNEY) if step in steps)
    phases = []
    for i, (name, _, sub) in enumerate(JOURNEY):
        cls = "on" if i == cur else "done" if i < cur else ""
        phases.append(
            f'<div class="gd-ph {cls}"><span class="n">{i + 1}</span>'
            f'<b>{esc(name)}</b><small>{esc(sub)}</small></div>'
        )
    return f'<div class="gd-map">{"".join(phases)}</div>'


def _row(kind: str, label: str, text: str) -> str:
    return (
        f'<div class="gd-row"><span class="ic">{_ICONS[kind]}</span>'
        f'<div><div class="k">{label}</div><div class="v">{esc(text)}</div></div></div>'
    )


def sheet(step: str, num: int, total: int) -> None:
    """Draw the step's intro sheet over the page, if it is open."""
    if not is_open(step):
        return
    g = GUIDE[step]
    first = step == "1"
    with st.container(key="guide"):
        with st.container(key="guide-card"):
            head = (
                f'<div class="gd-k">Welcome · {JOURNEY_TIME.lower()}</div>'
                '<div class="gd-h">Here’s how it works</div>'
                '<div class="gd-p">Three short phases, and you check everything before it’s used.</div>'
                + _journey(step)
                + f'<div class="gd-sep"></div><div class="gd-k">Now · step {num} of {total}</div>'
                if first else
                f'<div class="gd-k">Step {num} of {total}</div>'
            )
            html(
                f'<div class="gd{" gd-first" if first else ""}">{head}'
                f'<div class="gd-h{" sm" if first else ""}">{esc(g.title)}</div>'
                + _row("what", "What you’ll do", g.what)
                + _row("why", "Why it matters", g.why)
                + _row("time", "Time", g.time)
                + "</div>"
            )
            st.button("Let’s start" if first else "Got it", key="guide-ok", type="primary",
                      on_click=close, args=(step,), width="stretch")
    with st.container(key="guide-js"):
        st.html(f"<script>{_JS}</script>", unsafe_allow_javascript=True)


def help_button(step: str) -> None:
    """The footer's "?": opens the step's sheet again."""
    st.button("?", key="guide-open", help="What is this step for?", on_click=reopen, args=(step,))
