"""Matches — the ranked list and why each role sits where it does
(05_Ranking.html).

One population: curated roles and synthetic demo postings, ranked together by
the same formula (core/matches.py, D-051). Left: what happened before ranking,
the top five, the rest of the ranked roles, and one role a rule removed however
well it matched. Right: the selected role's Priority score, its four factor
scores, and the rule that says ranking never changes eligibility. A role to
verify is ordered 15 points lower; its Priority score is never changed.
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

m = store.matches()
ordered = list(m.ordered)
top = ordered[:5]
rest = ordered[5:]
n_eligible = sum(o.standing == "eligible" for o in ordered)
n_verify = sum(o.standing == "verify" for o in ordered)
n_excluded = len(m.excluded)
ranked_n = len(ordered)
checked = len(m.population)
if st.session_state[SEL] >= len(top):
    st.session_state[SEL] = 0

#: Synthetic postings have no logo colour of their own.
GREY = "#8E8E93"


def mono(o) -> str:
    if o.kind == "curated":
        r = d.role(o.role_id)
        return logo(r.mono, r.bg, 38, 13)
    return logo(store.initials(o.company), GREY, 38, 13)


def meta(o) -> str:
    mode = d.role(o.role_id).mode if o.kind == "curated" else ""
    return " · ".join(esc(x) for x in (o.company, o.city, mode) if x)


def why(o) -> str:
    """The factor that adds the most points, and the next one."""
    from core.matches import FACTOR_NAMES, FACTORS

    best = sorted(range(4), key=lambda i: -o.parts[i])[:2]
    return " · ".join(f"{FACTOR_NAMES[FACTORS[i]]} {int(o.factor(FACTORS[i]) + 0.5)}" for i in best)


def row(o, rank: int, selected: bool) -> str:
    cls, text = parts.unified_tag(o)
    return (
        f'<div class="k-row tile{" sel" if selected else ""}">'
        f'<span class="k-rank">{rank}</span>'
        f'<div class="k-job">{mono(o)}<div><div class="k-jt">{esc(o.title)}</div>'
        f'<div class="k-jm">{meta(o)}</div></div></div>'
        f'<div><div class="k-why1">{esc(why(o))}</div><div class="k-tags"><span class="chip {cls}">{esc(text)}</span></div></div>'
        f"{parts.eligibility_dot(o)}"
        f'<div class="k-sc"><div class="k-cb">{parts.unified_bars(o)}</div><b>{o.shown}</b></div></div>'
    )


def gate(o) -> str:
    """The RULE line: the curated wording for curated roles, the engine's counts otherwise."""
    if o.kind == "curated":
        return parts.gate(store.view(d.role(o.role_id)))
    checks = [x for x in o.result.outcomes if x.status.value != "not_applicable"]
    met = sum(x.status.value == "met" for x in checks)
    if o.standing == "eligible":
        return (f'<span class="ci">{parts.CK}</span><div><div style="font-weight:600"><span class="srct" '
                f'style="margin-right:6px">RULE</span>Eligible under checked rules · {met} of {len(checks)}</div>'
                '<div class="s2">Ranking orders eligible roles. It never changes eligibility.</div></div>')
    return (f'<span class="ci a">{parts.WN}</span><div><div style="font-weight:600"><span class="srct" '
            f'style="margin-right:6px">RULE</span>To verify · {met} of {len(checks)} rules pass</div>'
            '<div class="s2">Ranking never changes eligibility.</div></div>')


shell.topbar("matches", store.nav_counts())
with shell.header(
    "Your matches",
    f"<b>{ranked_n} roles</b> ranked · {n_eligible} eligible, {n_verify} to verify · "
    f"updated today {d.updated}",
):
    if st.button("Adjust preferences", key="adj"):
        tabs.go("onboarding", step="3a")

with st.container(key="mt-main"):
    with st.container(key="col"):
        # Before ranking: what the rules did to every role.
        with st.container(key="mt-strip"):
            html(
                '<div class="strip gl"><div class="s-in">'
                f'<div class="s-t">Before ranking<span>{checked} roles checked · '
                '<span class="lnk">1 question can verify more ›</span></span></div>'
                f'<div class="s-bar"><i style="flex:{n_eligible};background:#30A14E"></i>'
                f'<i style="flex:{n_verify};background:#E3A03A"></i>'
                f'<i style="flex:{n_excluded};background:repeating-linear-gradient(135deg,#F3C9C5 0 3px,#FBEAE8 3px 6px)"></i></div>'
                f'<div class="s-br"><div class="a" style="flex:{ranked_n}">{ranked_n} ranked · {n_eligible} eligible, '
                f'{n_verify} to verify</div><div style="width:3px"></div>'
                f'<div class="x2" style="flex:{n_excluded}">{n_excluded} excluded · conflict</div></div></div></div>'
            )
            if st.button("1 question can verify more", key="q-link"):
                tabs.go("question")

        # The top five.
        with st.container(key="gl-top5"):
            legend = "".join(
                f'<span><i style="background:{c}"></i>{n}</span>'
                for c, n in zip(parts.COL, ("Profile", "Preference", "Deadline urgency", "Freshness"))
            )
            html(
                '<div class="sh"><div><b>Your top 5 opportunities</b><span>Ordered by priority score · 0–100</span></div>'
                f'<div class="leg2">{legend}</div></div>'
                '<div class="k-hd"><span>#</span><span>Role</span><span>Why it ranks here</span>'
                "<span>Eligibility</span><span>Priority score</span></div>"
            )
            with st.container(key="klist"):
                for i, o in enumerate(top):
                    hit(f"row-{i}", row(o, i + 1, i == st.session_state[SEL]), f"Select {o.company}",
                        on_click=st.session_state.__setitem__, args=(SEL, i))

        # The rest of the ranked roles, in the same order and the same form.
        if rest:
            with st.expander(f"More ranked roles ({len(rest)})"):
                with st.container(key="klist-more"):
                    for i, o in enumerate(rest, start=6):
                        if hit(f"more-{i}", row(o, i, False), f"Open {o.company}"):
                            tabs.go("role", id=o.role_id)

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
    with st.container(key="pan-r"):
        if not top:
            html('<div class="pan"><div class="kk">No ranked roles</div><h3>Nothing to rank yet</h3></div>')
        else:
            i = st.session_state[SEL]
            o = top[i]
            cls, text = parts.unified_tag(o)
            html(
                f'<div class="pan"><div class="kk">#{i + 1} · {esc(o.company)} · {esc(o.city)}</div>'
                f'<h3>{"Why this is your top match" if i == 0 else f"Why it ranks #{i + 1}"}</h3></div>'
            )
            html(
                f'<div class="hero2"><div class="n">{o.shown}<small> /100</small></div>'
                f'<div class="c">Priority score<br>{esc(text)}</div></div><div class="kstack">{parts.unified_bars(o)}</div>'
            )
            html(f'<div class="box">{parts.unified_factor_rows(o)}</div>')
            with st.container(key="end-r"):
                note = parts.verify_note(o)
                html(f'<div class="gate box">{gate(o)}</div>'
                     + (f'<div class="vnote">{esc(note)}</div>' if note else ""))
            with st.container(key="mt-foot"):
                if st.button("Open role", key="mt-open"):
                    tabs.go("role", id=o.role_id)
                if o.kind == "curated":
                    app = parts.application_for(o.role_id)
                    applied = app is not None and app["stage"] in ("applied", "interview")
                    if st.button("View application" if applied else "Start application", type="primary", key="go"):
                        if not applied:
                            store.save_application(o.role_id)
                        tabs.go("applications", id=o.role_id)
