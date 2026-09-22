"""Today — the home screen.

Answers one question: what deserves my attention now. The page is ordered by
how soon it needs a decision, not by how interesting it is: what the band
counts, what to apply to, what to answer, and what a rule has ruled out.

Two rules from the approved direction govern the layout. The attention band
is three filters, not four KPIs -- every cell ends in something to do. And a
gap is named, never left as a number: "5 of 6 met" says nothing you can act
on, "1 to confirm: PowerPoint" does.
"""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from core import demo, ranking, state
from ui.components import (
    band_cell,
    eligibility_chip,
    gap_note,
    lead_card,
    mono_tile,
)

data = demo.load()
state.init(data)

ranked = ranking.rank(data.opportunities)
applying = [o for o in ranked if o.verdict == "apply"]
blocked = [o for o in ranked if o.verdict == "skip"]
questions = state.open_questions(data)
planned = state.hours_planned(data)
today = date.fromisoformat(data.today)

left, rail = st.columns([2.25, 1], gap="large")

with left:
    st.html(
        f'<div class="aa"><p class="aa-label">{today.strftime("%A %d %B")}</p>'
        f'<h1 class="aa-h-title" style="margin-top:7px">Good morning, '
        f'{escape(data.profile["name"].split()[0])}</h1></div>'
    )

    unlocks = sum(len(q.unlocks) for q in questions)
    lead_line = (
        f"{len(applying)} roles are worth your time this week."
        if not questions
        else f"{len(applying)} roles are worth your time this week. "
        f"One answer would change {unlocks} more."
    )
    st.html(f'<p class="aa aa-lead" style="margin-top:6px">{escape(lead_line)}</p>')

    # --- Attention band ---------------------------------------------------
    closing = [o for o in applying if o.deadline_days <= 7]
    fresh = [o for o in applying if (o.posted_days_ago or 99) <= 7]

    st.write("")
    band = st.columns(3, gap="small")
    with band[0]:
        st.html(
            band_cell(
                "Closing soon",
                len(closing),
                "within 7 days",
                f"{closing[0].company} closes in {closing[0].deadline_days} days"
                if closing
                else "Nothing closes this week",
            )
        )
    with band[1]:
        st.html(
            band_cell(
                "Needs verification",
                len(questions),
                "question open" if len(questions) == 1 else "questions open",
                f"One answer unlocks {unlocks} roles"
                if questions
                else "Nothing left to confirm",
                urgent=bool(questions),
            )
        )
    with band[2]:
        st.html(
            band_cell(
                "New this week",
                len(fresh),
                "posting read" if len(fresh) == 1 else "postings read",
                "All eligible" if fresh else "Nothing new since Monday",
            )
        )

    # --- The recompute card, when an answer has just moved something ------
    deltas = st.session_state.get(state.LAST_DELTA, [])
    if deltas:
        st.write("")
        with st.container(border=True, key="delta-card"):
            st.html('<p class="aa aa-label is-ai">✦ What your answer changed</p>')
            for d in deltas:
                opp = data.opportunity(d["opportunity_id"])
                before_v, before_p, before_r = d["before"]
                after_v, after_p, after_r = d["after"]
                st.html(
                    f'<div class="aa" style="display:flex;align-items:center;'
                    f'gap:14px;margin-top:12px">{mono_tile(opp.company, 40)}'
                    f'<div style="flex-grow:1"><p style="margin:0;font-weight:700">'
                    f"{escape(opp.title)}</p>"
                    f'<p class="aa-small">{escape(opp.company)}</p></div>'
                    f'<div style="text-align:right"><span style="font:800 15px/1 '
                    f'var(--font-display);color:var(--ink-muted)">{before_p}</span>'
                    f'<span style="color:var(--go);font-weight:800"> → </span>'
                    f'<span style="font:800 22px/1 var(--font-display);color:var(--go)">'
                    f"{after_p}</span>"
                    f'<p class="aa-small" style="margin-top:4px">#{before_r} → '
                    f"#{after_r}</p></div></div>"
                )
                for what, how in d["changes"]:
                    st.html(
                        f'<div class="aa" style="display:flex;justify-content:'
                        f'space-between;gap:16px;font-size:13.5px;padding:6px 0 0 54px">'
                        f"<span>{escape(what)}</span>"
                        f'<span style="font-weight:700;color:var(--go)">{escape(how)}'
                        f"</span></div>"
                    )
            st.button("Got it", on_click=state.dismiss_delta, key="dismiss-delta")

    # --- Apply next -------------------------------------------------------
    st.html(
        '<div class="aa" style="display:flex;align-items:baseline;'
        'justify-content:space-between;margin:30px 0 12px">'
        '<h2 class="aa-h">Apply next</h2>'
        '<p class="aa-small">Eligibility checked, then ranked</p></div>'
    )

    for index, opp in enumerate(applying[:4]):
        if index == 0:
            with st.container(border=True, key="lead-card"):
                st.html(lead_card(opp))
                note, action = st.columns([2, 1], vertical_alignment="center")
                with note:
                    st.html(f'<div class="aa">{gap_note(opp.requirements)}</div>')
                with action:
                    # One primary button per view: this is it.
                    st.button(
                        "Added to my week" if state.in_week(opp.id) else "Add to my week",
                        key=f"add-{opp.id}",
                        type="primary",
                        disabled=state.in_week(opp.id),
                        on_click=state.add_to_week,
                        args=(opp.id,),
                        use_container_width=True,
                    )
        else:
            with st.container(border=True):
                body, action = st.columns([4, 1], vertical_alignment="center")
                with body:
                    st.html(
                        f'<div class="aa" style="display:flex;gap:14px;'
                        f'align-items:flex-start">{mono_tile(opp.company, 40)}'
                        f'<div style="min-width:0">'
                        f'<div class="aa-row" style="gap:8px">'
                        f"{eligibility_chip(opp.eligibility_status)}"
                        f'<span class="aa-h-sm">{escape(opp.title)}</span></div>'
                        f'<p class="aa-small" style="margin-top:5px">'
                        f"{escape(opp.company)} · {escape(opp.city)} · closes in "
                        f"{opp.deadline_days} d · {escape(opp.contract)}</p>"
                        f'<div style="margin-top:8px">{gap_note(opp.requirements)}</div>'
                        f"</div></div>"
                    )
                with action:
                    st.html(
                        f'<div class="aa aa-pri" style="align-items:center">'
                        f'<span class="num" style="font-size:20px">{opp.priority}</span>'
                        f'<span class="cap">priority</span></div>'
                    )
                    st.button(
                        "Added" if state.in_week(opp.id) else "Add",
                        key=f"add-{opp.id}",
                        disabled=state.in_week(opp.id),
                        on_click=state.add_to_week,
                        args=(opp.id,),
                        use_container_width=True,
                    )

    if len(applying) > 4:
        st.page_link(
            "views/opportunities.py",
            label=f"See all {len(applying)} you are eligible for",
            icon=":material/arrow_forward:",
        )

    # --- Not now ----------------------------------------------------------
    if blocked:
        st.write("")
        with st.expander(
            f"{len(blocked)} not now — each with the rule that blocks it"
        ):
            for opp in blocked:
                reason = next(
                    (c for c in opp.eligibility if c.status == "conflict"), None
                )
                st.html(
                    f'<div class="aa" style="display:flex;gap:12px;align-items:'
                    f'flex-start;padding:10px 0;border-top:1px solid var(--line)">'
                    f"{mono_tile(opp.company, 32)}"
                    f'<div style="min-width:0"><p style="margin:0;font-weight:700;'
                    f'font-size:14px">{escape(opp.title)}</p>'
                    f'<p class="aa-small">{escape(opp.company)} · '
                    f"{escape(opp.city)}</p></div>"
                    f'<p class="aa-small" style="margin-left:auto;text-align:right;'
                    f'max-width:340px">{escape(reason.explanation) if reason else ""}'
                    f"</p></div>"
                )

with rail:
    if questions:
        question = questions[0]
        with st.container(border=True, key="question-card"):
            st.html(
                f'<div class="aa"><div style="display:flex;align-items:baseline;'
                f'justify-content:space-between">'
                f'<p class="aa-label" style="color:var(--clarify)">Open questions</p>'
                f'<span class="aa-small" style="color:var(--clarify);font-weight:700">'
                f"{len(questions)}</span></div>"
                f'<p style="margin:12px 0 0;font:600 17px/23px var(--font-display)">'
                f"{escape(question.text)}</p></div>"
            )
            choice = st.pills(
                question.text,
                question.options,
                key=f"pills-{question.id}",
                label_visibility="collapsed",
            )
            st.html(
                f'<p class="aa aa-small" style="font-size:12px">10 seconds · '
                f"unlocks {len(question.unlocks)} role{'' if len(question.unlocks) == 1 else 's'} · "
                f"{escape(question.impact)}</p>"
            )
            if choice:
                st.button(
                    "Save answer",
                    key=f"save-{question.id}",
                    type="primary",
                    on_click=state.answer,
                    args=(data, question, choice),
                    use_container_width=True,
                )
            if len(questions) > 1:
                rest = " · ".join(q.text.rstrip("?") for q in questions[1:])
                st.html(f'<p class="aa aa-small">Then: {escape(rest)}</p>')

    with st.container(border=True):
        st.html(
            f'<div class="aa"><p class="aa-label">This week</p>'
            f'<p style="margin:10px 0 0;font:700 14px/1 var(--font-sans)">'
            f'{planned:g} <span style="color:var(--ink-muted);font-weight:600">'
            f"of {data.hours_budget:g} h planned</span></p></div>"
        )
        st.progress(min(planned / data.hours_budget, 1.0))
        left_hours = max(data.hours_budget - planned, 0)
        st.html(
            f'<p class="aa aa-small">'
            f"{'Your week is full — anything else goes to next week.' if left_hours <= 0 else f'{left_hours:g} h still free.'}"
            f"</p>"
        )
        st.page_link(
            "views/tracker.py", label="Open tracker", icon=":material/arrow_forward:"
        )
