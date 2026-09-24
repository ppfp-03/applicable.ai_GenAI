"""Profile — check what we read from your CV (02_Profile_Intake.html).

Seven sections, each with the values we extracted, the CV lines they came
from and the deterministic checks that ran on them. The user confirms or
corrects each; only when every section is confirmed does the profile go to
ranking. Nothing is inferred silently: an inferred value is marked, and a
missing one says "Not stated in your CV".
"""

from __future__ import annotations

import streamlit as st

from core import store
from ui import shell
from ui.html import CHEV, CK, WN, esc, glyph, hit, html, md_icon
from ui.theme import page_css

d = store.data()
page_css("profile")

status = st.session_state[store.SECTIONS]
values = st.session_state[store.VALUES]
sections = d.sections
CUR = "profile_cur"
st.session_state.setdefault(CUR, next((i for i, s in enumerate(sections) if s.get("focus_first")), 0))
left = [s for s in sections if status[s["id"]] != "ok"]
CHIP = {"ok": ("g", "Confirmed"), "rev": ("u", "Needs review"), "pend": ("u", "Pending")}


def chip(st_: str) -> str:
    c, t = CHIP[st_]
    return f'<span class="chip {c}">{t}</span>'


def confirm(i: int) -> None:
    s = sections[i]
    status[s["id"]] = "ok"
    if s["id"] == "decl":
        values["decl"] = {"Accuracy attestation": "Signed", "Data processing consent": "Given"}
    note = st.session_state.get(f"note-{s['id']}", "").strip()
    if note:
        st.session_state[store.NOTES].setdefault(s["id"], []).append(note)
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
        st.switch_page("views/onboarding.py", query_params={"step": "1"})
    if st.button("Send to ranking", type="primary" if not n else "secondary", key="send", disabled=bool(n)):
        st.switch_page("views/matches.py")

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
with st.container(key="main"):
    with st.container(key="gl-prof"):
        html(
            '<div class="sh"><div><b>Candidate profile</b><span>What we read from your CV and your answers · '
            f'tap a section to see the evidence</span></div><span class="chip {"u" if n else "g"}">'
            f'{f"{n} to review" if n else "All confirmed"}</span></div>'
        )
        with st.container(key="rows"):
            for i, s in enumerate(sections):
                sel = i == cur
                hit(
                    f"sec-{i}",
                    f'<div class="row tile{" sel" if sel else ""}"><span class="ico">{glyph(s["icon"], "#0071E3" if sel else None)}</span>'
                    f'<div class="nm">{esc(s["name"])}</div><div style="min-width:0"><div class="v1">{esc(s["v1"])}</div>'
                    f'<div class="v2">{esc(s["v2"])}</div></div><div class="ev">{s["ev"]}</div>'
                    f'<div class="stc">{chip(status[s["id"]])}</div></div>',
                    f"Show {s['name']}",
                    on_click=st.session_state.__setitem__,
                    args=(CUR, i),
                )
        html(
            '<div class="pfoot"><b>Run ex_7f3a92</b> · extraction schema v2.3 · 42 fields · 38 extracted · 4 empty · '
            "every value is linked to a page and line in your CV · last edit 00:44</div>"
        )

    s = sections[cur]
    sid = s["id"]
    with st.container(key="pan-p"):
        html(
            f'<div class="pan"><div class="kk">Section {cur + 1} of {len(sections)} · Candidate profile</div>'
            f'<h3>{esc(s["name"])}{chip(status[sid])}</h3></div>'
        )
        html('<div class="lab">Extracted values<span>Tap a value to correct it</span></div>')
        with st.container(key="vals"):
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
                            st.rerun()
        html(f'<div class="lab">Source evidence<span>{esc(s["qs"])}</span></div>')
        with st.container(key="qbox"):
            html(
                f'<div class="qbox"><div class="qsrc"><span class="srct">{s["tag"]}</span>{esc(s["qs"])}</div>'
                f'<div class="qt">{s["q"]}</div><div class="note">{esc(s["note"])}</div></div>'
            )
            if s.get("link"):
                if st.button(s["link"], type="tertiary", key="uk-link"):
                    st.switch_page("views/question.py")
        checks = "".join(
            f'<div class="ck"><span class="ci{"" if ok else " a"}">{CK if ok else WN}</span>{esc(t)}'
            f'<span class="s{"" if ok else " a"}">{esc(r)}</span></div>'
            for ok, t, r in s["chk"]
        )
        rules = len(s["chk"])
        sig = "".join(f'<span class="chip {c}">{esc(t)}</span>' for c, t in s["sig"])
        html(
            f'<div class="lab">Deterministic checks<span>{rules} rule{"s" if rules > 1 else ""}</span></div>'
            f'<div class="box">{checks}</div>'
            f'<div class="sig">{sig}</div>'
        )
        with st.container(key="note"):
            html('<div class="lab">Correction note<span>Saved to your audit log</span></div>')
            st.text_area(
                "Correction note",
                key=f"note-{sid}",
                placeholder="Explain what you changed, e.g. “Singapore: requires Employment Pass sponsorship.”",
                label_visibility="collapsed",
            )
        with st.container(key="foot"):
            if st.button("Mark as incorrect", key="bad"):
                status[sid] = "rev"
                st.toast("Correct the values above, then add a note")
            ok = status[sid] == "ok"
            st.button(
                "Confirmed" if ok else s.get("cta", "Confirm section"),
                type="secondary" if ok else "primary",
                key="ok",
                disabled=ok,
                on_click=confirm,
                args=(cur,),
            )
