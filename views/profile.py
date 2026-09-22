"""Profile — what we understood about you, and where each line came from.

A structured professional profile, not a CV dumped on a page. Three things
make the difference: what we could not read with confidence sits at the top
rather than hidden in the middle; the facts that feed the hard rules are
grouped together and marked as such; and every value carries its source, so
nothing here has to be taken on trust.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from oi.contracts import Source

from core import demo, state
from ui.components import mark, mono_tile, source_line

data = demo.load()
state.init(data)

profile = data.profile
to_confirm = profile.get("to_confirm", [])

main, rail = st.columns([2.3, 1], gap="large")

with main:
    st.html(
        f'<div class="aa" style="display:flex;gap:18px;align-items:flex-start">'
        f"{mono_tile(profile['name'], 56, 'brand')}"
        f'<div><h1 class="aa-h-title">{escape(profile["name"])}</h1>'
        f'<p class="aa-lead" style="margin-top:4px">{escape(profile["headline"])} · '
        f"{len(profile['experience'])} roles · {len(profile['skills'])} skills"
        f"</p></div></div>"
    )

    cv_tab, facts_tab = st.tabs(["From your CV", "Facts you told us"])

    with cv_tab:
        if to_confirm:
            with st.container(border=True, key="confirm-card"):
                st.html(
                    f'<p class="aa aa-label" style="color:var(--clarify)">'
                    f"{len(to_confirm)} things to confirm · they feed the rules</p>"
                )
                for i, item in enumerate(to_confirm):
                    line, actions = st.columns([3, 1], vertical_alignment="center")
                    with line:
                        st.html(
                            f'<div class="aa" style="padding-top:6px">'
                            f'<p style="margin:0;font-weight:600">'
                            f'{escape(item["label"])} '
                            f'<span class="aa-hl">{escape(item["value"])}</span></p>'
                            f'<p style="margin-top:5px">'
                            f'{source_line(Source(**item["source"]))}'
                            f' · {escape(item["note"])}</p></div>'
                        )
                    with actions:
                        st.button("Confirm", key=f"confirm-{i}", use_container_width=True)

        st.html(
            '<div class="aa" style="margin-top:26px">'
            '<p class="aa-sech">Facts the rules read</p>'
            '<p class="aa-small">These four decide what you are eligible for. '
            "Everything else only changes the order.</p></div>"
        )
        with st.container(border=True):
            rows = [
                ("Citizenship", f"{profile['citizenship']} · EU/EFTA", "CV", "p.1 · Personal"),
                ("Graduating", str(profile["graduation_year"]), "CV", "p.1 · Education"),
                ("Available", f"{data.preferences['available_from']} – {data.preferences['available_until']}", "YOU", "14 Sep 2026"),
                ("Countries", ", ".join(data.preferences["countries"]), "YOU", "Preferences"),
            ]
            for label, value, kind, where in rows:
                st.html(
                    f'<div class="aa aa-fact"><span class="k">{escape(label)}</span>'
                    f"<span>{escape(value)}</span>"
                    f'<span class="d"><span class="aa-src">'
                    f'<span class="aa-doc">{kind}</span>{escape(where)}</span></span></div>'
                )

        st.html(
            '<div class="aa" style="margin-top:26px"><h2 class="aa-h">Skills we can quote</h2>'
            '<p class="aa-small" style="margin-top:4px">Each one points back to the '
            "line it came from.</p></div>"
        )
        st.html(
            '<div class="aa aa-row" style="gap:8px;margin-top:12px">'
            + "".join(
                f'<span class="aa-tag" style="height:32px">{escape(s)}</span>'
                for s in profile["skills"][:8]
            )
            + f'<span class="aa-tag" style="height:32px;border:1px dashed '
            f'var(--line-control);background:transparent">'
            f'{len(profile["skills"]) - 8} more</span></div>'
        )

        st.html('<div class="aa" style="margin-top:26px"><h2 class="aa-h">Experience</h2></div>')
        items = "".join(
            f'<div class="aa-tl-item{"" if e["current"] else " past"}">'
            f'<p class="when">{escape(e["when"])}</p>'
            f'<p style="margin:3px 0 0;font-weight:700">{escape(e["role"])} · '
            f'{escape(e["org"])}</p>'
            f'<p class="aa-small">{escape(e["city"])} · '
            f'{mark(e["note"])}'
            f"</p></div>"
            for e in profile["experience"]
        )
        st.html(f'<div class="aa aa-tl" style="margin-top:14px">{items}</div>')

    with facts_tab:
        facts = st.session_state.get(state.FACTS, [])
        if not facts:
            st.html(
                '<div class="aa aa-empty" style="margin-top:16px">'
                '<p class="aa-h-sm">Nothing yet</p>'
                '<p class="aa-small" style="margin-top:6px">Answers you give on '
                "Today land here, with the date, and are never asked again.</p></div>"
            )
        for fact in facts:
            question = next(
                (q for q in data.questions if q.id == fact["key"]), None
            )
            st.html(
                f'<div class="aa aa-fact">'
                f'<span class="k">{escape(question.text if question else fact["key"])}</span>'
                f'<span>{escape(fact["value"])}</span>'
                f'<span class="d"><span class="aa-src">'
                f'<span class="aa-doc">YOU</span>{escape(fact["date"])}</span></span></div>'
            )

with rail:
    st.write("")
    cv = profile["cv_file"]
    with st.container(border=True):
        st.html(
            f'<div class="aa"><p class="aa-label">Your CV</p>'
            f'<p style="margin:12px 0 0;font-weight:700;font-size:14px">'
            f'{escape(cv["name"])}</p>'
            f'<p class="aa-small" style="margin-top:3px">{cv["pages"]} pages · '
            f'read {escape(cv["read_on"])}</p></div>'
        )
        st.button("Replace CV", use_container_width=True)
    with st.container(border=True):
        st.html(
            '<p class="aa aa-small" style="margin:0">Nothing here is shared with '
            "employers. You send every application yourself.</p>"
        )
