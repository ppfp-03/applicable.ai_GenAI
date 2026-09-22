"""Tracker — what you send this week, and what each outcome taught you.

Four stages and an hours budget, kept from the design system. The budget is
the reason the weekly list is finite, so it leads the page rather than
sitting in a corner.

The last lane is the one that earns its place: an outcome with nothing
learned from it is just a record. When the same requirement blocks twice, the
page says so and offers the one action that would change it.
"""

from __future__ import annotations

from collections import Counter
from html import escape

import streamlit as st

from core import demo, state
from ui.components import mono_tile

data = demo.load()
state.init(data)

STAGES = [
    ("shortlisted", "Shortlisted"),
    ("preparing", "Preparing"),
    ("sent", "Sent"),
    ("outcome", "Outcome"),
]

planned = state.hours_planned(data)

head, budget = st.columns([2, 1], vertical_alignment="bottom")
with head:
    st.html(
        '<div class="aa"><h1 class="aa-h-title">Tracker</h1>'
        '<p class="aa-lead" style="margin-top:6px">What you send this week, and '
        "what each outcome taught you.</p></div>"
    )
with budget:
    st.html(
        f'<div class="aa"><p style="margin:0;font:700 14px/1 var(--font-sans);'
        f'text-align:right">{planned:g} <span style="color:var(--ink-muted);'
        f'font-weight:600">of {data.hours_budget:g} h planned</span></p></div>'
    )
    st.progress(min(planned / data.hours_budget, 1.0))

st.write("")
lanes = st.columns(4, gap="small")

# Cards the user added this session join the lane they belong to, so the
# board is the state of the app rather than a copy of the file.
entries = list(data.tracker)
tracked = {e["opportunity_id"] for e in entries}
for oid in st.session_state.get(state.WEEK, []):
    if oid not in tracked:
        first = data.opportunity(oid).before_you_apply
        entries.append(
            {
                "stage": "preparing",
                "opportunity_id": oid,
                "next": first[0][0].lower() if first else "start",
                "done": 0,
                "total": len(first),
            }
        )

for column, (stage, title) in zip(lanes, STAGES):
    items = [e for e in entries if e["stage"] == stage]
    with column, st.container(key=f"lane-{stage}"):
        st.html(
            f'<div class="aa" style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:0 4px 8px">'
            f'<span class="aa-label">{title}</span>'
            f'<span class="aa-small">{len(items)}</span></div>'
        )
        if not items:
            st.html(
                '<div class="aa" style="border:1px dashed var(--line-control);'
                'border-radius:14px;padding:14px;text-align:center">'
                '<p class="aa-small" style="margin:0">Nothing here</p></div>'
            )
        for entry in items:
            opp = data.opportunity(entry["opportunity_id"])
            with st.container(border=True):
                if "outcome" in entry:
                    tail = (
                        f'<p class="aa-small" style="margin-top:8px">'
                        f'<b style="color:var(--go)">{escape(entry["outcome"])}</b>'
                        f"</p>"
                        if entry.get("good")
                        else f'<p class="aa-small" style="margin-top:8px">'
                        f'{escape(entry["outcome"])} · learned: '
                        f'<b>{escape(entry.get("learned", ""))}</b></p>'
                    )
                elif "sent_on" in entry:
                    tail = (
                        f'<p class="aa-small" style="margin-top:8px">Sent '
                        f'<b>{escape(entry["sent_on"])}</b> · '
                        f'{escape(entry["state"])}</p>'
                    )
                else:
                    tail = (
                        f'<p class="aa-small" style="margin-top:8px">Next: '
                        f'<b>{escape(entry["next"])}</b> · '
                        f"{opp.deadline_days} d</p>"
                    )
                st.html(
                    f'<div class="aa" style="display:flex;gap:10px">'
                    f"{mono_tile(opp.company, 32)}"
                    f'<div style="min-width:0">'
                    f'<p style="margin:0;font-weight:700;font-size:14px;'
                    f'line-height:19px">{escape(opp.title)}</p>'
                    f'<p class="aa-small" style="font-size:12px">'
                    f"{escape(opp.company)}</p>{tail}</div></div>"
                )
                st.selectbox(
                    "Stage",
                    [t for _, t in STAGES],
                    index=[s for s, _ in STAGES].index(entry["stage"]),
                    key=f"stage-{opp.id}",
                    label_visibility="collapsed",
                )

# --- What the outcomes taught us -----------------------------------------

blocked_by = Counter(
    req.ask
    for entry in entries
    if entry.get("good") is False
    for req in data.opportunity(entry["opportunity_id"]).requirements
    if req.status == "conflict"
)
if blocked_by:
    ask, times = blocked_by.most_common(1)[0]
    st.write("")
    with st.container(border=True, key="learned-card"):
        st.html(
            f'<div class="aa"><p class="aa-label is-ai">✦ What your outcomes '
            f"taught us</p>"
            f'<p style="margin:8px 0 0;font-size:15px;line-height:24px">'
            f"“{escape(ask)}” is what closed "
            f"{times} of your finished applications. It is the one thing on "
            f"your profile that would change the most verdicts.</p></div>"
        )
        st.page_link("views/profile.py", label="Open profile", icon=":material/arrow_forward:")
