"""Structural adapter: the demo's state, as the canonical engine's inputs.

Every eligibility decision on the screens is made by `oi.intelligence.
eligibility` (assess_eligibility), the same engine the pipeline uses. This
module only translates, and decides nothing:

- the demo profile and the user's answers become one CandidateProfile: the
  degree, graduation month, field, CEFR languages, student status and months
  of experience become `eligibility_answers`; the user's answers become
  `declarations.work_authorizations`. Citizenship is not copied over: it is
  not a declaration, and it never implies work authorisation;
- a demo role becomes a JobRecord whose demo `requirements` are listed
  explicitly as canonical requirements (classification + modality +
  constraint), plus the typed JobParameterSet the rules compare against;
- the engine's EligibilityResult goes, unchanged, to the presentation
  adapter (core/eligibility_view.py).

The mapping, requirement by requirement:

| demo requirement      | canonical requirement                              |
|-----------------------|----------------------------------------------------|
| (role country)        | HC_WORK_AUTH, hard, mandatory; `sponsorship`       |
| student: true         | HC_STUDENT_STATUS, hard, mandatory; enrolled       |
| graduation [lo, hi]   | HC_GRAD_WINDOW, hard, mandatory; whole months      |
| degree_level          | HC_DEGREE_LEVEL, hard, mandatory; see below        |
| fields (+ related_ok) | HC_FIELD_OF_STUDY, hard, mandatory; FIELDS         |
| languages, CEFR level | HC_LANGUAGE, hard, mandatory; one per language     |
| languages, other      | informational, no constraint: never a hard gate    |
| experience_min        | HC_MIN_EXPERIENCE, hard, mandatory; min_months     |

Demo configuration, not engine semantics:

- `start` on each role is a synthetic scenario month, not a real posting's
  start date. It exists only so a degree in progress is decided the way the
  demo was approved: it counts when it completes before the role starts.
  That comparison becomes the per-job `in_progress_policy` the engine already
  accepts; without a start or a graduation month it stays "undecided".
- `experience_min` counts internships; the engine counts months. One
  internship is read as at least one month (`min_months = experience_min`).
- Mandarin HSK is not a CEFR level, so it stays outside canonical
  eligibility: it is recorded as an informational requirement.
- `sponsorship` is explicit ("offered", "not_offered", "not_stated"); a
  missing value is "not_stated". Only "not_offered" can conflict.
"""

from __future__ import annotations

import calendar
import json
from datetime import date
from functools import lru_cache
from typing import Any, Mapping, Optional

from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility import (
    EligibilityResult,
    JobParameterSet,
    RuleCatalogue,
    RuleOutcome,
    assess_eligibility,
    load_rule_catalogue,
)

WORK_AUTH = "HC_WORK_AUTH"
STUDENT = "HC_STUDENT_STATUS"
GRAD_WINDOW = "HC_GRAD_WINDOW"
DEGREE = "HC_DEGREE_LEVEL"
FIELD = "HC_FIELD_OF_STUDY"
LANGUAGE = "HC_LANGUAGE"
EXPERIENCE = "HC_MIN_EXPERIENCE"

_CANDIDATE_ID = "demo-candidate"
_CV = "demo-cv"
_QUESTIONNAIRE = "demo-answers"
_AT = "2026-09-01T00:00:00+00:00"
_RECEIPT = {
    "mode": "fixture",
    "provider": "demo",
    "model_id": "demo",
    "prompt_version": "demo",
    "schema_version": "0.2.0-draft",
    "input_hash": "demo",
    "produced_at": _AT,
}

#: What each UK answer declares, as (authorized_to_work, requires_sponsorship).
#: The question reads "Can you work in the UK without visa sponsorship?"; "Not
#: sure" and no answer declare nothing.
_UK_DECLARATIONS = {
    "yes": (True, False),
    "no": (False, True),
}

#: The explicit sponsorship values a demo role may carry.
SPONSORSHIP = ("offered", "not_offered", "not_stated")

#: Demo field labels -> the catalogue's field_of_study vocabulary.
FIELDS = {
    "Finance": "finance",
    "Economics": "economics",
    "Business": "business_administration",
    "Statistics": "statistics",
    "Computer Science": "computer_science",
}

#: Demo language names -> the catalogue's language codes (level_<code>).
LANGUAGES = {
    "English": "en",
    "Italian": "it",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Dutch": "nl",
}
_CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")

_DEGREE_LABEL = {"bachelor": "Bachelor's", "master": "Master's", "phd": "PhD"}


@lru_cache(maxsize=1)
def catalogue() -> RuleCatalogue:
    return load_rule_catalogue()


def _answer_type(constraint_id: str, key: str) -> str:
    spec = catalogue().get(constraint_id)
    answer_key = spec.answer_key(key) if spec else None
    if answer_key is None:
        raise ValueError(f"{constraint_id} has no answer key {key!r} in the catalogue")
    return answer_key.answer_type.value


def _month_start(ym: str) -> date:
    """'2027-07' -> 2027-07-01."""
    year, month = (int(x) for x in ym.split("-"))
    return date(year, month, 1)


def _month_end(ym: str) -> date:
    """'2027-12' -> 2027-12-31."""
    year, month = (int(x) for x in ym.split("-"))
    return date(year, month, calendar.monthrange(year, month)[1])


def canonical_language(name: str, level: Optional[str]) -> Optional[str]:
    """The catalogue code for a language at a CEFR level, else None.

    None means the requirement or fact is outside canonical eligibility (for
    example Mandarin at an HSK level).
    """
    if name not in LANGUAGES or level not in (*_CEFR, "native"):
        return None
    return LANGUAGES[name]


def in_progress_policy(graduation: Optional[str], start: Optional[str]) -> str:
    """Demo configuration: a degree in progress counts if it completes before start.

    Args:
        graduation: The candidate's expected completion month, "YYYY-MM".
        start: The role's synthetic start month, "YYYY-MM".

    Returns:
        "counts", "does_not_count", or "undecided" when either month is missing.
    """
    if not graduation or not start:
        return "undecided"
    return "counts" if graduation < start else "does_not_count"


# ───────────────────────── Candidate side ─────────────────────────


def declarations(answers: Mapping[str, Any]) -> tuple[tuple[str, Optional[bool], Optional[bool]], ...]:
    """The work-authorisation declarations the user's answers make.

    Returns:
        (country_code, authorized_to_work, requires_sponsorship) per country.
    """
    uk = _UK_DECLARATIONS.get(answers.get("uk_work"))
    return (("GB", *uk),) if uk else ()


def _candidate_key(profile: Mapping[str, Any], answers: Mapping[str, Any]) -> str:
    """Only the facts the adapter reads, so equal inputs share one profile."""
    return json.dumps({
        "degree": profile.get("degree"),
        "previous_degrees": profile.get("previous_degrees", []),
        "languages": profile.get("languages", {}),
        "enrolled": profile.get("enrolled"),
        "experience_months": profile.get("experience_months"),
        "certificates": answers.get("languages") or {},
        "declarations": declarations(answers),
    }, sort_keys=True)


def candidate(profile: Mapping[str, Any], answers: Mapping[str, Any]) -> CandidateProfile:
    """The demo profile and the user's answers as one CandidateProfile."""
    return _candidate(_candidate_key(profile, answers))


@lru_cache(maxsize=64)
def _candidate(key: str) -> CandidateProfile:
    facts = json.loads(key)
    evidence: list[dict] = []
    lines: dict[str, list[str]] = {_CV: [], _QUESTIONNAIRE: ["Answers given in the app."]}

    def cite(doc: str, quote: str, path: str) -> str:
        evidence_id = f"ev-{len(evidence) + 1}"
        evidence.append({"evidence_id": evidence_id, "document_id": doc,
                         "quote": quote, "field_path": path})
        lines[doc].append(quote)
        return evidence_id

    answers: dict[str, list[dict]] = {}

    def answer(cid: str, key: str, value: Any, doc: str, quote: str) -> None:
        answers.setdefault(cid, []).append({
            "constraint_id": cid, "answer_key": key, "state": "known",
            "answer_type": _answer_type(cid, key), "value": value,
            "evidence_ids": [cite(doc, quote, f"eligibility_answers.{cid}.{key}")],
            "source_document_id": doc,
        })

    education = []
    for d in [facts["degree"], *facts["previous_degrees"]]:
        if d:
            quote = f"{d['label']} · {d.get('school', '')} · {d.get('status', 'status not stated')}"
            education.append({"value": d["label"], "evidence_ids": [cite(_CV, quote, "education")]})

    degree = facts["degree"] or {}
    if degree.get("level"):
        answer(DEGREE, "degree_level", degree["level"], _CV, f"Degree level: {degree['level']}")
    if degree.get("status"):
        answer(DEGREE, "degree_status", degree["status"], _CV, f"Degree status: {degree['status']}")
    if degree.get("graduation"):
        answer(GRAD_WINDOW, "expected_graduation_date", _month_start(degree["graduation"]), _CV,
               f"Expected graduation: {degree['graduation']}")
    if degree.get("field"):
        answer(FIELD, "field_of_study", FIELDS[degree["field"]], _CV, f"Field of study: {degree['field']}")

    # The demo does not say whether someone not enrolled is a recent graduate,
    # so only enrolment is declared; anything else is asked, not assumed.
    if facts["enrolled"] is True:
        answer(STUDENT, "current_status", "enrolled_student", _CV, "Currently enrolled")

    if isinstance(facts["experience_months"], int):
        answer(EXPERIENCE, "prior_experience_months", facts["experience_months"], _CV,
               f"Total experience: {facts['experience_months']} months")

    # A certificate the user adds replaces the CV's level for that language.
    for name, level in sorted(facts["languages"].items()):
        code = canonical_language(name, level)
        if code and name not in facts["certificates"]:
            answer(LANGUAGE, f"level_{code}", level, _CV, f"{name}: {level}")
    for name, level in sorted(facts["certificates"].items()):
        code = canonical_language(name, level)
        if code:
            answer(LANGUAGE, f"level_{code}", level, _QUESTIONNAIRE, f"Certificate · {name}: {level}")

    rows = []
    for country, authorized, sponsorship in facts["declarations"]:
        quote = f"Work authorization · {country}"
        rows.append({
            "country_code": country,
            "authorized_to_work": authorized,
            "requires_sponsorship": sponsorship,
            "evidence_ids": [cite(_QUESTIONNAIRE, quote, f"declarations.work_authorizations.{country}")],
        })

    return CandidateProfile.model_validate({
        "schema_version": "0.2.0-draft",
        "candidate_id": _CANDIDATE_ID,
        "cv_document_id": _CV,
        "skills": [],
        "education": education,
        "experience": [],
        "preferences": {"preferred_country_codes": [], "preferred_role_families": [],
                        "preferred_industries": []},
        "declarations": {"additional_citizenships": [], "work_authorizations": rows},
        "eligibility_answers": answers,
        "provenance": {
            "questionnaire_document_ids": [_QUESTIONNAIRE],
            "clarification_document_ids": [],
            "documents": {
                _CV: {"document_id": _CV, "kind": "cv",
                      "text": "\n".join(["Synthetic demo profile.", *lines[_CV]]),
                      "content_hash": _CV, "source_ref": "data/demo.json#profile"},
                _QUESTIONNAIRE: {"document_id": _QUESTIONNAIRE, "kind": "questionnaire",
                                 "text": "\n".join(lines[_QUESTIONNAIRE]),
                                 "content_hash": _QUESTIONNAIRE, "source_ref": "session"},
            },
            "evidence": evidence,
            "extraction": _RECEIPT,
        },
    })


# ───────────────────────── Job side ─────────────────────────


def _job_id(role_id: str) -> str:
    return f"demo:{role_id}"


def _role_key(role: Mapping[str, Any]) -> str:
    """Only the role fields the adapter reads."""
    return json.dumps({k: role.get(k) for k in (
        "id", "company", "title", "city", "country", "first_seen_at",
        "requirements", "sponsorship", "start",
    )}, sort_keys=True)


def sponsorship(role: Mapping[str, Any]) -> str:
    """The role's explicit sponsorship value; missing means not stated.

    Raises:
        ValueError: If the value is not one of SPONSORSHIP.
    """
    value = role.get("sponsorship")
    if value is None:
        return "not_stated"
    if not isinstance(value, str) or value not in SPONSORSHIP:
        raise ValueError(f"{role.get('id')}: sponsorship {value!r} is not one of {SPONSORSHIP}")
    return value


def _requirements(role: Mapping[str, Any]) -> list[dict]:
    """The demo requirements, each mapped explicitly onto the canonical model.

    Returns:
        Dicts with requirement_id, text, classification, modality,
        constraint_id and the typed parameters (None for informational ones).
    """
    req = role["requirements"]
    country = role["country"]
    out = [{
        "requirement_id": "req-work-auth", "text": f"Right to work in {country}",
        "classification": "hard_constraint", "modality": "mandatory", "constraint_id": WORK_AUTH,
        "parameters": {"kind": "work_auth", "employer_sponsorship": sponsorship(role)},
    }]
    if req.get("student"):
        out.append({
            "requirement_id": "req-student", "text": "Open to enrolled students",
            "classification": "hard_constraint", "modality": "mandatory", "constraint_id": STUDENT,
            "parameters": {"kind": "student_status", "accepted": ["enrolled_student"]},
        })
    if req.get("graduation"):
        lo, hi = req["graduation"]
        out.append({
            "requirement_id": "req-grad-window", "text": f"Graduating between {lo} and {hi}",
            "classification": "hard_constraint", "modality": "mandatory", "constraint_id": GRAD_WINDOW,
            "parameters": {"kind": "grad_window", "start": _month_start(lo).isoformat(),
                           "end": _month_end(hi).isoformat()},
        })
    if req.get("degree_level"):
        out.append({
            "requirement_id": "req-degree", "text": f"{_DEGREE_LABEL[req['degree_level']]} degree required",
            "classification": "hard_constraint", "modality": "mandatory", "constraint_id": DEGREE,
            # in_progress_policy is added per candidate; see parameters().
            "parameters": {"kind": "degree_level", "min_level": req["degree_level"]},
        })
    if req.get("fields"):
        text = f"Degree in {', '.join(req['fields'])}" + (" or a related field" if req.get("related_ok") else "")
        out.append({
            "requirement_id": "req-field", "text": text,
            "classification": "hard_constraint", "modality": "mandatory", "constraint_id": FIELD,
            "parameters": {"kind": "field_of_study", "accepted": [FIELDS[f] for f in req["fields"]],
                           "related_accepted": bool(req.get("related_ok"))},
        })
    for name, level in req.get("languages", {}).items():
        code = canonical_language(name, level)
        if code and level in _CEFR:
            out.append({
                "requirement_id": f"req-language-{code}", "text": f"{name} {level}",
                "classification": "hard_constraint", "modality": "mandatory", "constraint_id": LANGUAGE,
                "parameters": {"kind": "language", "language": code, "min_level": level},
            })
        else:
            # Stated as required, but no supported rule can check it: it
            # informs, and can never exclude.
            out.append({
                "requirement_id": f"req-language-{name.lower()}", "text": f"{name} {level}",
                "classification": "informational", "modality": "mandatory", "constraint_id": None,
                "parameters": None,
            })
    if req.get("experience_min"):
        n = req["experience_min"]
        out.append({
            "requirement_id": "req-experience", "text": f"At least {n} internship{'s' if n != 1 else ''}",
            "classification": "hard_constraint", "modality": "mandatory", "constraint_id": EXPERIENCE,
            "parameters": {"kind": "min_experience", "min_months": n},
        })
    return out


def job(role: Mapping[str, Any]) -> JobRecord:
    """One demo role as the JobRecord the engine receives."""
    return _job(_role_key(role))


def _evidence_id(requirement_id: str) -> str:
    return "ev-" + requirement_id.removeprefix("req-")


@lru_cache(maxsize=None)
def _job(key: str) -> JobRecord:
    role = json.loads(key)
    doc = f"job-{role['id']}"
    reqs = _requirements(role)
    lines = [f"{role['title']} at {role['company']}.", f"{role['city']}, {role['country']}"]
    evidence = [{"evidence_id": "ev-location", "document_id": doc,
                 "quote": f"{role['city']}, {role['country']}", "field_path": "locations"}]
    for r in reqs:
        lines.append(r["text"])
        evidence.append({"evidence_id": _evidence_id(r["requirement_id"]), "document_id": doc,
                         "quote": r["text"], "field_path": "facts.requirements"})
    if role.get("start"):
        quote = f"Start: {role['start']} (synthetic scenario)"
        lines.append(quote)
        evidence.append({"evidence_id": "ev-start", "document_id": doc, "quote": quote,
                         "field_path": "facts.requirements"})
    first_seen = role.get("first_seen_at") or _AT
    return JobRecord.model_validate({
        "schema_version": "0.2.0-draft",
        "job_id": _job_id(role["id"]),
        "source": "demo",
        "source_job_id": role["id"],
        "company": role["company"],
        "title": role["title"],
        "url": f"https://example.invalid/{role['id']}",
        "description": {"document_id": doc, "kind": "job", "text": "\n".join(lines),
                        "content_hash": doc, "source_ref": "data/demo.json"},
        "source_documents": [],
        "locations": [{"country_code": role["country"], "city": role["city"],
                       "evidence_ids": ["ev-location"]}],
        "first_seen_at": first_seen,
        "last_seen_at": first_seen,
        "active_state": "active",
        "discovery_kind": "synthetic_scenario",
        "facts": {
            "skills": [], "experience": [], "education": [],
            "requirements": [{
                "requirement_id": r["requirement_id"], "text": r["text"],
                "classification": r["classification"], "modality": r["modality"],
                "constraint_id": r["constraint_id"],
                "evidence_ids": [_evidence_id(r["requirement_id"])],
            } for r in reqs],
        },
        "evidence": evidence,
    })


def parameters(role: Mapping[str, Any], profile: Mapping[str, Any]) -> JobParameterSet:
    """The typed parameters for one role's hard requirements.

    The degree requirement's `in_progress_policy` is the demo configuration
    described above: it compares the candidate's completion month with the
    role's synthetic start.
    """
    graduation = (profile.get("degree") or {}).get("graduation")
    return _parameters(_role_key(role), graduation)


@lru_cache(maxsize=None)
def _parameters(key: str, graduation: Optional[str]) -> JobParameterSet:
    role = json.loads(key)
    entries = []
    for r in _requirements(role):
        if r["parameters"] is None:
            continue
        params, evidence = dict(r["parameters"]), [_evidence_id(r["requirement_id"])]
        if r["constraint_id"] == DEGREE:
            params["in_progress_policy"] = in_progress_policy(graduation, role.get("start"))
            if role.get("start"):
                evidence.append("ev-start")
        entries.append({
            "job_id": _job_id(role["id"]),
            "requirement_id": r["requirement_id"],
            "constraint_id": r["constraint_id"],
            "parameters": params,
            "evidence_ids": evidence,
            "origin": "curated",
        })
    return JobParameterSet.model_validate({"layer_version": "0.1-temporary", "entries": entries})


# ───────────────────────── The engine call ─────────────────────────


def assess(role: Mapping[str, Any], profile: Mapping[str, Any], answers: Mapping[str, Any]) -> EligibilityResult:
    """The canonical engine's result for one demo role under `answers`."""
    graduation = (profile.get("degree") or {}).get("graduation")
    return _assess(_role_key(role), _candidate_key(profile, answers), graduation)


@lru_cache(maxsize=1024)
def _assess(role_key: str, candidate_key: str, graduation: Optional[str]) -> EligibilityResult:
    return assess_eligibility(
        _candidate(candidate_key),
        _job(role_key),
        catalogue(),
        job_parameters=_parameters(role_key, graduation),
    )


def work_auth(role: Mapping[str, Any], answers: Mapping[str, Any],
              profile: Optional[Mapping[str, Any]] = None) -> RuleOutcome:
    """The engine's HC_WORK_AUTH outcome for one demo role under `answers`.

    It reads only work-authorisation declarations, so the profile is optional.
    """
    result = assess(role, profile or {}, answers)
    return next(o for o in result.outcomes if o.rule_id == WORK_AUTH)
