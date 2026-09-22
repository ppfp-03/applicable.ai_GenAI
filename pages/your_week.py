"""Your week — the home screen.

Answers one question: what do I work on this week? A single column, at most
three decisions, then the highest-impact question, then everything that did
not make the cut, collapsed to one line but never hidden.

Density rules from design-system/README.md govern this page: one primary
button, three cards before the scroll, three sections. When there is more to
say, it moves behind a gesture rather than shrinking.

Class names come from design-system/components/bundle.css. The reference
markup is design-system/previews/ScreenYourWeek.html.
"""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from core import demo
from core.ranking import rank
from ui.components import card_top, hl, requirement_bar

data = demo.load()
first_name = data.profile["name"].split()[0]

# --- Header -------------------------------------------------------------

today = date.fromisoformat(data.today)
applying = [o for o in rank(data.opportunities) if o.verdict == "apply"]

st.html(
    f'<div class="aa-label">{today.strftime("%A %d %B")}</div>'
    f'<h1 class="aa-h-title" style="margin-top:6px">Good morning, '
    f"{escape(first_name)}</h1>"
    f'<p class="aa-lead" style="margin-top:6px">{len(applying)} applications '
    f"fit your {data.hours_budget:g} hours this week.</p>"
)

if data.changes:
    st.html(
        f'<div class="aa-notice" style="margin-top:20px">'
        f'<span class="dot"></span><span>{escape(data.changes)}</span></div>'
    )

# --- Apply this week ----------------------------------------------------

st.html('<div class="sec"><h2 class="aa-h">Apply this week</h2></div>')

for index, opp in enumerate(applying):
    with st.container(border=True):
        # The section heading already says "Apply this week", so the card
        # does not repeat the verdict chip.
        st.html(card_top(opp, show_verdict=False))
        left, right = st.columns([3, 1], vertical_alignment="center")
        with left:
            st.html(requirement_bar(opp.requirements))
        with right:
            # Only the first card carries the primary button: one primary
            # action per view, so the eye has a single place to land.
            st.button(
                "Add to my week",
                key=f"add-{opp.id}",
                type="primary" if index == 0 else "secondary",
                use_container_width=True,
            )

# --- Answer first -------------------------------------------------------

open_questions = [q for q in data.questions if q.unlocks]
if open_questions:
    # Only the highest-impact question appears here; the rest stay on the
    # opportunities they belong to, so the home screen asks at most once.
    question = max(open_questions, key=lambda q: len(q.unlocks))

    head, impact = st.columns([3, 1], vertical_alignment="bottom")
    with head:
        st.html('<h2 class="aa-h">Answer first</h2>')
    with impact:
        st.html(
            f'<div class="aa-small" style="text-align:right">'
            f"{escape(question.impact)}</div>"
        )

    with st.container(border=True):
        st.html(
            f'<p class="question" style="margin-bottom:4px">'
            f"{escape(question.text)}</p>"
            f'<p class="aa-small" style="margin:0">{hl(question.reason)}</p>'
        )
        st.pills(
            question.text,
            question.options,
            key=f"answer-{question.id}",
            label_visibility="collapsed",
        )

# --- Not for now --------------------------------------------------------

if data.not_for_now_count:
    # Deprioritised, never hidden: the count stays on screen and the reasons
    # are one gesture away.
    with st.expander(f"{data.not_for_now_count} Not for now, each with its reason"):
        st.html(
            '<p class="aa-small">Each of these is blocked by one requirement, '
            "shown with the rule or quote that blocks it.</p>"
        )
