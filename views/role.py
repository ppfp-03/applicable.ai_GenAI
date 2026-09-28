"""Role — every requirement of one role, and what to do about it.

Built on the design system's Opportunity screen (ScreenOpportunity,
RequirementRow): one "Requirements" list, what the posting asks beside what
the profile has. Rows that need attention come first and open, each with the
one action that settles it; met rows are one line each and open on a tap to
show the posting's words and how the rule decided. Requirements no fixed rule
checks (e.g. Mandarin HSK) are listed apart and never counted.

Every status comes from the canonical eligibility engine (core/eligibility.py
-> engine -> core/eligibility_view.py); this page only shows it. The panel on
the right is the role itself: its priority, deadline, and the actions.
"""

from __future__ import annotations

import streamlit as st

from core import clock, store, synthetic
from ui import parts, shell, tabs
from ui import synthetic as synthetic_ui
from ui.html import check_icon, esc, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("role")

role_id = st.query_params.get("id") or st.session_state.get("role_id") or "deutsch-shanghai"
# A synthetic demo posting has its own page, with the same hierarchy.
posting = synthetic_ui.posting_id(role_id)
if posting and store.matches().get(posting):
    st.session_state["role_id"] = posting
    synthetic_ui.role_page(posting)
    st.stop()
try:
    role = d.role(role_id)
except KeyError:
    role = d.role("deutsch-shanghai")
st.session_state["role_id"] = role.id
v = store.view(role)
#: The role in the one Matches ranking: its Priority score and four factors.
ranked = store.matches().get(role.id)

attention = sorted(
    [c for c in v.criteria if c.status != "met"], key=lambda c: 0 if c.status == "not_met" else 1
)
met = [c for c in v.criteria if c.status == "met"]
n_not = sum(c.status == "not_met" for c in v.criteria)
n_chk = sum(c.status == "check" for c in v.criteria)
#: The met requirement opened in the list (one at a time), per role.
ROW = f"role_row_{role.id}"
WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"]
TITLE = {"excluded": "Not eligible yet", "verify": "Almost eligible", "eligible": "Eligible"}
DOT = {"excluded": "#D9443C", "verify": "#E3A03A", "eligible": "#30A14E"}
CHIP = {"eligible": ("g", "Eligible"), "verify": ("u", "To verify"), "excluded": ("r", "Not eligible yet")}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DEGREE = {"bachelor": "Bachelor’s", "master": "Master’s", "phd": "PhD"}

#: Where the "back" button at the foot of the panel leads: the user's
#: application for this role if there is one, else the ranked matches.
HAS_APP = any(a["role"] == role.id for a in store.applications())
BACK = ("‹ Applications", "applications", {"id": role.id}) if HAS_APP else ("‹ Matches", "matches", {})


@st.dialog("Job posting")
def posting_notice() -> None:
    """What "Open job posting" does in the demo: say plainly there is nothing to open."""
    # Inline styles: a dialog is drawn outside the page, beyond role.css.
    html(
        f'<div style="font-size:13px;color:var(--t2);margin-bottom:10px">'
        f"{esc(role.title)} · {esc(role.company)} · {esc(role.city)}</div>"
        '<div style="font-size:14px;line-height:1.5"><p style="margin:0 0 8px"><b>This is a synthetic demo '
        "posting</b>, so there is no real job page to open.</p>"
        '<p style="margin:0 0 14px">With real postings, this button takes you to the employer’s own page, '
        "where you apply.</p></div>"
    )
    if st.button("Close", type="primary", key="pn-close"):
        st.rerun()


#: The answers to "Can you work in <country> without visa sponsorship?".
WORK_CHOICES = (("yes", "Yes"), ("no", "No · I need sponsorship"), ("unsure", "Not sure"))


@st.dialog("Permission to work")
def work_question() -> None:
    """Ask the one fact the permission check needs for this role's country."""
    name = store.country_name(role.country)
    html(
        f'<div style="font-size:15px;line-height:1.5;margin-bottom:6px">Can you work in <b>{esc(name)}</b> '
        "without visa sponsorship?</div>"
        '<div style="font-size:12.5px;color:var(--t2);line-height:1.45;margin-bottom:14px">Only your own answer '
        "counts: citizenship or a visa for another country does not settle it. “Not sure” keeps this role "
        "to verify.</div>"
    )
    current = store.work_answer(role.country)
    for choice, label in WORK_CHOICES:
        kind = "primary" if choice == current else "secondary"
        if st.button(label, type=kind, key=f"wq-{choice}", width="stretch"):
            store.set_work_answer(role.country, choice)
            st.session_state["flash"] = f"Answer saved · Work authorization · {name} = {label} · checked again"
            st.rerun()


def back() -> None:
    label, tab, params = BACK
    if st.button(label, key="back-f", width="stretch"):
        tabs.go(tab, **params)


shell.topbar("matches", store.nav_counts())
with shell.header(
    TITLE[v.standing],
    f"{esc(role.title)} · <b>{esc(role.company)}</b> · {esc(role.city)} · "
    + (f"<b>{esc(d.simulated_event['label'])}</b>" if store.is_simulated(role)
       else "Demo data"),
):
    pass  # every action, the way back included, is in the panel on the right


# ───────────────────────── What each row says ─────────────────────────
#
# Display only: the words for what the posting asks and what the profile
# holds. The status beside them is the engine's, unchanged.


def month(ym: str) -> str:
    """'2027-07' -> 'Jul 2027'."""
    year, m = ym.split("-")
    return f"{MONTHS[int(m) - 1]} {year}"


def checked_asks() -> dict[str, str]:
    """Languages the posting asks at a level a fixed rule checks (CEFR, fluent, native)."""
    return {lang: lvl for lang, lvl in role.requirements.get("languages", {}).items()
            if store.checked_language(lang, lvl)}


def they_ask(c) -> str:
    req = role.requirements
    country = store.country_name(role.country)
    if c.id == "location":
        return f"Based in {role.city}, {country} · {role.mode}"
    if c.id == "permission":
        return f"Right to work in {country}"
    if c.id == "student":
        return "Open to enrolled students" if req.get("student") else "No student requirement"
    if c.id == "graduation":
        if not req.get("graduation"):
            return "No graduation window"
        lo, hi = req["graduation"]
        return f"Graduating between {month(lo)} and {month(hi)}"
    if c.id == "degree":
        return f"{DEGREE[req['degree_level']]} degree" if req.get("degree_level") else "No degree requirement"
    if c.id == "field":
        fields = req.get("fields", [])
        if not fields:
            return "No field requirement"
        return "Degree in " + ", ".join(fields) + (" or a related field" if req.get("related_ok") else "")
    if c.id == "language":
        asks = checked_asks()
        return " · ".join(f"{lang} {lvl}" for lang, lvl in asks.items()) or "No language level to check"
    n = req.get("experience_min", 0)
    return f"At least {n} internship{'s' if n != 1 else ''}" if n else "No experience requirement"


def you_have(c) -> tuple[str, str]:
    """What the profile holds for this requirement, and where it comes from (CV / YOU / "")."""
    p = d.profile
    degree = p["degree"]
    if c.id == "location":
        return "You haven’t limited the countries you would work in", ""
    if c.id == "permission":
        said = store.work_answer(role.country)
        return {"yes": ("You can work there without sponsorship", "YOU"),
                "no": ("You need visa sponsorship", "YOU")}.get(said, ("Not stated", ""))
    if c.id == "student":
        return (f"Enrolled at {p.get('school', 'university')}", "CV") if p.get("enrolled") else ("Not stated", "")
    if c.id == "graduation":
        return f"{degree['label']} · graduating {month(degree['graduation'])}", "CV"
    if c.id == "degree":
        extra = [f"{x['label']} · completed" for x in p.get("previous_degrees", [])]
        status = " · in progress" if degree.get("status") == "in_progress" else ""
        return " · ".join([f"{degree['label']}{status}", *extra]), "CV"
    if c.id == "field":
        return f"{degree['field']} ({degree['label']})", "CV"
    if c.id == "language":
        certs = store.answers().get("languages") or {}
        have = {**p.get("languages", {}), **certs}
        asks = checked_asks() or have
        src = "YOU" if any(lang in certs for lang in asks) else "CV"
        return " · ".join(f"{lang} {have.get(lang, 'not stated')}" for lang in asks), src
    return f"{p.get('experience_months', 0)} months · {p.get('internships', 0)} internships", "CV"


def details(c) -> str:
    """Under an open row: the posting's own words when we have them, and how the rule decided.

    The rule's reason is shown in words; its ID, version and answer keys stay
    in the audit trace (`c.rule`), never on screen.
    """
    quote = role.get("posting", {}).get(c.id)
    posting = (
        f'<div class="q">{esc(quote["quote"])} <span class="srct">JOB</span> {esc(quote["line"])}</div>'
        if quote else
        '<div class="q muted">Demo posting: the requirement as recorded, with no source text to quote.</div>'
    )
    return (
        f'<div class="dt"><div class="lb">From the job posting</div>{posting}'
        f'<div class="lb">How it was decided</div><div class="how">{esc(readable(c))}</div></div>'
    )


def readable(c) -> str:
    """The rule's reason with no internal identifier left in it."""
    return synthetic.readable(c.detail, "HC_LANGUAGE" if c.id == "language" else "")


def row(c, is_open: bool) -> str:
    have, src = you_have(c)
    tag = f' <span class="srct">{src}</span>' if src else ""
    chip = {"not_met": '<span class="chip r">Not met</span>',
            "check": '<span class="chip u">To check</span>'}.get(c.status, "")
    tail = chip or f'<span class="chev">{"–" if is_open else "+"}</span>'
    return (
        f'<div class="rq {c.status}{" open" if is_open else ""}">{check_icon(c.status)}'
        f'<div class="ra"><div class="lb">They ask · {esc(c.name)}</div><div class="tv">{esc(they_ask(c))}</div></div>'
        f'<div class="rb"><div class="lb">You have</div><div class="yv{" ns" if have == "Not stated" else ""}">'
        f"{esc(have)}{tag}</div></div>{tail}</div>"
    )


def toggle(cid: str) -> None:
    st.session_state[ROW] = None if st.session_state.get(ROW) == cid else cid


def action(c) -> None:
    """The one button that settles an open requirement."""
    if c.id == "permission" and role.country == "GB":
        if st.button("Answer 1 question", type="primary", key="ask"):
            tabs.go("question")
    elif c.id == "permission":
        answered = store.work_answer(role.country) in ("yes", "no")
        if st.button("Change your answer" if answered else "Answer 1 question", type="primary", key="ask-wa"):
            work_question()
    elif c.id == "language":
        with st.popover("Add certificate", type="primary", key="cert"):
            have = {**d.profile.get("languages", {}), **(store.answers().get("languages") or {})}
            asks = checked_asks()
            lang = next((x for x in asks if x not in have), next(iter(asks), "English"))
            up = st.file_uploader(f"{lang} certificate (PDF)", type=["pdf", "png", "jpg"], key="cert-file")
            # "fluent" and "native" too: a posting asking French fluent is not met by a CEFR level (D-046).
            level = st.selectbox("Level on the certificate", ["B2", "C1", "C2", "fluent", "native"], index=1)
            if st.button("Check again with this certificate", type="primary", disabled=up is None):
                store.set_answer("languages", {**(store.answers().get("languages") or {}), lang: level})
                st.session_state["flash"] = f"Certificate added · {lang} = {level} · checked again"
                st.rerun()
    elif c.id == "field":
        with st.popover("Draft question to recruiter", type="primary", key="draft"):
            st.text_area("To the recruiter", d.eligibility_copy["field"]["draft"], height=160, key="draft-text")
            if st.button("Save draft", type="primary"):
                st.toast("Draft saved · nothing is sent until you send it")
    elif st.button("Open job posting", type="primary", key="other"):
        posting_notice()


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
        '<div class="ring"><svg width="120" height="120" viewBox="0 0 150 150">'
        '<circle cx="75" cy="75" r="62" fill="none" stroke="rgba(0,0,0,.06)" stroke-width="10"/>'
        + "".join(segs)
        + f'</svg><div class="c"><b>{len(met)}/8</b><span>met</span></div></div>'
    )


def summary() -> str:
    """"You meet 5 of 8 requirements. One doesn't match and two need..." """
    s = f"You meet {len(met)} of 8 requirements."
    bits = []
    if n_not:
        bits.append(f"{WORDS[n_not]} {'doesn’t' if n_not == 1 else 'don’t'} match")
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
            f"<p>{esc(summary())}</p></div>{ring()}</div>"
        )

        with st.container(key="gl-req"):
            counts = f"{len(met)} of 8 met" + (f" · {n_chk} to check" if n_chk else "") + (
                f" · {n_not} not met" if n_not else "")
            html(f'<div class="sh"><div><b>Requirements</b><span>{counts} · tap a met one for details</span></div></div>')
            # What needs attention first, open, with the action that settles it.
            for c in attention:
                with st.container(key=f"rq-{c.id}"):
                    html(row(c, True) + details(c))
                    with st.container(key=f"rqa-{c.id}"):
                        action(c)
            # Then the met ones, one line each; a tap opens one.
            for c in met:
                is_open = st.session_state.get(ROW) == c.id
                with st.container(key=f"rq-{c.id}"):
                    hit(f"rqh-{c.id}", row(c, is_open), f"{'Hide' if is_open else 'Show'} {c.name} details",
                        on_click=toggle, args=(c.id,))
                    if is_open:
                        html(details(c))
            # Requirements no fixed rule checks (e.g. Mandarin HSK): shown, never counted.
            if v.limitations:
                html('<div class="lim-h">Not checked by fixed rules · for information, never changes eligibility</div>')
                for n in v.limitations:
                    html(f'<div class="rq lim"><span class="ci n">–</span><div class="ra"><div class="lb">{esc(n.name)}</div>'
                         f'<div class="tv">{esc(n.text)}</div></div></div>')

    # The role itself: where it stands, how it ranks, and what to do next.
    with st.container(key="pan-e"):
        cls, chip = CHIP[v.standing]
        html(
            f'<div class="pan"><div class="kk">This role</div><h3>{esc(role.company)}<span class="chip {cls}">{chip}</span></h3></div>'
        )
        if ranked is not None and ranked.shown is not None:
            html(
                f'<div class="hero2"><div class="sc">{ranked.shown}<small> /100 priority</small></div>'
                f'<div class="cl">{esc(clock.closes_line(role)[0])}</div></div>'
            )
            html(f'<div class="box">{parts.unified_factor_rows(ranked)}</div>')
        else:
            html('<div class="box" style="font-size:12.5px;color:var(--t2)">Not ranked · a fixed rule excludes this role. '
                 "Ranking never changes eligibility.</div>")
        note = parts.verify_note(ranked) if ranked is not None and ranked.shown is not None else ""
        html(f'<div class="gate box">{parts.gate(v)}</div>' + (f'<div class="vnote">{esc(note)}</div>' if note else ""))
        with st.container(key="pan-acts"):
            if HAS_APP:
                # Already applying: "Start application" would move it back to In progress.
                if st.button("View application", type="primary", key="view-app", width="stretch"):
                    tabs.go("applications", id=role.id)
            elif st.button("Start application", type="primary", key="apply", width="stretch",
                           disabled=v.standing == "excluded"):
                store.save_application(role.id)
                tabs.go("applications", id=role.id)
            if st.button("Open job posting", key="posting", width="stretch"):
                posting_notice()
            back()
