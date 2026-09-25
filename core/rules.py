"""Deterministic eligibility rules.

Work authorisation is decided here, by table lookup, and nowhere else. No
model input reaches this module and none of its outputs depend on one: given
the same facts it always returns the same answer, and every answer names the
rule that produced it.

That separation is the point. A language model may explain what these rules
concluded; it may never conclude it. Getting someone's right to work wrong is
not a ranking error, and "the model said so" is not something a user can check.

The Swiss table for EU/EFTA citizens comes from
design-system/10-ux-architecture.md. This is not legal advice, and the rules
carry a version so an outcome can be traced to the text it was read from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from oi.contracts import Evidence, ReqStatus, Source

#: Bump when a rule changes. Shown in "How we know" alongside the outcome.
RULES_VERSION = "2026-09-22"

#: Countries whose citizens move freely within the EU/EFTA area.
_EU_EFTA = frozenset(
    {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
        "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
        "RO", "SK", "SI", "ES", "SE",          # EU
        "IS", "LI", "NO", "CH",                # EFTA
    }
)


@dataclass(frozen=True)
class RuleOutcome:
    """What a rule concluded, and the evidence for it.

    `evidence` is None only when the rule could not fire for want of a fact.
    In that case `status` is "confirm": we ask rather than assume.
    """

    status: ReqStatus
    explanation: str
    evidence: Optional[Evidence] = None


def _rule_evidence(explanation: str, where: str) -> Evidence:
    """Wrap a rule's conclusion as evidence attributed to RULE."""
    return Evidence(
        text=explanation,
        highlight=None,
        source=Source(kind="RULE", where=f"{where} · rules {RULES_VERSION}"),
    )


def swiss_permit_for_eu_citizen(contract_months: Optional[int]) -> RuleOutcome:
    """Apply the Swiss permit table for an EU/EFTA citizen.

    | Contract length      | Outcome                                |
    |----------------------|----------------------------------------|
    | <= 3 months          | No permit needed                       |
    | > 3 and < 12 months  | L permit (EU/EFTA), for the contract   |
    | >= 12 months         | B permit (EU/EFTA), valid 5 years      |

    Args:
        contract_months: Contract length in months, or None if the posting
            does not say.

    Returns:
        A met outcome for any of the three bands. When the length is unknown,
        a "confirm" outcome with no evidence -- we do not pick a band, because
        that would be inventing a fact about someone's legal status.

    Raises:
        ValueError: If `contract_months` is zero or negative.
    """
    if contract_months is None:
        return RuleOutcome(
            status="confirm",
            explanation="Contract length is not stated in this posting.",
        )

    if contract_months <= 0:
        raise ValueError(
            f"Contract length must be a positive number of months, "
            f"got {contract_months}."
        )

    if contract_months <= 3:
        explanation = "No permit needed for ≤ 3 months"
        where = "CH · EU/EFTA · contract ≤ 3 months"
    elif contract_months < 12:
        explanation = "L permit (EU/EFTA) for the contract length"
        where = "CH · EU/EFTA · contract 3–12 months"
    else:
        explanation = "B permit (EU/EFTA), valid 5 years"
        where = "CH · EU/EFTA · contract ≥ 12 months"

    return RuleOutcome(
        status="met",
        explanation=explanation,
        evidence=_rule_evidence(explanation, where),
    )


def work_authorisation(
    citizenship: Optional[str],
    country: str,
    contract_months: Optional[int] = None,
) -> RuleOutcome:
    """Decide whether the candidate may work in `country`.

    Args:
        citizenship: ISO 3166-1 alpha-2 code of the declared citizenship, or
            None if we have not been told.
        country: ISO 3166-1 alpha-2 code of where the role is based.
        contract_months: Contract length, where the posting states it.

    Returns:
        A RuleOutcome. Absent a rule for the pair, the status is "confirm":
        having no rule means we do not know, which is different from knowing
        the answer is no.
    """
    citizenship = (citizenship or "").upper() or None
    country = country.upper()

    if citizenship is None:
        return RuleOutcome(
            status="confirm",
            explanation="Citizenship is not stated in your CV.",
        )

    # Free movement inside the EU/EFTA area, except Switzerland, which runs
    # its own permit regime even for EU citizens.
    if country in _EU_EFTA and country != "CH" and citizenship in _EU_EFTA:
        explanation = "EU/EFTA citizen — free movement applies"
        return RuleOutcome(
            status="met",
            explanation=explanation,
            evidence=_rule_evidence(
                explanation, f"{country} · EU/EFTA citizen"
            ),
        )

    if country == "CH" and citizenship in _EU_EFTA:
        return swiss_permit_for_eu_citizen(contract_months)

    # No rule covers this pair yet. Ask; never assume either way.
    return RuleOutcome(
        status="confirm",
        explanation=(
            f"We have no work-authorisation rule for {citizenship} "
            f"citizens in {country} yet."
        ),
    )


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


def _permission(profile: dict, answers: dict, role: dict) -> Criterion:
    """Work permission, by the country the role is based in."""
    name = CRITERION_NAMES["permission"]
    country = role["country"]

    if country == "GB":
        uk = answers.get("uk_work")
        if uk == "yes":
            return Criterion("permission", name, "met", "UK · no sponsorship needed",
                             "You told us you can work in the UK without visa sponsorship.",
                             "UK_right_to_work = yes → allowed")
        if uk == "no":
            if role.get("sponsors_visa"):
                return Criterion("permission", name, "check", "Needs sponsorship · employer sponsors",
                                 "You need a visa; this employer sponsors visas, subject to its approval.",
                                 "UK_right_to_work = no + employer_sponsors → to verify")
            return Criterion("permission", name, "not_met", "Needs sponsorship · not offered",
                             "You need a visa and this employer does not sponsor visas.",
                             "UK_right_to_work = no + no_sponsorship → not allowed")
        return Criterion("permission", name, "check", "UK right to work · not stated",
                         "UK right to work is not stated in your CV.",
                         "UK_right_to_work = unknown → ask")

    if country == "CN" and profile.get("citizenship") != "CN":
        visa = profile.get("visa") or {}
        if visa.get("type") != "X1":
            return Criterion("permission", name, "check", "China permit · not stated",
                             "No Chinese work or study permit is stated in your CV.",
                             "CN_permit = unknown → ask")
        if role.get("cn_permit") == "employer":
            return Criterion("permission", name, "met", "X1 visa · employer arranges permit",
                             "The employer arranges the internship permit with your university.",
                             "CN_X1 + employer_arranges → allowed")
        if profile.get("university_letter") or answers.get("cn_letter"):
            return Criterion("permission", name, "met", "X1 visa + university letter",
                             "An X1 study visa with a university letter allows internships.",
                             "CN_X1 + university_letter → allowed")
        return Criterion("permission", name, "check", "X1 visa · letter missing",
                         "An X1 study visa allows internships only with a letter from your university.",
                         "CN_X1 + university_letter → allowed")

    if country == "SG":
        if role.get("sponsors_visa"):
            return Criterion("permission", name, "met", "Employment Pass sponsored",
                             "You need an Employment Pass and this employer sponsors it.",
                             "SG_EP_required + employer_sponsors → allowed")
        return Criterion("permission", name, "not_met", "Employment Pass not sponsored",
                         "You need an Employment Pass and this employer does not sponsor it.",
                         "SG_EP_required + no_sponsorship → not allowed")

    outcome = work_authorisation(profile.get("citizenship"), country, role.get("contract_months"))
    status = {"met": "met", "confirm": "check", "conflict": "not_met"}[outcome.status]
    return Criterion("permission", name, status, outcome.explanation, outcome.explanation,
                     f"{profile.get('citizenship')}_citizen + {country} → table")


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


def evaluate(profile: dict, answers: dict, role: dict) -> list[Criterion]:
    """Check one role against the eight fixed criteria.

    Args:
        profile: The candidate profile (from the CV and confirmed by the user).
        answers: The user's answers to our questions, e.g. {"uk_work": "yes"}.
        role: The role, with the `requirements` read from its posting.

    Returns:
        Eight Criterion outcomes, in CRITERIA order.
    """
    req = role["requirements"]
    degree = profile["degree"]
    out: list[Criterion] = []

    out.append(Criterion("location", CRITERION_NAMES["location"], "met",
                         f"{role['city']} · {role['mode'].lower()}",
                         "The role’s location is stated in the posting.", "location_stated → met"))
    out.append(_permission(profile, answers, role))

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
