"""Markup pieces more than one screen draws: score bars, factor rows, the
formula, the eligibility gate, role tags.

Colours are the mockups' (blue scale); ui.html.html() maps them to orange.
"""

from __future__ import annotations

from core import clock, ranking, store
from ui.html import CK, WN, esc

#: One colour per factor, strongest first, as in the mockups' legend.
COL = ["#0071E3", "#5AA2F0", "#A9CDF7", "#D6E7FB"]


def bars(v) -> str:
    """The stacked contribution bar: four segments, then the empty rest."""
    segs = "".join(
        f'<i style="flex:{c:.2f};background:{COL[i]}"></i>' for i, c in enumerate(v.parts)
    )
    rest = max(0.0, 100 - v.raw)
    return segs + f'<i style="flex:{rest:.2f};background:transparent"></i>'


def factor_rows(v) -> str:
    """Four rows: factor · score, its note, and the points it adds."""
    w = store.data().weights
    rows = []
    for i, k in enumerate(ranking.FACTORS):
        score, note = v.factors[k]
        rows.append(
            f'<div class="kci"><span class="sw" style="background:{COL[i]}"></span>'
            f'<span class="nm">{ranking.FACTOR_NAMES[k]} · {score}</span>'
            f'<span class="pt"><b>+{v.parts[i]:.1f}</b><span>× {int(w[k] * 100)}%</span></span>'
            f'<span class="kw">{esc(note)}</span></div>'
        )
    return "".join(rows)


def formula(v) -> str:
    """The weighted sum written out, with the penalty when there is one."""
    w = store.data().weights
    f = [v.factors[k][0] for k in ranking.FACTORS]
    line = (
        f"score = {w['profile']:.2f} × {f[0]} + {w['preference']:.2f} × {f[1]}<br>"
        f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ {w['urgency']:.2f} × {f[2]} + {w['freshness']:.2f} × {f[3]} = {v.raw:.1f}"
    )
    if v.standing == "verify":
        line += f"<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;− {store.data().penalty:g} until verified = {v.score:.1f}"
    return line


def gate(v) -> str:
    """The RULE line under the score: ranking never changes eligibility."""
    if v.standing == "eligible":
        return (
            f'<span class="ci">{CK}</span><div><div style="font-weight:600"><span class="srct" style="margin-right:6px">'
            f"RULE</span>Eligible under checked rules · {v.met} of 8</div>"
            '<div class="s2">Ranking orders eligible roles. It never changes eligibility.</div></div>'
        )
    open_ = next((c for c in v.criteria if c.status != "met"), None)
    why = f"{open_.value}." if open_ else ""
    return (
        f'<span class="ci a">{WN}</span><div><div style="font-weight:600"><span class="srct" style="margin-right:6px">'
        f"RULE</span>To verify · {v.met} of 8 rules pass</div>"
        f'<div class="s2">{esc(why)} Ranking never changes eligibility.</div></div>'
    )


def application_for(role_id: str) -> dict | None:
    """The user's application for a role, if any."""
    return next((a for a in store.applications() if a["role"] == role_id), None)


def tag(v) -> tuple[str, str]:
    """The one chip a list row shows: applied, simulated, closing soon, or how fresh.

    Returns:
        (chip class, text) -- class "g" green, "u" amber, "" neutral.
    """
    app = application_for(v.id)
    if app and app["stage"] in ("applied", "interview"):
        when = app["note"].split(" · ")[0].replace("Sent", "Applied")
        return "g", when
    if store.is_simulated(v):
        return "", store.data().simulated_event["label"]
    n = clock.days_until(v.closes)
    if n <= 9:
        return "u", f"Closes in {n} days"
    p = v.posted_days_ago
    return "", "Posted today" if p == 0 else "Posted yesterday" if p == 1 else f"Posted {p} days ago"


def eligibility_dot(v) -> str:
    """"● Eligible" / "● To verify" as the list shows it."""
    if v.standing == "eligible":
        return '<span class="k-el" style="color:var(--green)"><i style="background:var(--green)"></i>Eligible</span>'
    return '<span class="k-el" style="color:var(--amber)"><i style="background:#D98A1E"></i>To verify</span>'
