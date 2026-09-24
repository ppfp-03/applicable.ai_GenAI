"""Applications — every application, by stage.

No mockup covers this screen, so it is built from the vocabulary the mockups
share: a summary strip, glass lanes of tiles, and the side panel for the
selected item. Stages and counts come from the session, so an application
started anywhere in the product appears here at once.
"""

from __future__ import annotations

import streamlit as st

from core import clock, store
from ui import parts, shell
from ui.html import CK, WN, esc, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("applications")

STAGES = [
    ("saved", "Saved", "#C7C7CC"),
    ("progress", "In progress", "#0071E3"),
    ("applied", "Applied", "#48484A"),
    ("interview", "Interview", "#30A14E"),
]
STAGE_NAME = {k: n for k, n, _ in STAGES}
CHECKLIST = {
    "saved": [("CV tailored", False), ("Cover letter", False), ("Eligibility checked", True)],
    "progress": [("CV tailored", True), ("Eligibility checked", True), ("Cover letter to review", False)],
    "applied": [("CV + cover letter sent", True), ("Confirmation received", True), ("Reply", False)],
    "interview": [("3 prep notes ready", True), ("Role and team researched", True), ("Prepare 1 case question", False)],
}

apps = store.applications()
SEL = "apps_sel"
qid = st.query_params.get("id")
if qid and any(a["role"] == qid for a in apps):
    st.session_state[SEL] = qid
st.session_state.setdefault(SEL, next((a["role"] for a in apps if a["stage"] == "interview"), apps[0]["role"]))
sc = store.stage_counts()
total = sum(sc.values())

shell.topbar("applications", store.nav_counts())
urgent = min(apps, key=lambda a: clock.days_until(a["r"].closes) if a["stage"] in ("saved", "progress") else 999)
with shell.header(
    "Your applications",
    f"<b>{total} applications</b> · {sc['interview']} interview today · "
    f"{esc(urgent['r'].company)} closes in {clock.days_until(urgent['r'].closes)} days",
):
    if st.button("Explore roles", key="explore"):
        st.switch_page("views/explore.py")

with st.container(key="strip"):
    bar = "".join(f'<i style="flex:{max(sc[k], .2)};background:{c}"></i>' for k, _, c in STAGES)
    leg = "".join(f'<span><i style="background:{c}"></i>{n} <b>{sc[k]}</b></span>' for k, n, c in STAGES)
    html(f'<div class="astrip gl"><span class="s-t">Pipeline</span><div class="abar">{bar}</div><div class="aleg">{leg}</div></div>')


def card(a: dict) -> str:
    r = a["r"]
    v = store.view(r)
    sel = a["role"] == st.session_state[SEL]
    prog = ""
    if a["stage"] == "progress" and a.get("progress"):
        done, of = a["progress"]
        prog = f'<div class="pb"><i style="width:{done / of * 100:.0f}%"></i></div>'
    close, hot = clock.closes_line(r)
    foot = close if a["stage"] in ("saved", "progress") else STAGE_NAME[a["stage"]]
    return (
        f'<div class="ac tile{" sel" if sel else ""}"><div class="h">{logo(r.mono, r.bg, 32, 12, 9)}'
        f'<div style="min-width:0"><div class="t">{esc(r.title)}</div><div class="m">{esc(r.company)} · {esc(r.city)}</div></div></div>'
        f'<div class="n">{esc(a["note"])}</div>{prog}'
        f'<div class="f"><span class="{"u" if hot and a["stage"] in ("saved", "progress") else ""}">{esc(foot)}</span>'
        f"<span>Score {v.shown}</span></div></div>"
    )


with st.container(key="main"):
    with st.container(key="lanes"):
        for k, name, color in STAGES:
            with st.container(key=f"gl-lane-{k}"):
                html(f'<div class="lh"><i style="background:{color}"></i>{name}<span>{sc[k]}</span></div>')
                for a in [a for a in apps if a["stage"] == k]:
                    hit(f"app-{a['role']}", card(a), f"Select {a['r'].company}",
                        on_click=st.session_state.__setitem__, args=(SEL, a["role"]))

    a = next((a for a in apps if a["role"] == st.session_state[SEL]), apps[0])
    r = a["r"]
    v = store.view(r)
    stage_color = dict((k, c) for k, _, c in STAGES)[a["stage"]]
    with st.container(key="pan-a"):
        html(
            f'<div class="pan"><div class="kk"><i style="background:{stage_color}"></i>{STAGE_NAME[a["stage"]]} · {esc(r.company)}</div>'
            f'<h3>{esc(r.title)}</h3></div>'
            f'<div class="big2">{logo(r.mono, r.bg, 46, 16, 12)}<div><div class="tt">{v.shown}<span style="font-size:13px;color:var(--t3);font-weight:560"> /100 priority</span></div>'
            f'<div class="mm">{esc(r.city)} · {esc(r.mode)} · {esc(clock.closes_line(r)[0])}</div></div></div>'
        )
        items = CHECKLIST[a["stage"]]
        if a["stage"] == "progress" and a.get("progress"):
            done = a["progress"][0]
            items = [(t, i < done) for i, (t, _) in enumerate(CHECKLIST["progress"])]
        rows = "".join(
            f'<div class="ck"><span class="ci{"" if ok else " a"}">{CK if ok else WN}</span>{esc(t)}'
            f'<span class="s">{"Done" if ok else "To do"}</span></div>'
            for t, ok in items
        )
        html(f'<div class="lab">Checklist<span>{sum(ok for _, ok in items)} of {len(items)}</span></div><div class="box ckl">{rows}</div>')
        html(
            '<div class="lab">Eligibility<span>Fixed rules</span></div>'
            f'<div class="gate box" style="display:flex;align-items:center;gap:10px;padding:12px 14px;font-size:12.5px">{parts.gate(v)}</div>'
        )
        html('<div class="lab">Stage<span>Move when something happens</span></div>')
        with st.container(key="stage"):
            keys = [k for k, _, _ in STAGES]
            new = st.selectbox("Stage", keys, index=keys.index(a["stage"]), format_func=STAGE_NAME.get, key=f"stage-{r.id}")
            if new != a["stage"]:
                store.save_application(r.id, new)
                st.toast(f"{r.company} moved to {STAGE_NAME[new]}")
                st.rerun()
        with st.container(key="anote"):
            html('<div class="lab">Notes<span>Only you see these</span></div>')
            st.text_area("Notes", key=f"note-{r.id}", placeholder="Recruiter name, what you discussed, next step…")
        with st.container(key="end-a"):
            pass
        with st.container(key="foot"):
            if st.button("Open role", key="open"):
                st.switch_page("views/role.py", query_params={"id": r.id})
            first, _ = a["actions"]
            if st.button(first, type="primary", key="act"):
                st.toast(f"{first} · {r.company}")
