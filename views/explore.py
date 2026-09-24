"""Explore — the whole catalogue we track, under the same rules.

No mockup covers this screen; it reuses the Home match cards and the Matches
side panel. Every role is shown with its standing from core/rules.py,
including the excluded ones, so nothing is hidden without a reason.
"""

from __future__ import annotations

import streamlit as st

from core import clock, store
from ui import parts, shell
from ui.html import check_icon, esc, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("explore")

FILTERS = ["All", "Eligible", "To verify", "New today", "Excluded"]
qf = st.query_params.get("filter")
if qf == "new" and st.session_state.get("_x_qf") != qf:
    st.session_state["_x_qf"] = qf
    st.session_state["x-filter"] = "New today"

allv = sorted(store.views(), key=lambda v: (v.standing == "excluded", -v.score))
new_n = sum(1 for v in allv if v.get("new"))

shell.topbar("explore", store.nav_counts())
with shell.header(
    "Explore",
    f"<b>{len(allv)} roles</b> tracked here · same rules for every role · {new_n} new today",
):
    q = st.text_input("Search", placeholder="Search company, role or city", key="x-q",
                      value=st.query_params.get("city", ""))

with st.container(key="filters"):
    f = st.pills("Filter", FILTERS, default="All", key="x-filter", label_visibility="collapsed") or "All"


def keep(v) -> bool:
    if q and q.lower() not in f"{v.company} {v.title} {v.city}".lower():
        return False
    return {
        "All": True,
        "Eligible": v.standing == "eligible",
        "To verify": v.standing == "verify",
        "New today": bool(v.get("new")),
        "Excluded": v.standing == "excluded",
    }[f]


shown = [v for v in allv if keep(v)]
SEL = "x_sel"
if shown and st.session_state.get(SEL) not in [v.id for v in shown]:
    st.session_state[SEL] = shown[0].id


def card(v) -> str:
    sel = v.id == st.session_state.get(SEL)
    close, hot = clock.closes_line(v)
    if v.standing == "excluded":
        small, why = "Excluded", "✕ " + next(c.value for c in v.criteria if c.status == "not_met")
    else:
        small = "New" if v.get("new") else ("To verify" if v.standing == "verify" else "Priority")
        why = ("! " if v.get("highlight_kind") == "gap" else "✓ ") + v.highlight
    return (
        f'<div class="mc tile{" sel" if sel else ""}{" x2" if v.standing == "excluded" else ""}">'
        f'<div class="h">{logo(v.mono, v.bg, 36, 13)}<div class="sc">{v.shown if v.standing != "excluded" else "—"}<small>{small}</small></div></div>'
        f'<div class="t">{esc(v.title)}</div><div class="m">{esc(v.company)} · {esc(v.city)}</div>'
        f'<div class="why">{esc(why)}</div><div class="b" style="margin-top:auto"><i style="width:{v.shown if v.standing != "excluded" else 0}%"></i></div>'
        f'<div class="f"><span class="{"u" if hot else ""}">{esc(close)}</span><span>Verified today</span></div></div>'
    )


with st.container(key="main"):
    with st.container(key="gl-grid"):
        html(
            f'<div class="sh"><div><b>{f if f != "All" else "All roles"}</b><span>{len(shown)} shown · '
            "excluded roles stay visible, with the rule that removed them</span></div></div>"
        )
        with st.container(key="grid"):
            for v in shown:
                hit(f"x-{v.id}", card(v), f"Preview {v.company}", on_click=st.session_state.__setitem__, args=(SEL, v.id))
        if not shown:
            html('<div style="font-size:13px;color:var(--t2);margin-top:14px">No roles match. Try another filter.</div>')

    with st.container(key="pan-x"):
        if shown:
            v = next(x for x in shown if x.id == st.session_state[SEL])
            label = {"eligible": "Eligible", "verify": "To verify", "excluded": "Excluded"}[v.standing]
            chip = {"eligible": "g", "verify": "u", "excluded": "r"}[v.standing]
            html(
                f'<div class="pan"><div class="kk">{esc(v.company)} · {esc(v.city)} · {esc(v.mode)}</div>'
                f'<h3>{esc(v.title)}<span class="chip {chip}">{label}</span></h3></div>'
            )
            if v.standing != "excluded":
                html(
                    f'<div><div class="hero2"><div class="n">{v.shown}<small> /100</small></div>'
                    f'<div class="c">Priority score<br>{esc(clock.closes_line(v)[0])}</div></div>'
                    f'<div class="kstack">{parts.bars(v)}</div></div>'
                )
            rows = "".join(
                f'<div class="ck">{check_icon(c.status)}{esc(c.name)}<span class="s">{esc(c.value)}</span></div>'
                for c in v.criteria
            )
            html(f'<div class="lab">8 fixed criteria<span>{v.met} of 8 met</span></div><div class="box crit">{rows}</div>')
            with st.container(key="end-x"):
                html(f'<div class="gate box">{parts.gate(v)}</div>' if v.standing != "excluded" else "")
            with st.container(key="foot"):
                if st.button("Open role", key="open"):
                    st.switch_page("views/role.py", query_params={"id": v.id})
                if st.button("Save", type="primary", key="save", disabled=v.standing == "excluded"):
                    store.save_application(v.id, "saved")
                    st.toast(f"Saved · {v.company} · {v.title}")
