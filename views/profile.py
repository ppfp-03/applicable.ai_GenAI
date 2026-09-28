"""Profile — check what we read from your CV (02_Profile_Intake.html).

Seven sections, each with the values we extracted, the CV lines they came
from and the deterministic checks that ran on them. The user confirms or
corrects each; only when every section is confirmed does the profile go to
ranking. Nothing is inferred silently: an inferred value is marked, and a
missing one says "Not stated in your CV".

The data processing consent comes first: until it is given, the consent
section is the only one that opens.
"""

from __future__ import annotations

import streamlit as st

from core import store
from ui import shell, tabs
from ui.html import CHEV, CK, WN, esc, glyph, hit, html, md_icon
from ui.theme import page_css

d = store.data()
page_css("profile")
store.show_consent()

status = st.session_state[store.SECTIONS]
values = st.session_state[store.VALUES]
sections = d.sections
CUR = "profile_cur"
FIX = "profile_fix"  # section whose values the user marked as incorrect
st.session_state.setdefault(CUR, next((i for i, s in enumerate(sections) if s.get("focus_first")), 0))
CONSENT_AT = next(i for i, s in enumerate(sections) if s["id"] == store.CONSENT_SECTION)
consent = store.consent_given()
if not consent:
    st.session_state[CUR] = CONSENT_AT
NEEDS_CONSENT = "Give your data processing consent first"
left = [s for s in sections if status[s["id"]] != "ok"]
CHIP = {"ok": ("g", "Confirmed"), "rev": ("u", "Needs review"), "pend": ("u", "Pending")}


def chip(st_: str) -> str:
    c, t = CHIP[st_]
    return f'<span class="chip {c}">{t}</span>'


def mark_incorrect(sid: str) -> None:
    status[sid] = "rev"
    st.session_state[FIX] = sid


def confirm(i: int) -> None:
    s = sections[i]
    status[s["id"]] = "ok"
    st.session_state.pop(FIX, None)
    if s["id"] == store.CONSENT_SECTION:
        store.give_consent()
    nxt = next((j for j, x in enumerate(sections) if status[x["id"]] != "ok"), None)
    if nxt is not None:
        st.session_state[CUR] = nxt
        st.toast(f"{s['name']} confirmed")
    else:
        st.toast("All sections confirmed · ready for ranking")


cv = d.profile["cv"]
n = len(left)
shell.topbar("profile", store.nav_counts())
with shell.header(
    "Check what we read from your CV",
    f"{esc(cv['name'])} · {cv['pages']} pages · processed {esc(cv['processed'])} · "
    + (f"<b>{n} section{'s' if n != 1 else ''}</b> need a quick look before ranking" if n else "<b>all sections</b> confirmed"),
):
    if st.button("Replace CV", key="replace"):
        tabs.go("onboarding", step="1")
    if st.button("Send to ranking", type="primary" if not n else "secondary", key="send", disabled=bool(n)):
        tabs.go("matches")

# Pipeline steps.
done = [(CK, "Upload"), (CK, "Text extraction"), (CK, "AI extraction"), (CK, "Candidate profile")]
steps = "".join(f'<div class="stp"><span class="c">{i}</span>{t}</div><span class="sl"></span>' for i, t in done)
lock = (
    '<svg width="13" height="13" viewBox="0 0 16 16"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" '
    'stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" '
    'stroke="currentColor" stroke-width="1.6" fill="none"/></svg>'
)
if n:
    steps += (
        f'<div class="stp cur"><span class="c">5</span>Review &amp; correction <small>{n} to review</small></div>'
        f'<span class="sl d"></span><div class="stp lk"><span class="c">{lock}</span>Ranking</div>'
    )
else:
    steps += (
        f'<div class="stp"><span class="c">{CK}</span>Review &amp; correction</div><span class="sl d"></span>'
        '<div class="stp cur"><span class="c">6</span>Ranking <small style="color:var(--blue)">ready</small></div>'
    )
html(f'<div class="steps gl">{steps}</div>')

cur = st.session_state[CUR]
with st.container(key="pf-main"):
    with st.container(key="gl-prof"):
        html(
            '<div class="sh"><div><b>Candidate profile</b><span>What we read from your CV and your answers · '
            f'tap a section to see the evidence</span></div><span class="chip {"u" if n else "g"}">'
            f'{f"{n} to review" if n else "All confirmed"}</span></div>'
        )
        if not consent:
            html(
                f'<div class="consent-gate" role="status"><i></i><span><b>{NEEDS_CONSENT}.</b> '
                "The other sections open once you agree to how we process your CV.</span></div>"
            )
        with st.container(key="rows"):
            for i, s in enumerate(sections):
                sel = i == cur
                locked = not consent and i != CONSENT_AT
                ev = "<b>Your form</b> · given" if i == CONSENT_AT and consent else s["ev"]
                hit(
                    f"sec-{i}",
                    f'<div class="row tile{" sel" if sel else ""}{" lk" if locked else ""}"><span class="ico">{glyph(s["icon"], "#0071E3" if sel else None)}</span>'
                    f'<div class="nm">{esc(s["name"])}</div><div style="min-width:0"><div class="v1">{esc(s["v1"])}</div>'
                    f'<div class="v2">{esc(s["v2"])}</div></div><div class="ev">{ev}</div>'
                    f'<div class="stc">{chip(status[s["id"]])}</div></div>',
                    f"Show {s['name']}",
                    on_click=st.toast if locked else st.session_state.__setitem__,
                    args=(NEEDS_CONSENT,) if locked else (CUR, i),
                )
        html(
            '<div class="pfoot"><b>Demo profile</b> · every value is linked to a page and line '
            "in the synthetic demo CV</div>"
        )

    s = sections[cur]
    sid = s["id"]
    with st.container(key="pan-p"):
        html(
            f'<div class="pan"><div class="kk">Section {cur + 1} of {len(sections)} · Candidate profile</div>'
            f'<h3>{esc(s["name"])}{chip(status[sid])}</h3></div>'
        )
        # "Mark as incorrect" points at the values to correct instead of a toast.
        fix = st.session_state.get(FIX) == sid and status[sid] != "ok"
        html(
            f'<div class="lab{" fix" if fix else ""}">Extracted values<span>Tap a value to correct it</span></div>'
        )
        with st.container(key="vals-fix" if fix else "vals"):
            for j, (label, _) in enumerate(s["vals"]):
                val = values[sid][label]
                focus = s.get("focus_first") and j == 0 and status[sid] != "ok"
                with st.container(key=f"vr-{'f-' if focus else ''}{sid}-{j}"):
                    html(f"<span>{esc(label)}</span>")
                    with st.popover(f"{val} {md_icon(CHEV)}", key=f"pick-{sid}-{j}"):
                        opts = d.value_options.get(label, [val])
                        if val not in opts:
                            opts = [val, *opts]
                        new = st.selectbox(label, opts, index=opts.index(val), key=f"sel-{sid}-{j}")
                        if new != val:
                            values[sid][label] = new
                            status[sid] = "rev"
                            st.session_state.pop(FIX, None)
                            st.rerun()
        html(f'<div class="lab">Source evidence<span>{esc(s["qs"])}</span></div>')
        with st.container(key="qbox"):
            html(
                f'<div class="qbox"><div class="qsrc"><span class="srct">{s["tag"]}</span>{esc(s["qs"])}</div>'
                f'<div class="qt">{s["q"]}</div><div class="note">{esc(s["note"])}</div></div>'
            )
            if s.get("link"):
                if st.button(s["link"], type="tertiary", key="uk-link"):
                    tabs.go("question")
        chk = s["chk"]
        if sid == store.CONSENT_SECTION:  # the rule checks the consent as it is now
            chk = [(consent, t, "Pass" if consent else r) for _, t, r in chk]
        checks = "".join(
            f'<div class="ck"><span class="ci{"" if ok else " a"}">{CK if ok else WN}</span>{esc(t)}'
            f'<span class="s{"" if ok else " a"}">{esc(r)}</span></div>'
            for ok, t, r in chk
        )
        rules = len(s["chk"])
        sig = "".join(f'<span class="chip {c}">{esc(t)}</span>' for c, t in s["sig"])
        html(
            f'<div class="lab">Deterministic checks<span>{rules} rule{"s" if rules > 1 else ""}</span></div>'
            f'<div class="box">{checks}</div>'
            f'<div class="sig">{sig}</div>'
        )
        with st.container(key="pf-foot"):
            # Consent is given or not: there is nothing to correct.
            if sid != store.CONSENT_SECTION:
                st.button("Mark as incorrect", key="bad", on_click=mark_incorrect, args=(sid,))
            ok = status[sid] == "ok"
            st.button(
                "Confirmed" if ok else s.get("cta", "Confirm section"),
                type="secondary" if ok else "primary",
                key="ok",
                disabled=ok,
                on_click=confirm,
                args=(cur,),
            )
