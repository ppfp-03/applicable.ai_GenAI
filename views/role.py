"""Role — how eligibility was decided for one role (03_Eligibility.html).

Eight fixed criteria: permission to work from the canonical HC_WORK_AUTH rule
(core/eligibility.py), the rest from core/rules.py. What needs attention comes
first, one tile per open criterion; the side panel shows the posting's words,
the rule that compared them with the profile, and what the user can do. The
primary action feeds a new fact back (a certificate, an answer) and the same
rules run again.
"""

from __future__ import annotations

import streamlit as st

from core import clock, store
from ui import parts, shell, tabs
from ui.html import CK, SH, check_icon, esc, glyph, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("role")

role_id = st.query_params.get("id") or st.session_state.get("role_id") or "deutsch-shanghai"
try:
    role = d.role(role_id)
except KeyError:
    role = d.role("deutsch-shanghai")
st.session_state["role_id"] = role.id
v = store.view(role)

attention = sorted(
    [c for c in v.criteria if c.status != "met"], key=lambda c: 0 if c.status == "not_met" else 1
)
met = [c for c in v.criteria if c.status == "met"]
n_not = sum(c.status == "not_met" for c in v.criteria)
n_chk = sum(c.status == "check" for c in v.criteria)
SEL = f"role_sel_{role.id}"
if st.session_state.get(SEL, 0) >= max(1, len(attention)):
    st.session_state[SEL] = 0
st.session_state.setdefault(SEL, 0)

ICON = {"language": "lang", "permission": "auth", "field": "field", "student": "edu",
        "graduation": "edu", "degree": "edu", "experience": "exp", "location": "loc"}
SHORT = {"Computer Science": "CS", "Statistics": "Statistics"}
WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"]
TITLE = {"excluded": "Not eligible yet", "verify": "Almost eligible", "eligible": "Eligible"}
DOT = {"excluded": "#D9443C", "verify": "#E3A03A", "eligible": "#30A14E"}

shell.topbar("matches", store.nav_counts())
with shell.header(
    TITLE[v.standing],
    f"{esc(role.title)} · <b>{esc(role.company)}</b> · {esc(role.city)} · checked today {role.get('checked', d.updated)}",
):
    if st.button("‹ Matches", key="back"):
        tabs.go("matches")
    if st.button("Open job posting", key="posting"):
        st.toast("Opening the job posting")
    if st.button("Check again", key="again"):
        st.toast("Checked again · no changes")


# ───────────────────────── Per-criterion copy ─────────────────────────


def fields_short(c) -> str:
    return ", ".join(SHORT.get(f, f) for f in role.requirements.get("fields", []))


def copy(c) -> dict:
    """Everything the tile and the panel say about one open criterion."""
    base = d.eligibility_copy.get(c.id, {})
    posting = role.get("posting", {}).get(c.id)
    out = {
        "kind": base.get("kind", c.name), "name": c.name if c.id == "language" else base.get("name", c.name),
        "act": base.get("act", "See how it was decided"), "btn": base.get("btn", "Report a mistake"),
        "say": base.get("say", "Tell us if this looks wrong; we check it with the same rule."),
        "alt": base.get("alt", ["Similar roles without this requirement", "Explore more roles"]),
        "quote": posting["quote"] if posting else "Not stated in the posting we read.",
        "line": posting["line"] if posting else "Requirements",
        "td": c.detail, "viz": "", "big": "", "dec": f"Rule <code>{esc(c.rule)}</code>.",
    }
    if c.id == "language":
        scale = c.need.split()[0] if c.need.startswith("HSK") else ""
        levels = [f"{scale} {i}" for i in range(1, 7)] if scale else ["A1", "A2", "B1", "B2", "C1", "C2"]
        have_i = levels.index(c.have) if c.have in levels else -1
        need_i = levels.index(c.need) if c.need in levels else -1

        def sc() -> str:
            cells = "".join(
                f'<i class="{"f" if i <= have_i else "rq" if i == need_i else ""}"></i>' for i in range(6)
            )
            return f'<div class="scale">{cells}</div>'

        gap = need_i - have_i
        out["viz"] = sc() + f'<div class="scl"><b>You · {esc(c.have)}</b><span class="rq">Required · {esc(c.need)}</span></div>'
        out["big"] = (
            f'<h4>{gap} level{"s" if gap != 1 else ""} below</h4><div class="sub">Required {esc(c.need)} · your profile {esc(c.have)}</div>'
            + sc()
            + '<div class="nums">' + "".join(f"<span>{i}</span>" for i in range(1, 7)) + "</div>"
            '<div class="leg"><span><i style="background:#1D1D1F"></i>Your level</span>'
            '<span><i style="box-shadow:inset 0 0 0 1.5px #C4302B"></i>Required</span></div>'
        )
        out["dec"] = (
            f"A fixed rule compared <code>{esc(c.have)}</code> with <code>{esc(c.need)}</code>. "
            "AI only read the posting. It didn’t make this decision."
        )
        out["name"] = c.name
    elif c.id == "permission" and role.country == "GB":
        out.update(
            act="Answer 1 question", btn="Answer 1 question",
            say="Tell us whether you can work in the UK without sponsorship. One answer settles 14 roles.",
            alt=["Why we ask", "It’s the only fact still deciding these roles"],
            viz='<div class="cmp"><span class="pill">EU citizen</span><span class="ar">+</span><span class="pill q">UK right to work ?</span></div>',
            big='<h4>One answer missing</h4><div class="sub">United Kingdom · right to work not stated</div>'
                '<div class="cmp" style="justify-content:flex-start"><span class="pill">EU citizen <span style="color:var(--green)">✓</span></span>'
                '<span class="ar">+</span><span class="pill q">UK right to work ?</span></div>',
            dec=f"Rule <code>{esc(c.rule)}</code>. Your nationality is in your CV (p.2). UK right to work is not stated in your CV.",
        )
    elif c.id == "permission":
        # Outside the UK nothing answers it yet, and citizenship is not an answer.
        out.update(
            act="Confirm with the employer", btn="Open job posting",
            say=f"Citizenship alone does not settle whether you can work in {role.city}. "
                "Check the posting or ask the employer before you apply.",
            alt=["Similar roles", "Explore more roles"],
        )
    elif c.id == "field":
        out["viz"] = (
            f'<div class="cmp"><span class="pill">{esc(c.have)}</span><span class="ar">≈</span>'
            f'<span class="pill q">{esc(fields_short(c))} ?</span></div>'
        )
        out["big"] = (
            '<h4>“Related field” is unclear</h4>'
            f'<div class="sub">Posting: {esc(fields_short(c))} or related · you: {esc(d.profile["degree"]["label"])}</div>'
            f'<div class="cmp" style="justify-content:flex-start"><span class="pill">{esc(d.profile["degree"]["label"])}</span>'
            f'<span class="ar">≈</span><span class="pill q">{esc(fields_short(c))} ?</span></div>'
        )
        out["dec"] = (
            f"The rule can’t decide whether <code>{esc(c.have)}</code> counts as “related”, so it asks instead of guessing."
        )
    return out


def ring() -> str:
    """The 8-segment donut: met, to check, not met."""
    circ, gap = 389.6, 5.0
    segs, offset = [], 0.0
    for n, color in ((len(met), "#30A14E"), (n_chk, "#E3A03A"), (n_not, "#D9443C")):
        if not n:
            continue
        length = n / 8 * circ
        segs.append(
            f'<circle cx="75" cy="75" r="62" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round" '
            f'stroke-dasharray="{max(length - gap, 1):.1f} {circ}" stroke-dashoffset="{-offset:.1f}" transform="rotate(-90 75 75)"/>'
        )
        offset += length
    return (
        '<div class="ring"><svg width="150" height="150" viewBox="0 0 150 150">'
        '<circle cx="75" cy="75" r="62" fill="none" stroke="rgba(0,0,0,.06)" stroke-width="10"/>'
        + "".join(segs)
        + f'</svg><div class="c"><b>{len(met)}/8</b><span>criteria met</span></div></div>'
    )


def summary() -> str:
    """"You meet 5 of 8 required criteria. One doesn't match and two need..." """
    s = f"You meet {len(met)} of 8 required criteria."
    bits = []
    if n_not:
        bits.append(f"{WORDS[n_not].lower() if bits else WORDS[n_not]} {'doesn’t' if n_not == 1 else 'don’t'} match")
    if n_chk:
        w = WORDS[n_chk].lower() if bits else WORDS[n_chk]
        bits.append(f"{w} need{'s' if n_chk == 1 else ''} a quick check before you apply")
    if bits:
        s += " " + " and ".join(bits) + "."
    else:
        s += " Nothing stands between you and applying."
    return s


# ───────────────────────── Layout ─────────────────────────

label = {"excluded": "Not eligible yet", "verify": "To verify", "eligible": "Eligible"}[v.standing]
closes = role.closes_label.split()[-2:] if role.closes_label else []

with st.container(key="main"):
    with st.container(key="col"):
        html(
            f'<div class="hero card"><div class="l">'
            f'<div class="kk"><i style="background:{DOT[v.standing]}"></i>{label} · checked by fixed rules</div>'
            f'<div class="r1">{logo(role.mono, role.bg, 46, 16, 12)}<div><div class="tt">{esc(role.title)}</div>'
            f'<div class="mm">{esc(role.company)} · {esc(role.city)} · {esc(role.mode)} · closes {esc(" ".join(closes))}</div></div></div>'
            f"<p>{esc(summary())}</p>"
            f'<div class="cnts"><span><i style="background:#30A14E"></i><b>{len(met)}</b> met</span>'
            f'<span><i style="background:#E3A03A"></i><b>{n_chk}</b> to check</span>'
            f'<span><i style="background:#D9443C"></i><b>{n_not}</b> not met</span></div>'
            '<div class="how"><span class="chip">AI reads the posting</span><span class="ar">→</span>'
            '<span class="chip">Sorted into 8 fixed criteria</span><span class="ar">→</span>'
            f'<span class="chip b">Fixed rules decide, not AI</span></div></div>{ring()}</div>'
        )

        with st.container(key="gl-att"):
            if attention:
                html(
                    f'<div class="sh"><div><b>Needs your attention</b><span>{len(attention)} '
                    f'criteri{"on" if len(attention) == 1 else "a"} · tap one to see how it was decided</span></div></div>'
                )
                with st.container(key="att"):
                    for i, c in enumerate(attention[:3]):
                        k = copy(c)
                        sel = i == st.session_state[SEL]
                        chip = '<span class="chip r">Not met</span>' if c.status == "not_met" else '<span class="chip u">Check</span>'
                        hit(
                            f"at-{i}",
                            f'<div class="at tile{" sel" if sel else ""}"><div class="t0"><span class="ico">'
                            f'{glyph(ICON[c.id], "#0071E3" if sel else None)}</span>{chip}</div>'
                            f'<div class="tn">{esc(k["name"])}</div><div class="td">{esc(k["td"])}</div>'
                            f'<div class="viz">{k["viz"]}</div><div class="act">{esc(k["act"])}<span>›</span></div></div>',
                            f"Show {c.name}",
                            on_click=st.session_state.__setitem__,
                            args=(SEL, i),
                        )
            else:
                html(
                    '<div class="sh"><div><b>Needs your attention</b><span>Nothing · all 8 criteria met</span></div></div>'
                    f'<div class="allgood tile"><span class="ci">{CK}</span>Every fixed criterion is met. '
                    "Ranking decides the order; nothing blocks this role.</div>"
                )

        tiles = "".join(
            f'<div class="mt tile">{check_icon("met")}<div style="min-width:0"><div class="n">{esc(c.name)}</div>'
            f'<div class="v">{esc(c.value)}</div></div></div>'
            for c in met
        )
        with st.container(key="gl-met"):
            html(
                f'<div class="sh"><div><b>Criteria met</b><span>{len(met)} criteri{"on" if len(met) == 1 else "a"} · '
                f'same rules for every role</span></div></div><div class="met" style="--n:{min(len(met), 5) or 1}">{tiles}</div>'
            )

    with st.container(key="pan-e"):
        if attention:
            c = attention[st.session_state[SEL]]
            k = copy(c)
            chip = '<span class="chip r">Not met</span>' if c.status == "not_met" else '<span class="chip u">Check</span>'
            html(f'<div class="pan"><div class="kk">{esc(k["kind"])}</div><h3>{esc(k["name"])}{chip}</h3></div>')
            html(f'<div class="big box">{k["big"] or "<h4>" + esc(c.value) + "</h4><div class=sub>" + esc(c.detail) + "</div>"}</div>')
            html(
                f'<div class="lab">From the job posting</div><div class="box qbox">{esc(k["quote"])}'
                f'<div class="m"><span class="srct">JOB</span>{esc(k["line"])}</div></div>'
            )
            html(
                f'<div class="lab">How it was decided</div><div class="dec">{SH}'
                f'<div><span class="srct" style="margin-right:6px">RULE</span>{k["dec"]}</div></div>'
            )
            html(f'<div class="lab">What you can do</div><div class="say">{esc(k["say"])}</div>')
            with st.container(key="end-e"):
                if hit(
                    "alt",
                    f'<div class="alt box"><div><div class="an">{esc(k["alt"][0])}</div>'
                    f'<div class="as">{esc(k["alt"][1])}</div></div><span>›</span></div>',
                    k["alt"][0],
                ):
                    if c.id == "language":
                        tabs.go("explore", city=role.city)
                    st.toast(f"{k['alt'][0]} · {k['alt'][1]}")
            with st.container(key="foot"):
                if st.button("Report a mistake", key="report"):
                    st.toast("Thanks · we’ll review this check")
                if c.id == "language":
                    with st.popover(k["btn"], type="primary", key="cert"):
                        up = st.file_uploader("HSK certificate (PDF)", type=["pdf", "png", "jpg"], key="cert-file")
                        level = st.selectbox("Level on the certificate", ["HSK 4", "HSK 5", "HSK 6"], index=2)
                        if st.button("Check again with this certificate", type="primary", disabled=up is None):
                            langs = {**(store.answers().get("languages") or {}), c.name.split()[0]: level}
                            store.set_answer("languages", langs)
                            st.session_state["flash"] = f"Certificate added · {c.name} = {level} · checked again"
                            st.rerun()
                elif c.id == "permission" and role.country == "GB":
                    if st.button(k["btn"], type="primary", key="ask"):
                        tabs.go("question")
                elif c.id == "permission":
                    if st.button(k["btn"], type="primary", key="posting-f"):
                        st.toast("Opening the job posting")
                elif c.id == "field":
                    with st.popover(k["btn"], type="primary", key="draft"):
                        st.text_area("To the recruiter", d.eligibility_copy["field"]["draft"], height=160, key="draft-text")
                        if st.button("Save draft", type="primary"):
                            st.toast("Draft saved · nothing is sent until you send it")
                else:
                    if st.button(k["btn"], type="primary", key="other"):
                        st.toast("Thanks · we’ll review this check")
        else:
            html(
                f'<div class="pan"><div class="kk">Priority score</div><h3>Ready to apply<span class="chip g">Eligible</span></h3></div>'
                f'<div class="hero2" style="display:flex;align-items:flex-end;justify-content:space-between">'
                f'<div style="font-size:56px;font-weight:700;letter-spacing:-0.045em;line-height:1">{v.shown}'
                f'<small style="font-size:16px;color:var(--t3);font-weight:560;letter-spacing:0"> /100</small></div>'
                f'<div style="font-size:12px;color:var(--t2);text-align:right;line-height:1.5">{esc(clock.closes_line(role)[0])}</div></div>'
            )
            html(f'<div class="box">{parts.factor_rows(v)}</div>')
            with st.container(key="end-e"):
                html(f'<div class="gate box" style="display:flex;align-items:center;gap:10px;padding:12px 14px;font-size:12.5px">{parts.gate(v)}</div>')
            with st.container(key="foot"):
                if st.button("‹ Matches", key="back2"):
                    tabs.go("matches")
                if st.button("Start application", type="primary", key="apply"):
                    store.save_application(role.id)
                    tabs.go("applications", id=role.id)
