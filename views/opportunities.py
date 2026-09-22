"""Opportunities — the list and the one you are reading, side by side.

The list keeps its place while the detail changes, which is the whole point:
deciding between two roles ranked next to each other is the work, and a page
that forgets where you were makes you do it from memory.

The detail is always the same eight sections in the same order — header,
decision, why it ranks here, eligibility, requirements, warnings, how we
know, actions — so the second opportunity you read is faster than the first.

Eligibility and fit never borrow each other's language. The left half of the
decision strip can stop an application; the right half only orders what is
already allowed.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from core import demo, ranking, state
from ui.components import (
    decision_strip,
    eligibility_chip,
    eligibility_rows,
    factor_rows,
    gap_note,
    hl,
    list_row,
    mono_tile,
    req_line,
    req_open,
    source_line,
    warning_rows,
)

data = demo.load()
state.init(data)

ranked = ranking.rank(data.opportunities)
ranks = state.ranks(data)

VIEWS = {
    "Top": lambda o: o.verdict == "apply",
    "Needs verification": lambda o: any(
        r.status == "confirm" for r in o.requirements
    )
    or o.eligibility_status == "confirm",
    "Conflicts": lambda o: o.eligibility_status == "conflict",
    "All": lambda o: True,
}

# --- Toolbar --------------------------------------------------------------

head, view, filters = st.columns([2, 3, 1], vertical_alignment="center")
with head:
    st.html(
        f'<div class="aa"><h1 class="aa-h" style="font-size:19px">Opportunities</h1>'
        f'<p class="aa-small">{len(data.opportunities)} read against your '
        f"profile</p></div>"
    )
with view:
    chosen = st.segmented_control(
        "View",
        list(VIEWS),
        default="Top",
        key="opp-view",
        label_visibility="collapsed",
    )
with filters:
    with st.popover("Filters", use_container_width=True):
        st.multiselect(
            "Country",
            sorted({o.city for o in data.opportunities}),
            key="filter-city",
            placeholder="Any city",
        )
        st.select_slider(
            "Closes within",
            options=[7, 14, 30, 60, 90],
            value=90,
            key="filter-days",
            format_func=lambda d: f"{d} days",
        )

shown = [o for o in ranked if VIEWS[chosen or "All"](o)]
cities = st.session_state.get("filter-city") or []
within = st.session_state.get("filter-days") or 90
shown = [
    o
    for o in shown
    if (not cities or o.city in cities) and o.deadline_days <= within
]

st.html('<div class="aa" style="height:6px"></div>')

listing, detail = st.columns([1, 1.9], gap="medium")

# --- The list -------------------------------------------------------------

with listing:
    current = st.session_state.get(state.SELECTED)
    if not shown:
        st.html(
            '<div class="aa aa-empty"><p class="aa-h-sm">Nothing matches</p>'
            '<p class="aa-small" style="margin-top:6px">Widen the filters, or '
            "add a country in Preferences.</p></div>"
        )
    for opp in shown:
        with st.container(key=f"row-{opp.id}"):
            st.html(list_row(opp, selected=opp.id == current))
            # The row is the button: the markup draws it, and a transparent
            # native button laid over it carries the click to Python.
            st.button(
                f"Open {opp.title} at {opp.company}",
                key=f"open-{opp.id}",
                on_click=state.select,
                args=(opp.id,),
                use_container_width=True,
            )

# --- The detail -----------------------------------------------------------

opp = state.selected(data)
with detail:
    if opp is None:
        st.info("Pick an opportunity on the left.")
        st.stop()

    length = f"{opp.contract_months} months" if opp.contract_months else ""
    posted = (
        f"posted {opp.posted_days_ago} d ago"
        if opp.posted_days_ago is not None
        else "no date on the posting"
    )
    meta = " · ".join(
        p
        for p in (
            opp.company,
            opp.city,
            opp.contract,
            length,
            f"closes in {opp.deadline_days} days",
            posted,
        )
        if p
    )
    st.html(
        f'<div class="aa" style="display:flex;gap:16px;align-items:flex-start">'
        f"{mono_tile(opp.company, 56, 'brand')}"
        f'<div style="flex-grow:1;min-width:0">'
        f'<h1 class="aa-h-title" style="font-size:26px;line-height:32px">'
        f"{escape(opp.title)}</h1>"
        f'<p class="aa-small" style="margin-top:5px">{escape(meta)}</p>'
        f"</div></div>"
    )

    add, compare, _ = st.columns([1, 1, 2])
    with add:
        st.button(
            "Added to my week" if state.in_week(opp.id) else "Add to my week",
            key=f"detail-add-{opp.id}",
            type="primary",
            disabled=state.in_week(opp.id) or opp.verdict == "skip",
            on_click=state.add_to_week,
            args=(opp.id,),
            use_container_width=True,
        )
    with compare:
        st.button(
            "Compare",
            key=f"detail-compare-{opp.id}",
            use_container_width=True,
            on_click=lambda oid=opp.id: st.session_state[state.COMPARE].append(oid)
            if oid not in st.session_state[state.COMPARE]
            else None,
        )

    st.write("")
    st.html(decision_strip(opp, ranks[opp.id], len(data.opportunities)))

    # --- Why it is ranked here -------------------------------------------
    st.html(
        '<div class="aa" style="margin-top:24px">'
        '<p class="aa-sech">Why it is ranked here</p>'
        '<p class="aa-small">Four factors, equal weight. None of them decides '
        "eligibility.</p></div>"
    )
    st.html(factor_rows(opp, data.factor_labels))

    # --- Eligibility ------------------------------------------------------
    st.html(
        '<div class="aa" style="margin-top:24px">'
        '<p class="aa-sech">Eligibility · decided by rules, never by a model</p>'
        "</div>"
    )
    st.html(eligibility_rows(opp))

    # --- Requirements and gaps -------------------------------------------
    met = [r for r in opp.requirements if r.status == "met"]
    st.html(
        f'<div class="aa" style="margin-top:24px">'
        f'<p class="aa-sech">Requirements and gaps</p>'
        f'<div style="margin-top:6px">{gap_note(opp.requirements)}</div></div>'
    )
    sources = st.toggle("Show sources", key=f"src-{opp.id}")

    for req in opp.requirements:
        if req.status != "met":
            st.html(req_open(req))
            if req.question_id:
                question = next(
                    (q for q in data.questions if q.id == req.question_id), None
                )
                if question and question.id not in st.session_state[state.ANSWERS]:
                    choice = st.pills(
                        question.text,
                        question.options,
                        key=f"detail-pills-{question.id}",
                    )
                    if choice:
                        st.button(
                            "Save answer",
                            key=f"detail-save-{question.id}",
                            on_click=state.answer,
                            args=(data, question, choice),
                        )
    for req in met:
        st.html(req_line(req, show_sources=sources))

    # --- Warnings ---------------------------------------------------------
    if opp.warnings:
        st.html(
            '<div class="aa" style="margin-top:24px">'
            '<p class="aa-sech">Warnings · about the posting, not about you</p>'
            "</div>"
        )
        st.html(warning_rows(opp))

    # --- How we know ------------------------------------------------------
    st.write("")
    with st.expander("How we know — method, rules version, what is uncertain"):
        st.html(
            f'<div class="aa"><p class="aa-small">The verdict comes from the '
            f"eligibility rules; the priority is the sum of four equally "
            f"weighted factors. No model output is added to either.</p>"
            f'<div class="aa-fact"><span class="k">Why this fits</span>'
            f"<span>{hl(opp.why)}</span></div>"
            f'<div class="aa-fact"><span class="k">Rules version</span>'
            f'<span>{source_line(opp.eligibility[0].source)}</span></div>'
            f'<div class="aa-fact"><span class="k">Weights</span>'
            f"<span>25% each · config/ranking.json</span></div></div>"
        )

    # --- Compare ----------------------------------------------------------
    compare_ids = [i for i in st.session_state.get(state.COMPARE, []) if i != opp.id]
    if compare_ids:
        other = data.opportunity(compare_ids[-1])
        st.write("")
        with st.container(border=True):
            st.html(
                f'<div class="aa"><p class="aa-sech">Side by side</p>'
                f'<p style="margin-top:8px">{escape(opp.title)} at '
                f"{escape(opp.company)} against {escape(other.title)} at "
                f"{escape(other.company)}.</p></div>"
            )
            a, b = st.columns(2)
            for column, item in ((a, opp), (b, other)):
                with column:
                    st.html(
                        f'<div class="aa">{eligibility_chip(item.eligibility_status)}'
                        f'<p style="margin:10px 0 0;font-weight:700">{item.priority}'
                        f' <span class="aa-small">priority</span></p>'
                        f'<p class="aa-small">closes in {item.deadline_days} d · '
                        f"{sum(h for _, h in item.before_you_apply):g} h of work "
                        f"before sending</p>"
                        f'<div style="margin-top:8px">{gap_note(item.requirements)}'
                        f"</div></div>"
                    )
            st.button(
                "Clear comparison",
                key="clear-compare",
                on_click=lambda: st.session_state[state.COMPARE].clear(),
            )
