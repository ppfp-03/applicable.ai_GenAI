"""Set up — the three steps between a CV and a first week.

Step 2 is the one that matters and the one most products skip: showing what
was read before anything is built on it. Only the two or three fields we are
unsure about are put to the user; confirming twenty correct ones would teach
them to click through without looking.

Nothing is asked here that a posting has not yet needed. Visas, languages and
licences become a single question later, when a real role depends on the
answer.
"""

from __future__ import annotations

import streamlit as st

from core import demo, state
from ui.components import source_line
from oi.contracts import Source

data = demo.load()
state.init(data)

profile = data.profile
step = st.session_state.setdefault("setup-step", 2)

st.html(
    f'<div class="aa aa-steps" style="justify-content:center">'
    f'<span class="{"done" if step > 1 else "on"}"><i>✓</i>Upload</span>'
    f'<span class="sep"></span>'
    f'<span class="{"on" if step == 2 else ""}"><i>2</i>What we understood</span>'
    f'<span class="sep"></span>'
    f'<span class="{"on" if step == 3 else ""}"><i>3</i>Essentials</span></div>'
)

_, middle, _ = st.columns([1, 2.4, 1])

with middle:
    st.html(
        '<div class="aa" style="margin-top:30px">'
        '<p class="aa-label">Step 2 of 3 · about a minute</p>'
        '<h1 class="aa-h-title" style="margin-top:8px">This is what we '
        "understood</h1>"
        '<p class="aa-lead" style="margin-top:7px">We read your CV once. Correct '
        "anything that is wrong — every verdict later rests on it.</p></div>"
    )

    st.write("")
    summary = st.columns(4)
    cells = [
        (len(profile["experience"]), "roles"),
        (14, "months of work"),
        (len(profile["skills"]), "skills we can quote"),
        (len(profile["languages"]), "languages"),
    ]
    for column, (value, label) in zip(summary, cells):
        with column:
            st.html(
                f'<div class="aa aa-well" style="padding:16px">'
                f'<span style="font:800 26px/1 var(--font-display)">{value}</span>'
                f'<p class="aa-small" style="margin-top:6px">{label}</p></div>'
            )

    st.write("")
    with st.container(border=True, key="understood-card"):
        st.html(
            f'<p class="aa aa-label" style="color:var(--clarify)">'
            f'{len(profile["to_confirm"])} things we could not read with '
            f"confidence</p>"
        )
        for i, item in enumerate(profile["to_confirm"]):
            st.html(
                f'<div class="aa" style="margin-top:16px">'
                f'<p style="margin:0;font-weight:600">{item["label"]} '
                f'<span class="aa-hl">{item["value"]}</span></p>'
                f'<p style="margin-top:5px">{source_line(Source(**item["source"]))}'
                f' · {item["note"]}</p></div>'
            )
            st.pills(
                item["label"],
                ["That is right", "Let me correct it"],
                key=f"setup-confirm-{i}",
                label_visibility="collapsed",
            )

    st.write("")
    with st.container(border=True):
        st.html(
            '<p class="aa aa-small" style="margin:0">✦ We will not ask about '
            "visas, languages or driving licences now. Each becomes one question "
            "only when a real posting needs the answer.</p>"
        )

    st.write("")
    back, forward = st.columns([1, 1])
    with back:
        st.button("Back", use_container_width=True)
    with forward:
        st.button("Looks right", type="primary", use_container_width=True)
