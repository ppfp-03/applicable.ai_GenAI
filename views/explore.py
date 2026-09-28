"""Explore — the whole catalogue we track, under the same rules.

No mockup covers this screen; it reuses the Home match cards and the Matches
side panel. Every role is shown with its standing from the canonical engine,
including the excluded ones, so nothing is hidden without a reason.

New postings come only from the controlled "Simulated ingestion event"
(FR-10), run from the header; every posting it added is labelled as such.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core import clock, store
from ui import choice, parts, shell, tabs
from ui.html import check_icon, esc, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("explore")
PAGER_JS = (Path(__file__).resolve().parents[1] / "ui" / "js" / "pager.js").read_text(encoding="utf-8")

SIM = d.simulated_event["label"]
NEW = "Simulated event"
FILTERS = ["All", "Eligible", "To verify", NEW, "Excluded"]
qf = tabs.param("filter")
if qf == "new" and st.session_state.get("_x_qf") != qf:
    st.session_state["_x_qf"] = qf
    st.session_state["x-filter"] = NEW

# Closed roles stay listed, after the open ones, so they read as gone.
allv = sorted(store.views(), key=lambda v: (clock.is_closed(v), v.standing == "excluded", -v.score))
new_n = sum(1 for v in allv if store.is_simulated(v))
ran = store.simulated_event_ran()

shell.topbar("explore", store.nav_counts())
with shell.header(
    "Explore",
    f"<b>{len(allv)} roles</b> tracked here · same rules for every role · "
    + (f"{new_n} added by a {SIM.lower()}" if ran else f"{SIM.lower()} not run"),
):
    if not ran:
        st.button(f"Run {SIM.lower()}", type="primary", key="x-sim", on_click=store.run_simulated_event)
    q = st.text_input("Search", placeholder="Search company, role or city", key="x-q",
                      value=tabs.param("city", ""))

with st.container(key="filters"):
    f = choice.pills("Filter", FILTERS, default="All", key="x-filter", label_visibility="collapsed") or "All"


def keep(v) -> bool:
    if q and q.lower() not in f"{v.company} {v.title} {v.city}".lower():
        return False
    return {
        "All": True,
        "Eligible": v.standing == "eligible",
        "To verify": v.standing == "verify",
        NEW: store.is_simulated(v),
        "Excluded": v.standing == "excluded",
    }[f]


shown = [v for v in allv if keep(v)]

# Three rows of five cards a page, so the grid never runs past the side panel.
PER = 15
PG = "x_page"
pages = max(1, -(-len(shown) // PER))
if st.session_state.get("_x_view") != (f, q):
    st.session_state["_x_view"] = (f, q)
    st.session_state[PG] = 0
st.session_state[PG] = min(st.session_state.get(PG, 0), pages - 1)
page = shown[st.session_state[PG] * PER:(st.session_state[PG] + 1) * PER]

SEL = "x_sel"
if page and st.session_state.get(SEL) not in [v.id for v in page]:
    st.session_state[SEL] = page[0].id


def go_page(n: int) -> None:
    """Turn to page n and preview its first role."""
    st.session_state[PG] = n
    st.session_state[SEL] = shown[n * PER].id


def page_nums(cur: int, n: int) -> list[int | None]:
    """Google-style run: first, last and the pages around the current one; None is a gap."""
    if n <= 7:
        return list(range(n))
    keep_ = sorted({0, n - 1, cur - 1, cur, cur + 1} & set(range(n)))
    out: list[int | None] = []
    for i in keep_:
        if out and i - out[-1] > 1:
            out.append(i - 1 if i - out[-1] == 2 else None)
        out.append(i)
    return out


def card(v) -> str:
    sel = v.id == st.session_state.get(SEL)
    close, hot = clock.closes_line(v)
    if v.standing == "excluded":
        small, why = "Excluded", "✕ " + next(c.value for c in v.criteria if c.status == "not_met")
    else:
        small = "Simulated" if store.is_simulated(v) else ("To verify" if v.standing == "verify" else "Priority")
        why = ("! " if v.get("highlight_kind") == "gap" else "✓ ") + v.highlight
    return (
        f'<div class="mc tile{" sel" if sel else ""}{" x2" if v.standing == "excluded" else ""}">'
        f'<div class="h">{logo(v.mono, v.bg, 36, 13)}<div class="sc">{parts.priority_text(v.id) if v.standing != "excluded" else "—"}<small>{small}</small></div></div>'
        f'<div class="t">{esc(v.title)}</div><div class="m">{esc(v.company)} · {esc(v.city)}</div>'
        f'<div class="why">{esc(why)}</div><div class="b" style="margin-top:auto"><i style="width:{parts.priority_width(v.id) if v.standing != "excluded" else 0}%"></i></div>'
        + (f'<div class="f"><span>{SIM}</span></div></div>' if store.is_simulated(v) else
           f'<div class="f"><span class="{"u" if hot else ""}">{esc(close)}</span><span>Demo data</span></div></div>')
    )


with st.container(key="ex-main"):
    with st.container(key="gl-grid"):
        cur = st.session_state[PG]
        span = f"{cur * PER + 1}–{cur * PER + len(page)} of {len(shown)}" if pages > 1 else f"{len(shown)} shown"
        html(
            f'<div class="sh"><div><b>{f if f != "All" else "All roles"}</b><span>{span} · '
            "excluded roles stay visible, with the rule that removed them</span></div></div>"
        )
        with st.container(key="grid"):
            for v in page:
                hit(f"x-{v.id}", card(v), f"Preview {v.company}", on_click=st.session_state.__setitem__, args=(SEL, v.id))
        if not shown:
            html('<div style="font-size:13px;color:var(--t2);margin-top:14px">No roles match. Try another filter.</div>')
        if pages > 1:
            with st.container(key="x-pager", horizontal=True, gap="small"):
                # Tells ui/js/pager.js which number is lit: its liquid-glass lens
                # slides there, and stays put between reruns instead of redrawing.
                html(f'<i class="xp-mark" data-cur="{cur}"></i>')
                st.button("‹", key="x-pg-prev", help="Previous page", disabled=cur == 0,
                          on_click=go_page, args=(cur - 1,))
                for n in page_nums(cur, pages):
                    if n is None:
                        html('<span class="gap">…</span>')
                    else:
                        st.button(str(n + 1), key=f"x-pg-{n}", type="primary" if n == cur else "secondary",
                                  on_click=go_page, args=(n,))
                st.button("›", key="x-pg-next", help="Next page", disabled=cur == pages - 1,
                          on_click=go_page, args=(cur + 1,))

    with st.container(key="pan-x"):
        if shown:
            v = next(x for x in shown if x.id == st.session_state[SEL])
            label = {"eligible": "Eligible", "verify": "To verify", "excluded": "Excluded"}[v.standing]
            chip = {"eligible": "g", "verify": "u", "excluded": "r"}[v.standing]
            html(
                f'<div class="pan"><div class="kk">{esc(v.company)} · {esc(v.city)} · {esc(v.mode)}</div>'
                f'<h3>{esc(v.title)}<span class="chip {chip}">{label}</span></h3></div>'
            )
            if store.is_simulated(v):
                html(f'<div style="font-size:12px;line-height:1.45;color:var(--t2)"><b>{SIM}</b> · '
                     f'{esc(d.simulated_event["disclaimer"])}</div>')
            if v.standing != "excluded":
                html(
                    f'<div><div class="hero2"><div class="n">{parts.priority_text(v.id)}<small> /100</small></div>'
                    f'<div class="c">Priority score<br>{esc(clock.closes_line(v)[0])}</div></div>'
                    f'<div class="kstack">{parts.unified_bars(store.matches().get(v.id)) if store.priority(v.id) is not None else ""}</div></div>'
                )
            rows = "".join(
                f'<div class="ck">{check_icon(c.status)}{esc(c.name)}<span class="s">{esc(c.value)}</span></div>'
                for c in v.criteria
            )
            html(f'<div class="lab">8 fixed criteria<span>{v.met} of 8 met</span></div><div class="box crit">{rows}</div>')
            with st.container(key="end-x"):
                html(f'<div class="gate box">{parts.gate(v)}</div>' if v.standing != "excluded" else "")
            with st.container(key="ex-foot"):
                if st.button("Open role", key="ex-open"):
                    tabs.go("role", id=v.id)
                if st.button("Save", type="primary", key="save", disabled=v.standing == "excluded"):
                    store.save_application(v.id, "saved")
                    st.toast(f"Saved · {v.company} · {v.title}")

with st.container(key="aa-js-pager"):
    st.html(f"<script>{PAGER_JS}</script>", unsafe_allow_javascript=True)
