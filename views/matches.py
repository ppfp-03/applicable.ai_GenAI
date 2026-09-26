"""Matches — the ranked list and why each role sits where it does
(05_Ranking.html).

Left: what happened before ranking, the top five, and one role a rule
removed however well it matched. Right: the selected role's score taken
apart -- four factors, fixed weights, the arithmetic, and the rule that says
ranking never changes eligibility.
"""

from __future__ import annotations

import streamlit as st

from core import store
from ui import parts, shell, tabs
from ui.html import LOCK, esc, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("matches")

SEL = "matches_sel"
st.session_state.setdefault(SEL, 0)

counts = store.counts()
top = store.ranked()[:5]
ranked_n = counts["eligible"] + counts["verify"]
checked = sum(counts.values())
if st.session_state[SEL] >= len(top):
    st.session_state[SEL] = 0

shell.topbar("matches", store.nav_counts())
with shell.header(
    "Your matches",
    f"<b>{ranked_n} roles</b> ranked · {counts['eligible']} eligible, {counts['verify']} to verify · "
    f"updated today {d.updated}",
):
    if st.button("Adjust preferences", key="adj"):
        tabs.go("onboarding", step="3a")

with st.container(key="mt-main"):
    with st.container(key="col"):
        # Before ranking: what the rules did to the catalogue.
        with st.container(key="mt-strip"):
            html(
                '<div class="strip gl"><div class="s-in">'
                f'<div class="s-t">Before ranking<span>{checked} roles checked · '
                '<span class="lnk">1 question can verify more ›</span></span></div>'
                f'<div class="s-bar"><i style="flex:{counts["eligible"]};background:#30A14E"></i>'
                f'<i style="flex:{counts["verify"]};background:#E3A03A"></i>'
                f'<i style="flex:{counts["excluded"]};background:repeating-linear-gradient(135deg,#F3C9C5 0 3px,#FBEAE8 3px 6px)"></i></div>'
                f'<div class="s-br"><div class="a" style="flex:{ranked_n}">{ranked_n} ranked · {counts["eligible"]} eligible, '
                f'{counts["verify"]} to verify</div><div style="width:3px"></div>'
                f'<div class="x2" style="flex:{counts["excluded"]}">{counts["excluded"]} excluded · conflict</div></div></div>'
                '<div class="s-div"></div><div class="s-how">'
                '<div class="s-t">How ranking works<span>Same inputs, same order</span></div>'
                '<div class="s-flow"><div class="s-comp"><span>Profile fit</span><span>Preference fit</span>'
                '<span>Urgency</span><span>Freshness</span></div><span class="s-ar">→</span>'
                '<div class="s-ps"><b>Priority score</b><small>weighted sum</small></div><span class="s-ar">→</span>'
                '<span class="s-top">Top 5</span></div></div></div>'
            )
            if st.button("1 question can verify more", key="q-link"):
                tabs.go("question")

        # The top five.
        with st.container(key="gl-top5"):
            legend = "".join(
                f'<span><i style="background:{c}"></i>{n}</span>'
                for c, n in zip(parts.COL, ("Profile", "Preference", "Urgency", "Freshness"))
            )
            html(
                '<div class="sh"><div><b>Your top 5 opportunities</b><span>Ordered by priority score · 0–100</span></div>'
                f'<div class="leg2">{legend}</div></div>'
                '<div class="k-hd"><span>#</span><span>Role</span><span>Why it ranks here</span>'
                "<span>Eligibility</span><span>Priority score</span></div>"
            )
            with st.container(key="klist"):
                for i, v in enumerate(top):
                    cls, text = parts.tag(v)
                    row = (
                        f'<div class="k-row tile{" sel" if i == st.session_state[SEL] else ""}">'
                        f'<span class="k-rank">{i + 1}</span>'
                        f'<div class="k-job">{logo(v.mono, v.bg, 38, 13)}<div><div class="k-jt">{esc(v.title)}</div>'
                        f'<div class="k-jm">{esc(v.company)} · {esc(v.city)} · {esc(v.mode)}</div></div></div>'
                        f'<div><div class="k-why1">{esc(v.why)}</div><div class="k-tags"><span class="chip {cls}">{esc(text)}</span></div></div>'
                        f"{parts.eligibility_dot(v)}"
                        f'<div class="k-sc"><div class="k-cb">{parts.bars(v)}</div><b>{v.shown}</b></div></div>'
                    )
                    hit(f"row-{i}", row, f"Select {v.company}", on_click=st.session_state.__setitem__, args=(SEL, i))

        # A high match that a rule removed.
        gone = next((v for v in store.excluded() if v.get("semantic")), None)
        if gone:
            blocker = next(c for c in gone.criteria if c.status == "not_met")
            if hit(
                "exc",
                f'<div class="exc gl">{logo(gone.mono, gone.bg, 38, 13)}'
                f'<div><div class="t1">{esc(gone.title)} · {esc(gone.company)} · {esc(gone.city)}</div>'
                f'<div class="t2">Removed before ranking · <b>requires {esc(blocker.need.replace("HSK", "Mandarin HSK"))}</b>, '
                f'you have {esc(blocker.have)} · <span class="lnk">See why ›</span></div></div>'
                f'<div class="sem"><div><div class="v">{gone.semantic}%</div><div class="l">Semantic match</div></div>'
                f'<span class="lockb">{LOCK}A high match can’t override a conflict</span></div></div>',
                "See why",
            ):
                tabs.go("role", id=gone.id)

    # The selected role, taken apart.
    v = top[st.session_state[SEL]]
    i = st.session_state[SEL]
    cls, text = parts.tag(v)
    with st.container(key="pan-r"):
        html(
            f'<div class="pan"><div class="kk">#{i + 1} · {esc(v.company)} · {esc(v.city)}</div>'
            f'<h3>{"Why this is your top match" if i == 0 else f"Why it ranks #{i + 1}"}</h3></div>'
        )
        html(
            f'<div class="hero2"><div class="n">{v.shown}<small> /100</small></div>'
            f'<div class="c">Priority score<br>{esc(text)}</div></div><div class="kstack">{parts.bars(v)}</div>'
        )
        html(f'<div class="box">{parts.factor_rows(v)}</div>')
        html(f'<div class="kform">{parts.formula(v)}</div>')
        w = d.weights
        html(
            '<div class="lab">Weights<span>Same for every role</span></div><div class="wts">'
            f'<span style="flex:{w["profile"] * 100:g};background:#0071E3;color:#fff">{w["profile"] * 100:g}%</span>'
            f'<span style="flex:{w["preference"] * 100:g};background:#5AA2F0;color:#fff">{w["preference"] * 100:g}%</span>'
            f'<span style="flex:{w["urgency"] * 100:g};background:#A9CDF7;color:#0B3F7A">{w["urgency"] * 100:g}%</span>'
            f'<span style="flex:{w["freshness"] * 100:g};background:#D6E7FB;color:#0B3F7A">{w["freshness"] * 100:g}%</span></div>'
        )
        with st.container(key="end-r"):
            html(f'<div class="gate box">{parts.gate(v)}</div>')
        with st.container(key="mt-foot"):
            if st.button("Open role", key="mt-open"):
                tabs.go("role", id=v.id)
            app = parts.application_for(v.id)
            applied = app is not None and app["stage"] in ("applied", "interview")
            if st.button("View application" if applied else "Start application", type="primary", key="go"):
                if not applied:
                    store.save_application(v.id)
                tabs.go("applications", id=v.id)
