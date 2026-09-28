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
    """The one chip a list row shows: applied, simulated, closing soon, or demo data.

    Demo postings have no source publication date, so no posting age is shown.

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
    return "", "Demo data"


#: A role's standing, in the words every list uses.
STANDING = {"eligible": "Eligible", "verify": "To verify", "excluded": "Excluded"}


def work_auth_check(v) -> tuple[str, str]:
    """The right-to-work line for a role, as a (kind, text) checklist row.

    Only renders the permission criterion the canonical HC_WORK_AUTH rule
    decided for the current answers (core.store.view); it decides nothing.

    Returns:
        ("ok", …) when met; ("gap", …) when it needs verification or conflicts.
    """
    status = v.criterion("permission").status
    where = f"Right to work in {v.city}"
    if status == "met":
        return "ok", f"{where} · confirmed"
    if status == "not_met":
        return "gap", f"{where} · conflict"
    return "gap", f"{where} · needs verification"


def eligibility_dot(v) -> str:
    """"● Eligible" / "● To verify" as the list shows it."""
    if v.standing == "eligible":
        return '<span class="k-el" style="color:var(--green)"><i style="background:var(--green)"></i>Eligible</span>'
    return '<span class="k-el" style="color:var(--amber)"><i style="background:#D98A1E"></i>To verify</span>'


# ───────────────────────── The one Matches ranking (core/matches.py) ─────────────────────────

MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
#: The small per-job disclosure a synthetic posting carries. It never groups or ranks.
DEMO_POSTING = "Demo posting"


def unified_bars(o) -> str:
    """The stacked contribution bar of a ranked opportunity."""
    segs = "".join(f'<i style="flex:{c:.2f};background:{COL[i]}"></i>' for i, c in enumerate(o.parts))
    rest = max(0.0, 100 - (o.raw or 0))
    return segs + f'<i style="flex:{rest:.2f};background:transparent"></i>'


def _date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTH_ABBR[int(m) - 1]}"


def factor_note(o, name: str) -> str:
    """What one factor rests on, in plain words. Ranking skills a curated role
    does not state are called typical for the role, never posting facts."""
    fit, e = o.profile, o.entry
    if name == "profile_fit":
        n, m = len(o.job_profile.skills), len(fit.matched_skills)
        typical = len(o.topped_up_skills)
        skills = f"{m} of {n} skills" + (f" ({typical} typical for the role)" if typical else "")
        edu = {100.0: "degree and field match", 50.0: "degree or field matches", 0.0: "degree and field differ"}
        bits = [skills, edu.get(fit.education_field, "")]
        if fit.experience is not None and fit.experience < 100:
            bits.append("less experience than asked")
        return " · ".join(b for b in bits if b)
    if name == "preference_fit":
        sub = e.preference.subfactors
        bits = []
        if sub.get("location") is not None:
            bits.append(f"{o.city} is a preferred place" if sub["location"] else "Not a preferred place")
        if sub.get("role_family") is not None:
            bits.append(f"{o.role_family} role" if sub["role_family"] else "Other role family")
        return " · ".join(bits)
    if name == "deadline_urgency":
        return f"Applications close {_date(o.closes)}"
    days = e.freshness.age_days
    if days is None:
        return ""
    n = int(days)
    return ("Found today" if n == 0 else f"Found {n} day{'s' if n != 1 else ''} ago") + " · simulated"


def unified_factor_rows(o) -> str:
    """Four rows: factor · its score, its weighted points and weight, a note."""
    from core.matches import FACTOR_NAMES, FACTORS, WEIGHTS

    rows = []
    for i, k in enumerate(FACTORS):
        rows.append(
            f'<div class="kci"><span class="sw" style="background:{COL[i]}"></span>'
            f'<span class="nm">{FACTOR_NAMES[k]} · {int(o.factor(k) + 0.5)}</span>'
            f'<span class="pt"><b>+{o.parts[i]:.1f}</b><span>× {int(WEIGHTS[k] * 100)}%</span></span>'
            f'<span class="kw">{esc(factor_note(o, k))}</span></div>'
        )
    return "".join(rows)


def unified_tag(o) -> tuple[str, str]:
    """The one chip a Matches row shows: applied, closing soon, or its demo label."""
    app = application_for(o.role_id)
    if app and app["stage"] in ("applied", "interview"):
        return "g", app["note"].split(" · ")[0].replace("Sent", "Applied")
    n = clock.days_until(o.closes)
    if n <= 9:
        return "u", f"Closes in {n} days"
    return "", DEMO_POSTING if o.kind == "synthetic" else "Demo data"


def verify_note(o) -> str:
    """For a job to verify: how it is ordered. Its Priority score is unchanged."""
    return "Ordered 15 points lower until verified · its Priority score is unchanged" if o.standing == "verify" else ""


def priority_text(role_id: str) -> str:
    """A role's raw Priority score as the screens print it, or "—" when not ranked."""
    n = store.priority(role_id)
    return "—" if n is None else str(n)


def priority_width(role_id: str) -> int:
    """The width, in percent, of a role's score bar."""
    return store.priority(role_id) or 0
