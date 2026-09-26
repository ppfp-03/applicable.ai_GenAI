"""Work authorisation for the demo screens, decided by the canonical engine.

The screens used to ask core/rules.py whether a role's country lets the user
work there. That is now asked of `oi.intelligence.eligibility` (HC_WORK_AUTH),
the same engine the pipeline uses. This module only translates:

- the user's structured answers become `declarations.work_authorizations` on
  a CandidateProfile. Citizenship is not copied over: it is not a declaration;
- a demo role becomes a JobRecord in its country with one mandatory
  HC_WORK_AUTH requirement, and its `sponsors_visa` flag becomes the
  employer-sponsorship parameter;
- the engine's HC_WORK_AUTH outcome becomes the "permission" tile.

Nothing here decides anything. Every status comes from the engine unchanged.

The other seven criteria are still read from core/rules.py.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping, Optional

from core.rules import CRITERION_NAMES, Criterion
from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility import (
    JobParameterSet,
    RuleCatalogue,
    RuleOutcome,
    RuleStatus,
    assess_eligibility,
    load_rule_catalogue,
)

WORK_AUTH = "HC_WORK_AUTH"

_CANDIDATE_ID = "demo-candidate"
_QUESTIONNAIRE = "demo-answers"
_REQUIREMENT_ID = "req-work-auth"
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

#: The demo's `sponsors_visa` flag, as the parameter layer names it.
_SPONSORSHIP = {True: "offered", False: "not_offered"}

#: Engine status -> tile status the screens already understand.
_TILE_STATUS = {
    RuleStatus.MET: "met",
    RuleStatus.CONFLICT: "not_met",
    RuleStatus.UNKNOWN: "check",
    RuleStatus.NOT_APPLICABLE: "met",
}
_TILE_VALUE = {
    RuleStatus.MET: "Right to work · confirmed",
    RuleStatus.CONFLICT: "Right to work · conflict",
    RuleStatus.UNKNOWN: "Right to work · needs verification",
    RuleStatus.NOT_APPLICABLE: "Right to work · not required",
}


@lru_cache(maxsize=1)
def catalogue() -> RuleCatalogue:
    return load_rule_catalogue()


def declarations(answers: Mapping[str, Any]) -> tuple[tuple[str, Optional[bool], Optional[bool]], ...]:
    """The work-authorisation declarations the user's answers make.

    Returns:
        (country_code, authorized_to_work, requires_sponsorship) per country.
    """
    uk = _UK_DECLARATIONS.get(answers.get("uk_work"))
    return (("GB", *uk),) if uk else ()


@lru_cache(maxsize=16)
def candidate(decls: tuple[tuple[str, Optional[bool], Optional[bool]], ...]) -> CandidateProfile:
    """A CandidateProfile carrying only the declared work authorisations."""
    evidence, rows = [], []
    for country, authorized, sponsorship in decls:
        evidence_id = f"ev-work-auth-{country}"
        evidence.append({
            "evidence_id": evidence_id,
            "document_id": _QUESTIONNAIRE,
            "quote": f"Work authorization · {country}",
            "field_path": f"declarations.work_authorizations.{country}",
        })
        rows.append({
            "country_code": country,
            "authorized_to_work": authorized,
            "requires_sponsorship": sponsorship,
            "evidence_ids": [evidence_id],
        })
    return CandidateProfile.model_validate({
        "schema_version": "0.2.0-draft",
        "candidate_id": _CANDIDATE_ID,
        "cv_document_id": "demo-cv",
        "skills": [],
        "education": [],
        "experience": [],
        "preferences": {"preferred_country_codes": [], "preferred_role_families": [],
                        "preferred_industries": []},
        "declarations": {"additional_citizenships": [], "work_authorizations": rows},
        "eligibility_answers": {},
        "provenance": {
            "questionnaire_document_ids": [_QUESTIONNAIRE],
            "clarification_document_ids": [],
            "documents": {
                "demo-cv": {"document_id": "demo-cv", "kind": "cv", "text": "Demo CV.",
                            "content_hash": "demo-cv", "source_ref": "data/demo.json"},
                _QUESTIONNAIRE: {"document_id": _QUESTIONNAIRE, "kind": "questionnaire",
                                 "text": "\n".join(["Answers given in the app.",
                                                     *(e["quote"] for e in evidence)]),
                                 "content_hash": "demo-answers",
                                 "source_ref": "session"},
            },
            "evidence": evidence,
            "extraction": _RECEIPT,
        },
    })


def _job_id(role_id: str) -> str:
    return f"demo:{role_id}"


@lru_cache(maxsize=None)
def _job(role_id: str, country: str, city: str, company: str, title: str) -> JobRecord:
    """The role as a JobRecord: one location, one mandatory HC_WORK_AUTH requirement."""
    doc = f"job-{role_id}"
    return JobRecord.model_validate({
        "schema_version": "0.2.0-draft",
        "job_id": _job_id(role_id),
        "source": "demo",
        "source_job_id": role_id,
        "company": company,
        "title": title,
        "url": f"https://example.invalid/{role_id}",
        "description": {"document_id": doc, "kind": "job",
                        "text": f"{title} at {company}.\n{city}, {country}\nRight to work in {country}",
                        "content_hash": doc, "source_ref": "data/demo.json"},
        "source_documents": [],
        "locations": [{"country_code": country, "city": city, "evidence_ids": ["ev-location"]}],
        "first_seen_at": _AT,
        "last_seen_at": _AT,
        "active_state": "active",
        "discovery_kind": "synthetic_scenario",
        "facts": {
            "skills": [], "experience": [], "education": [],
            "requirements": [{
                "requirement_id": _REQUIREMENT_ID,
                "text": f"Right to work in {country}",
                "classification": "hard_constraint",
                "modality": "mandatory",
                "constraint_id": WORK_AUTH,
                "evidence_ids": ["ev-work-auth"],
            }],
        },
        "evidence": [
            {"evidence_id": "ev-location", "document_id": doc, "quote": f"{city}, {country}",
             "field_path": "locations"},
            {"evidence_id": "ev-work-auth", "document_id": doc, "quote": f"Right to work in {country}",
             "field_path": "facts.requirements"},
        ],
    })


@lru_cache(maxsize=None)
def _parameters(role_id: str, sponsors_visa: Optional[bool]) -> JobParameterSet:
    return JobParameterSet.model_validate({
        "layer_version": "0.1-temporary",
        "entries": [{
            "job_id": _job_id(role_id),
            "requirement_id": _REQUIREMENT_ID,
            "constraint_id": WORK_AUTH,
            "parameters": {"kind": "work_auth",
                           "employer_sponsorship": _SPONSORSHIP.get(sponsors_visa, "not_stated")},
            "evidence_ids": ["ev-work-auth"],
            "origin": "curated",
        }],
    })


@lru_cache(maxsize=256)
def _work_auth(role_id: str, country: str, city: str, company: str, title: str,
               sponsors_visa: Optional[bool], decls: tuple) -> RuleOutcome:
    result = assess_eligibility(
        candidate(decls),
        _job(role_id, country, city, company, title),
        catalogue(),
        job_parameters=_parameters(role_id, sponsors_visa),
    )
    return next(o for o in result.outcomes if o.rule_id == WORK_AUTH)


def work_auth(role: Mapping[str, Any], answers: Mapping[str, Any]) -> RuleOutcome:
    """The engine's HC_WORK_AUTH outcome for one demo role under `answers`."""
    return _work_auth(role["id"], role["country"], role["city"], role["company"], role["title"],
                      role.get("sponsors_visa"), declarations(answers))


def permission(role: Mapping[str, Any], answers: Mapping[str, Any]) -> Criterion:
    """The "permission" tile, rendered from the engine's outcome."""
    outcome = work_auth(role, answers)
    rule = f"{outcome.rule_id} v{outcome.rule_version} · {role['country']} → {outcome.status.value}"
    return Criterion("permission", CRITERION_NAMES["permission"], _TILE_STATUS[outcome.status],
                     _TILE_VALUE[outcome.status], outcome.reason, rule)
