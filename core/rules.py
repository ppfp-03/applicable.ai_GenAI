"""Deterministic eligibility rules for the seven non-permission criteria.

Permission to work is not decided here: it comes from the canonical
HC_WORK_AUTH rule (core/eligibility.py) and is passed in. No model input
reaches this module and none of its outputs depend on one: given the same
facts it always returns the same answer, and every answer names the rule that
produced it.

That separation is the point. A language model may explain what these rules
concluded; it may never conclude it. "The model said so" is not something a
user can check. This is not legal advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Bump when a rule changes.
RULES_VERSION = "2026-09-26"


# ───────────────────────── The eight fixed criteria ─────────────────────────
#
# Every role is checked against the same eight criteria, in the same order.
# The model only reads the posting into `requirements`; everything below is
# table lookup and comparison. Each outcome says which rule decided it, so the
# screen can print "Fixed rules decide, not AI" and mean it.

#: Criterion ids, in the order they are always evaluated and listed.
CRITERIA = (
    "location",
    "permission",
    "student",
    "graduation",
    "degree",
    "field",
    "language",
    "experience",
)

#: Display names, as the eligibility screen shows them.
CRITERION_NAMES = {
    "location": "Location",
    "permission": "Permission to work",
    "student": "Student status",
    "graduation": "Graduation",
    "degree": "Degree level",
    "field": "Field of study",
    "language": "Language",
    "experience": "Experience",
}

#: Known proficiency scales, lowest to highest. "native" beats every level.
_SCALES = (
    ("A1", "A2", "B1", "B2", "C1", "C2"),
    ("HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6"),
)
_DEGREES = ("bachelor", "master", "phd")
_DEGREE_LABEL = {"bachelor": "Bachelor’s", "master": "Master’s", "phd": "PhD"}
_DEGREE_SHORT = {"bachelor": "BSc", "master": "MSc", "phd": "PhD"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class Criterion:
    """One criterion's outcome for one role.

    Attributes:
        id: One of CRITERIA.
        name: Display name.
        status: "met", "check" (we need one more fact) or "not_met".
        value: The short line under the name on a tile.
        detail: One sentence saying what the rule compared.
        rule: The rule as it would be written down, for "How it was decided".
        have: What the profile says, for comparisons ("HSK 4").
        need: What the posting asks, for comparisons ("HSK 6").
    """

    id: str
    name: str
    status: str
    value: str
    detail: str
    rule: str
    have: str = ""
    need: str = ""


def _month(ym: str) -> str:
    """'2027-07' -> 'Jul 2027'."""
    year, month = ym.split("-")
    return f"{_MONTHS[int(month) - 1]} {year}"


def level_gap(have: Optional[str], need: str) -> Optional[int]:
    """How many levels `have` is above (+) or below (-) `need`.

    Args:
        have: The candidate's level, e.g. "HSK 4", "C1" or "native".
        need: The required level on the same scale.

    Returns:
        The signed gap, or None when the level is missing or the two are not
        on a scale we know (then we ask rather than guess).
    """
    if have is None:
        return None
    if have == "native":
        return 99
    for scale in _SCALES:
        if have in scale and need in scale:
            return scale.index(have) - scale.index(need)
    return None


def _language(profile: dict, role: dict, answers: dict | None = None) -> Criterion:
    """Every language the posting requires, at the level it requires.

    A certificate the user adds (answers["languages"]) updates their level.
    """
    have_all = {**profile.get("languages", {}), **((answers or {}).get("languages") or {})}
    worst: Optional[Criterion] = None
    for lang, need in role["requirements"].get("languages", {}).items():
        have = have_all.get(lang)
        gap = level_gap(have, need)
        label = f"{lang} level"
        if gap is None:
            c = Criterion("language", label, "check", f"{lang} · not stated",
                          f"{lang} is required at {need}; it is not stated in your CV.",
                          f"{lang} ≥ {need}", have or "", need)
        elif gap < 0:
            c = Criterion("language", label, "not_met", f"{have} · {need} required",
                          f"The role requires {need}. Your profile shows {have}.",
                          f"{have} ≥ {need} → false", have, need)
        else:
            c = Criterion("language", label, "met", f"{lang} {have}",
                          f"The role requires {need}. Your profile shows {have}.",
                          f"{have} ≥ {need} → true", have, need)
        rank = {"not_met": 0, "check": 1, "met": 2}
        if worst is None or rank[c.status] < rank[worst.status]:
            worst = c
    return worst or Criterion("language", CRITERION_NAMES["language"], "met", "No language requirement",
                              "The posting sets no language requirement.", "none → allowed")


def evaluate(profile: dict, answers: dict, role: dict, *, permission: Criterion) -> list[Criterion]:
    """Check one role against the eight fixed criteria.

    Args:
        profile: The candidate profile (from the CV and confirmed by the user).
        answers: The user's answers to our questions, e.g. {"uk_work": "yes"}.
        role: The role, with the `requirements` read from its posting.
        permission: The permission outcome, decided by the canonical
            HC_WORK_AUTH rule (core/eligibility.permission). There is no
            fallback: this module never decides work authorisation.

    Returns:
        Eight Criterion outcomes, in CRITERIA order.
    """
    req = role["requirements"]
    degree = profile["degree"]
    out: list[Criterion] = []

    out.append(Criterion("location", CRITERION_NAMES["location"], "met",
                         f"{role['city']} · {role['mode'].lower()}",
                         "The role’s location is stated in the posting.", "location_stated → met"))
    out.append(permission)

    if req.get("student") and not profile.get("enrolled"):
        out.append(Criterion("student", CRITERION_NAMES["student"], "not_met", "Not enrolled",
                             "The role is for enrolled students.", "enrolled = false → not allowed"))
    else:
        out.append(Criterion("student", CRITERION_NAMES["student"], "met",
                             f"Enrolled at {profile.get('school', 'university')}",
                             "The role is for enrolled students; you are enrolled.", "enrolled = true → allowed"))

    lo, hi = req["graduation"]
    grad = degree["graduation"]
    ok = lo <= grad <= hi
    out.append(Criterion("graduation", CRITERION_NAMES["graduation"], "met" if ok else "not_met",
                         f"{_month(grad)} · {'in window' if ok else 'outside window'}",
                         f"Graduation window {_month(lo)} – {_month(hi)}; you graduate {_month(grad)}.",
                         f"{lo} ≤ {grad} ≤ {hi} → {'true' if ok else 'false'}"))

    need = req["degree_level"]
    ok = _DEGREES.index(degree["level"]) >= _DEGREES.index(need)
    out.append(Criterion("degree", CRITERION_NAMES["degree"], "met" if ok else "not_met",
                         f"{_DEGREE_SHORT[degree['level']]} · {_DEGREE_LABEL[need]} required",
                         f"{_DEGREE_LABEL[need]} required; you hold {degree['label']}.",
                         f"{degree['level']} ≥ {need} → {'true' if ok else 'false'}"))

    fields = req.get("fields", [])
    field = degree["field"]
    if field in fields:
        out.append(Criterion("field", CRITERION_NAMES["field"], "met", f"{field} · accepted",
                             f"The posting accepts {', '.join(fields)}.", f"{field} ∈ accepted → true"))
    elif req.get("related_ok"):
        out.append(Criterion("field", CRITERION_NAMES["field"], "check", f"{field} ≈ related?",
                             "The posting accepts “a related field”. Ask the recruiter whether "
                             f"{field} counts.", f"{field} ∈ related → unknown", field,
                             ", ".join(fields)))
    else:
        out.append(Criterion("field", CRITERION_NAMES["field"], "not_met", f"{field} · not accepted",
                             f"The posting accepts only {', '.join(fields)}.", f"{field} ∈ accepted → false"))

    out.append(_language(profile, role, answers))

    n, m = profile.get("internships", 0), req.get("experience_min", 0)
    ok = n >= m
    out.append(Criterion("experience", CRITERION_NAMES["experience"], "met" if ok else "not_met",
                         f"{n} internships · {m} required",
                         f"{m} internship required; you have {n}.", f"{n} ≥ {m} → {'true' if ok else 'false'}"))
    return out


def verdict(criteria: list[Criterion]) -> str:
    """Collapse eight outcomes into the role's standing.

    Returns:
        "excluded" if any criterion is not met -- a high match can never
        override a conflict; "verify" if any needs a fact; else "eligible".
    """
    statuses = {c.status for c in criteria}
    if "not_met" in statuses:
        return "excluded"
    if "check" in statuses:
        return "verify"
    return "eligible"
