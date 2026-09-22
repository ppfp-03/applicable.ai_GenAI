"""Preferences — what you want, and how much each thing should count.

Two halves, and the line between them is the point of the page. The top half
is what you are looking for; the bottom half is how the four factors are
weighed. Neither can make you eligible for something a rule rules out, and
the page says so where a reader would otherwise assume otherwise.

The rail shows the effect of a change before it is saved, computed with the
same function that would apply it. An effect that is estimated rather than
computed would be worse than none.
"""

from __future__ import annotations

import streamlit as st

from core import demo, ranking, state

data = demo.load()
state.init(data)

prefs = data.preferences
labels = prefs.get("country_labels", {})

st.html(
    '<div class="aa"><h1 class="aa-h-title">Preferences</h1>'
    '<p class="aa-lead" style="margin-top:6px">What you want, and how much each '
    "thing should count. Nothing here decides eligibility.</p></div>"
)

main, rail = st.columns([2.2, 1], gap="large")

with main:
    st.html('<div class="aa" style="margin-top:22px"><h2 class="aa-h">What you are looking for</h2></div>')

    with st.container(border=True):
        st.html('<p class="aa aa-sech">Countries</p>')
        countries = st.pills(
            "Countries",
            list(labels.values()),
            default=[labels[c] for c in prefs["countries"] if c in labels],
            selection_mode="multi",
            key="pref-countries",
            label_visibility="collapsed",
        )

        st.html('<p class="aa aa-sech" style="margin-top:18px">Role types</p>')
        st.pills(
            "Role types",
            ["Internship", "Graduate programme", "Off-cycle", "Full-time"],
            default=prefs["role_types"],
            selection_mode="multi",
            key="pref-roles",
            label_visibility="collapsed",
        )

        since, until = st.columns(2)
        with since:
            st.text_input("Available from", value=prefs["available_from"])
        with until:
            st.text_input("Available until", value=prefs["available_until"])
        st.html(
            f'<p class="aa aa-small">We already block {prefs["blocked"]}, read '
            f"from your CV.</p>"
        )

        st.html('<p class="aa aa-sech" style="margin-top:18px">Hours a week for applications</p>')
        st.segmented_control(
            "Hours",
            [3, 5, 8, 10],
            default=int(data.hours_budget),
            format_func=lambda h: f"{h} h",
            key="pref-hours",
            label_visibility="collapsed",
        )
        st.html(
            '<p class="aa aa-small">This is what keeps the weekly list finite. '
            "Five hours is about three applications.</p>"
        )

    st.html(
        '<div class="aa" style="margin-top:30px"><h2 class="aa-h">How we rank</h2>'
        '<p class="aa-small" style="margin-top:4px">Four factors. Raising one '
        "lowers the others' share of the same 100 points.</p></div>"
    )

    with st.container(border=True):
        weights = {}
        for key, (name, note) in data.factor_labels.items():
            st.html(
                f'<div class="aa" style="margin-top:10px">'
                f'<p style="margin:0;font-weight:700">{name}</p>'
                f'<p class="aa-small">{note}</p></div>'
            )
            weights[key] = st.slider(
                name,
                min_value=0,
                max_value=60,
                value=int(prefs["weights"][key] * 100),
                step=5,
                format="%d%%",
                key=f"w-{key}",
                label_visibility="collapsed",
            )

with rail:
    st.write("")
    total = sum(weights.values()) or 100
    normalised = {k: v / total for k, v in weights.items()}
    changed = any(
        abs(normalised[k] - prefs["weights"][k]) > 0.005 for k in normalised
    )

    with st.container(border=True, key="effect-card"):
        st.html('<p class="aa aa-label" style="color:var(--go)">Live effect</p>')
        if not changed:
            st.html(
                '<p class="aa aa-small" style="margin-top:8px">Balanced, as it '
                "was. Move a slider to see what would change.</p>"
            )
        else:
            before = ranking.rank(data.opportunities)
            after = sorted(
                data.opportunities,
                key=lambda o: (
                    0 if o.verdict == "apply" else 1,
                    -ranking.score_with(o, normalised),
                ),
            )
            moved = [
                (o, i + 1, before.index(o) + 1)
                for i, o in enumerate(after)
                if before.index(o) != i
            ]
            st.html(
                f'<p class="aa aa-small" style="margin-top:8px">If you save '
                f"these weights:</p>"
                f'<div class="aa"><div class="aa-fact" style="border-top:0">'
                f'<span class="k">{len(moved)}</span>'
                f'<span class="aa-small">roles change position</span></div>'
                + "".join(
                    f'<div class="aa-fact"><span class="k">#{was} → #{now}</span>'
                    f'<span class="aa-small">{o.company} · {o.title}</span></div>'
                    for o, now, was in moved[:3]
                )
                + "</div>"
            )
        st.html(
            '<p class="aa aa-small" style="margin-top:12px">Weights change the '
            "order of what you see, never whether you are allowed to apply.</p>"
        )
        st.button("Save preferences", type="primary", use_container_width=True)
