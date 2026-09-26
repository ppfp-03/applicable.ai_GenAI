"""Presentation adapter: the canonical engine's result, as the screens show it.

The screens list eight criteria per role, in a fixed order, as met / check /
not met tiles, and a standing (eligible / verify / excluded). This module
renders an EligibilityResult into exactly that and decides nothing:

- every tile's status is its rule's status, unchanged in meaning: MET is
  met, CONFLICT is not met, UNKNOWN is check, and NOT_APPLICABLE (the posting
  sets no such hard requirement) is shown as met with a "no requirement"
  line;
- a criterion with several outcomes (one per required language) shows the
  most severe one;
- the standing is the engine's aggregate status;
- requirements outside canonical eligibility (e.g. Mandarin HSK) are listed
  as limitations, never as criteria, so they cannot change a standing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core import eligibility
from core.rules import CRITERIA, CRITERION_NAMES, Criterion
from oi.contracts import RequirementClassification
from oi.intelligence.eligibility import EligibilityResult, EligibilityStatus, RuleOutcome, RuleStatus

#: Canonical constraint -> the screens' criterion id.
CRITERION_OF = {
    "HC_LOCATION": "location",
    eligibility.WORK_AUTH: "permission",
    eligibility.STUDENT: "student",
    eligibility.GRAD_WINDOW: "graduation",
    eligibility.DEGREE: "degree",
    eligibility.FIELD: "field",
    eligibility.LANGUAGE: "language",
    eligibility.EXPERIENCE: "experience",
}

#: Engine status -> tile status the screens already understand.
TILE_STATUS = {
    RuleStatus.MET: "met",
    RuleStatus.CONFLICT: "not_met",
    RuleStatus.UNKNOWN: "check",
    RuleStatus.NOT_APPLICABLE: "met",
}

#: Engine aggregate -> the role's standing.
STANDING = {
    EligibilityStatus.ELIGIBLE: "eligible",
    EligibilityStatus.UNCERTAIN: "verify",
    EligibilityStatus.INELIGIBLE: "excluded",
}

_SEVERITY = {RuleStatus.CONFLICT: 0, RuleStatus.UNKNOWN: 1, RuleStatus.MET: 2, RuleStatus.NOT_APPLICABLE: 3}

_PERMISSION_VALUE = {
    RuleStatus.MET: "Right to work · confirmed",
    RuleStatus.CONFLICT: "Right to work · conflict",
    RuleStatus.UNKNOWN: "Right to work · needs verification",
    RuleStatus.NOT_APPLICABLE: "Right to work · not required",
}
_NOT_REQUIRED = {
    "location": "No location restriction",
    "student": "No student requirement",
    "graduation": "No graduation window",
    "degree": "No degree requirement",
    "field": "No field requirement",
    "language": "No language rule applies",
    "experience": "No experience requirement",
}
_DEGREE_LABEL = {"bachelor": "Bachelor’s", "master": "Master’s", "phd": "PhD"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_CODE_LANGUAGE = {code: name for name, code in eligibility.LANGUAGES.items()}


@dataclass(frozen=True)
class Limitation:
    """A requirement the fixed rules do not check. It never changes a standing.

    Attributes:
        name: Display name ("Mandarin level").
        text: One sentence saying what was asked and why it is not checked.
    """

    name: str
    text: str


def _month(ym: str) -> str:
    """'2027-07' -> 'Jul 2027'."""
    year, month = ym.split("-")
    return f"{_MONTHS[int(month) - 1]} {year}"


def standing(result: EligibilityResult) -> str:
    """The role's standing: the engine's aggregate status, renamed."""
    return STANDING[result.status]


def _languages(profile: Mapping[str, Any], answers: Mapping[str, Any]) -> dict[str, str]:
    return {**profile.get("languages", {}), **(answers.get("languages") or {})}


def _tile(cid: str, o: RuleOutcome, role: Mapping[str, Any], profile: Mapping[str, Any],
          answers: Mapping[str, Any]) -> Criterion:
    """One outcome as a tile: status, the short line, and have/need for comparisons."""
    s, req = o.status, role["requirements"]
    status, name = TILE_STATUS[s], CRITERION_NAMES[cid]
    rule = f"{o.rule_id} v{o.rule_version} → {s.value}"
    degree = profile.get("degree") or {}
    have = need = ""

    if cid == "permission":
        rule = f"{o.rule_id} v{o.rule_version} · {role['country']} → {s.value}"
        value = _PERMISSION_VALUE[s]
    elif s is RuleStatus.NOT_APPLICABLE:
        value = _NOT_REQUIRED[cid]
        if cid == "location":
            value = f"{role['city']} · {role['mode'].lower()}"
    elif cid == "student":
        value = {RuleStatus.MET: f"Enrolled at {profile.get('school', 'university')}",
                 RuleStatus.CONFLICT: "Status not accepted",
                 RuleStatus.UNKNOWN: "Student status · needs verification"}[s]
    elif cid == "graduation":
        grad = degree.get("graduation")
        value = {RuleStatus.MET: f"{_month(grad)} · in window" if grad else "In window",
                 RuleStatus.CONFLICT: f"{_month(grad)} · outside window" if grad else "Outside window",
                 RuleStatus.UNKNOWN: "Graduation · needs verification"}[s]
    elif cid == "degree":
        short = (degree.get("label") or "Degree").split()[0]
        progress = " in progress" if degree.get("status") == "in_progress" else ""
        value = f"{short}{progress} · {_DEGREE_LABEL[req['degree_level']]} required"
    elif cid == "field":
        have, need = degree.get("field", ""), ", ".join(req.get("fields", []))
        value = {RuleStatus.MET: f"{have} · accepted",
                 RuleStatus.CONFLICT: f"{have} · not accepted",
                 RuleStatus.UNKNOWN: f"{have} ≈ related?"}[s]
    elif cid == "language":
        lang = _CODE_LANGUAGE[(o.requirement_id or "").removeprefix("req-language-")]
        have, need = _languages(profile, answers).get(lang, ""), req["languages"][lang]
        name = f"{lang} level"
        value = {RuleStatus.MET: f"{lang} {have}",
                 RuleStatus.CONFLICT: f"{have} · {need} required",
                 RuleStatus.UNKNOWN: f"{lang} · not stated"}[s]
    elif cid == "experience":
        n = req.get("experience_min", 0)
        months = profile.get("experience_months")
        required = f"{n} internship{'s' if n != 1 else ''} required"
        value = f"{months} months · {required}" if s is not RuleStatus.UNKNOWN else f"Experience · {required}"
    else:  # location with an explicit country perimeter
        value = f"{role['city']} · {role['mode'].lower()}"

    return Criterion(cid, name, status, value, o.reason, rule, have, need)


def criteria(result: EligibilityResult, role: Mapping[str, Any], profile: Mapping[str, Any],
             answers: Mapping[str, Any]) -> list[Criterion]:
    """The eight tiles for one role, in CRITERIA order.

    Raises:
        ValueError: If the result has no outcome for a criterion.
    """
    worst: dict[str, RuleOutcome] = {}
    for o in result.outcomes:
        cid = CRITERION_OF[o.rule_id]
        if cid not in worst or _SEVERITY[o.status] < _SEVERITY[worst[cid].status]:
            worst[cid] = o
    missing = [cid for cid in CRITERIA if cid not in worst]
    if missing:
        raise ValueError(f"no engine outcome for {missing}")
    return [_tile(cid, worst[cid], role, profile, answers) for cid in CRITERIA]


def limitations(role: Mapping[str, Any], profile: Mapping[str, Any],
                answers: Mapping[str, Any]) -> list[Limitation]:
    """The role's requirements that no supported rule checks."""
    out = []
    langs = _languages(profile, answers)
    for r in eligibility.job(role).facts.requirements:
        if r.classification is RequirementClassification.HARD_CONSTRAINT:
            continue
        lang = r.text.split()[0]
        have = langs.get(lang)
        yours = f"your profile shows {have}" if have else "your profile states no level"
        out.append(Limitation(
            f"{lang} level",
            f"The posting asks for {r.text}; {yours}. The fixed rules do not check this "
            "level, so it does not change eligibility.",
        ))
    return out
