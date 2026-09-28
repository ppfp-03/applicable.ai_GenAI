"""Onboarding Updated ranking: a role's job description, line by line against the CV.

Each requirement line of a role's `description` (data/demo.json) has a `kind`:

- a rule criterion id (core/rules.CRITERIA): its outcome is the one the rules
  already decided for this role, never decided again here. A language whose
  level no rule checks (store.RoleView.limitations) is to verify instead;
- `skill`: named among the CV's skills or experience, compared without case;
- `preferred_field`: a field the posting prefers, compared with the degrees
  in the profile;
- `duration`: a length of stay the posting prefers; the profile does not say
  how long the candidate can stay, so it is always to verify.

A line the CV does not cover carries one piece of advice, from the fixed
ADVICE table: no model writes or rewrites it. A role with no `description`
falls back to its rule outcomes and the gaps its fixture names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from core import rules

MET, GAP, VERIFY = "met", "gap", "verify"

#: A rule outcome, as a job description line shows it.
_STATUS = {"met": MET, "check": VERIFY, "not_met": GAP}

#: What to do about a line the CV does not cover, by kind. `{value}`, `{have}`
#: and `{need}` are filled from the line and its rule outcome.
ADVICE = {
    "skill": "Get hands-on with {value} through a short course or a small project, then add it to your CV.",
    "preferred_field": "Preferred, not required. List the {value} courses, projects or tools you have used.",
    "duration": "Say in your application how many months you can stay.",
    "language": "Your profile shows {have}; the role asks for {need}. A certificate at that level proves it: add it to your profile.",
    "language_unchecked": "The fixed rules do not check this level. If you hold it, add the certificate to your profile; if not, say in your application how you are working towards it.",
    "field": "List the courses, thesis or projects that connect your studies to this field.",
    "degree": "Check that your programme gives the degree level the role asks for before applying.",
    "graduation": "Your graduation date is outside the window. Ask the recruiter whether they accept other dates.",
    "experience": "Add internships, part-time work and substantial projects to your CV, with what each achieved.",
    "student": "The role is for enrolled students: keep proof of enrolment ready.",
    "permission": "Declare where you can work without sponsorship in your profile, and check the visa route for this country.",
    "location": "Check that you can be in the office as often as the role asks.",
    "other": "Show related projects or coursework in your CV and cover letter.",
}


@dataclass(frozen=True)
class Line:
    """One requirement of a job description, checked against the candidate.

    Attributes:
        text: The requirement as the posting states it.
        kind: A rule criterion id, "skill", "preferred_field", "duration" or "other".
        status: "met", "gap" (the CV does not cover it) or "verify" (one more fact needed).
        advice: How to cover it; empty when met.
    """

    text: str
    kind: str
    status: str
    advice: str = ""


def named(value: str, cv: Iterable[str]) -> bool:
    """Whether the CV names `value`: the same word, or one inside the other."""
    k = value.lower()
    return any(k == s or (len(s) > 2 and s in k) or (len(k) > 2 and k in s) for s in (c.lower() for c in cv))


def _advice(kind: str, value: object = "", crit: Optional[rules.Criterion] = None) -> str:
    text = ADVICE.get(kind, ADVICE["other"])
    return text.format(value=value, have=(crit.have if crit else "") or "not stated", need=crit.need if crit else "")


def _line(req: dict, criteria: dict[str, rules.Criterion], cv: Optional[list[str]], fields: list[str],
          unchecked: Iterable[str]) -> Line:
    kind, text, value = req["kind"], req["text"], req.get("value", "")
    if kind == "language" and any(lang in text for lang in unchecked):
        return Line(text, kind, VERIFY, ADVICE["language_unchecked"])
    if kind in criteria:
        crit = criteria[kind]
        status = _STATUS[crit.status]
        return Line(text, kind, status, "" if status == MET else _advice(kind, value, crit))
    if kind == "skill":
        status = VERIFY if cv is None else MET if named(str(value), cv) else GAP
    elif kind == "preferred_field":
        status = MET if value in fields else GAP
    elif kind == "duration":
        status = VERIFY
    else:
        raise ValueError(f"unknown requirement kind: {kind!r}")
    return Line(text, kind, status, "" if status == MET else _advice(kind, value))


def lines(role: dict, criteria: list[rules.Criterion], profile: dict, cv: Optional[list[str]],
          unchecked: Iterable[str] = ()) -> list[Line]:
    """The role's requirements, each checked against the candidate.

    Args:
        role: The role as data/demo.json holds it.
        criteria: The rules' outcomes for this role (store.RoleView.criteria).
        profile: The candidate profile (data/demo.json `profile`).
        cv: The skills and experience read from the CV, or None before one is.
        unchecked: Languages the role asks for at a level no rule checks.
    """
    unchecked = list(unchecked)
    by_id = {c.id: c for c in criteria}
    desc = role.get("description")
    if desc:
        fields = [profile["degree"]["field"], *(d["field"] for d in profile.get("previous_degrees", []))]
        return [_line(r, by_id, cv, fields, unchecked) for r in desc["requirements"]]
    # No written description: what the rules checked, then the gaps the fixture names.
    out = [
        Line(c.detail, c.id, _STATUS[c.status], "" if c.status == "met" else _advice(c.id, crit=c))
        for c in criteria if c.id != "location"
    ]
    return out + [Line(g, "other", GAP, ADVICE["other"]) for g in role.get("gaps", [])]
