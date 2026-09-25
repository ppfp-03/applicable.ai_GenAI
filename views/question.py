"""One quick question — the answer that moves the most roles
(04_Clarification_Question.html).

Asked only because a fixed rule cannot decide 14 roles without it. The
right-hand preview recomputes live for whichever answer is selected: the
same rules and arithmetic that run after saving, run now on a copy of the
answers, so what the preview promises is exactly what saving does.
"""

from __future__ import annotations

import streamlit as st

from core import store
from ui import shell, tabs
from ui.html import CLOCK, SH, esc, hit, html, logo
from ui.theme import page_css

d = store.data()
page_css("question")

PICK = "q_choice"
st.session_state.setdefault(PICK, store.uk() or "yes")
choice = st.session_state[PICK]

before = store.counts(None)
after = {k: store.counts(k) for k in store.UK_CHOICES}
cat = d.catalog
uk_roles = [v for v in store.views() if v.country == "GB" and not v.get("new")]


def pick(k: str) -> None:
    st.session_state[PICK] = k


shell.topbar("home", store.nav_counts())
with shell.header(
    "One quick question",
    f"Asked only because <b>{cat['uk_roles']} roles</b> depend on it · your answer updates one profile field",
):
    if st.button("Answer later", key="later"):
        tabs.go("home")

OPTIONS = [
    ("yes", "Yes, I can work in the UK", "For example UK/Irish citizen, settled status or a valid work visa",
     f"+{after['yes']['eligible'] - before['eligible']} roles", "gr"),
    ("no", "No, I’d need sponsorship", "We’ll keep only roles that sponsor visas",
     f"{after['no']['eligible'] - before['eligible']} roles stay", "am"),
    ("unsure", "I’m not sure", "Roles stay marked “to check” for now", "No change", "ne"),
]

with st.container(key="main"):
    with st.container(key="card-q"):
        with st.container(key="qin"):
            logos = "".join(logo(v.mono, v.bg, 28, 10.5, 8) for v in uk_roles[:4])
            names = ", ".join(v.company for v in uk_roles[:3])
            html(
                '<div class="kk"><i style="background:#0071E3"></i>Question 1 of 1 · about 10 seconds</div>'
                '<div class="q-h">Can you work in the UK without visa sponsorship?</div>'
                "<div class=\"q-sub\">It’s not stated in your CV, and it’s the only thing still deciding "
                f"<b>{cat['uk_roles']} roles in London</b>.</div>"
                f'<div class="q-meta"><span class="chip u">{CLOCK}{cat["uk_closing_this_week"]} of these roles close this week</span>'
                f'<div class="logos">{logos}<span class="more">{esc(names)} and {cat["uk_roles"] - 3} more</span></div></div>'
            )
            with st.container(key="opts"):
                for n, (k, title, sub, fx, fc) in enumerate(OPTIONS, start=1):
                    with st.container(key=f"hit-opt-{k}"):
                        html(
                            f'<div class="opt tile{" sel" if k == choice else ""}"><span class="rd"></span>'
                            f'<div><div class="ot">{esc(title)}</div><div class="os">{esc(sub)}</div></div>'
                            f'<span class="fx {fc}">{esc(fx)}</span><span class="kbd">{n}</span></div>'
                        )
                        st.button(title, key=f"ov-opt-{k}", on_click=pick, args=(k,), shortcut=str(n))
            html(
                '<div class="why"><div class="lab">Why we’re asking<span>From your CV</span></div><div class="cs">'
                '<span class="c2"><span class="srct">CV</span>Nationality · <b>Italian</b> <span class="p2">p.2</span></span>'
                '<span class="c2"><span class="srct">CV</span>Current visa · <b>China X1</b> <span class="p2">p.2</span></span>'
                '<span class="c2 miss">UK right to work · Not stated in your CV</span></div></div>'
            )
            with st.container(key="qfoot"):
                html(
                    '<div class="nt">Saved as <b>Work authorization · UK</b> in your profile.<br>'
                    "You can change it anytime.</div>"
                )
                if st.button("Skip", key="q-skip", shortcut="Escape"):
                    st.session_state["flash"] = "Skipped · we’ll ask again later"
                    tabs.go("home")
                if st.button("Save answer", type="primary", key="q-save", shortcut="Enter"):
                    store.set_uk(choice)
                    st.session_state["flash"] = f"Answer saved · Work authorization · UK = {store.UK_LABELS[choice]}"
                    tabs.go("matches")

    # Live preview: the same rules, run on the selected answer.
    with st.container(key="pan-q"):
        html('<div class="pan"><div class="kk">Live preview</div><h3>Your matches after answering</h3></div>')
        with st.container(key="seg"):
            for k, label in (("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")):
                st.button(label, key=f"seg-{'on-' if k == choice else ''}{k}", on_click=pick, args=(k,))

        def v3(old: int, new: int) -> str:
            if old == new:
                return str(new)
            delta = new - old
            return f'<s>{old}</s>{new}<small style="color:var(--green)">{"+" if delta > 0 else "−"}{abs(delta)}</small>'

        a = after[choice]
        html(
            '<div class="stats">'
            f'<div class="stt box"><div class="k2">Eligible roles</div><div class="v3">{v3(before["eligible"], a["eligible"])}</div></div>'
            f'<div class="stt box"><div class="k2">To check</div><div class="v3">{v3(before["verify"], a["verify"])}</div></div></div>'
        )
        ans = {**store.answers(), "uk_work": choice}
        base = {**store.answers(), "uk_work": None}
        moves = store.movement(base, ans)
        rows = []
        for i, v in enumerate(store.ranked(ans)[:5], start=1):
            mv = moves.get(v.id, "—")
            cls = "nw" if mv == "New" else "up" if mv.startswith("↑") else "dn"
            where = v.city
            if v.country == "GB" and v.standing == "verify":
                where += " · sponsors visas" if choice == "no" else " · to verify"
            rows.append(
                f'<div class="ri"><span class="p">{i}</span>{logo(v.mono, v.bg, 30, 10.5, 8)}'
                f'<div><div class="nm">{esc(v.title)}</div><div class="co">{esc(v.company)} · {esc(where)}</div></div>'
                f'<span class="mv {cls}">{mv}</span></div>'
            )
        note = {
            "yes": "Updated ranking",
            "no": f"{a['excluded'] - before['excluded']} roles move to Excluded · you can undo",
            "unsure": "No change · we’ll ask again later",
        }[choice]
        html(f'<div class="lab">Top matches<span>{esc(note)}</span></div><div class="box">{"".join(rows)}</div>')
        new_chip = {
            "yes": '<span class="chip g" style="padding:3px 10px">Yes</span>',
            "no": '<span class="chip u" style="padding:3px 10px">No · needs sponsorship</span>',
            "unsure": '<span class="chip" style="padding:3px 10px">Not sure</span>',
        }[choice]
        html(
            '<div class="lab">Profile update<span>1 field</span></div><div class="box upd"><div>'
            '<div class="nm">Work authorization · UK</div><div class="co">Predefined profile field</div></div>'
            '<span style="margin-left:auto;display:flex;align-items:center;gap:8px"><span class="old">Unknown</span>'
            f'<span style="color:#AEAEB2">→</span>{new_chip}</span></div>'
        )
        with st.container(key="end-q"):
            html(
                f'<div class="flow">{SH}<div><span class="srct" style="margin-right:6px">RULE</span>'
                "You answer → one profile field updates → fixed rules recalculate your matches. "
                "Nothing is sent to employers.</div></div>"
            )
