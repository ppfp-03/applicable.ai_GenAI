"""Synthetic CandidateProfile / JobRecord / JobParameterSet builders.

All people, companies and documents here are fictional. Every builder returns
a fully validated shared-contract object, so the engine is tested against the
real frozen shapes rather than hand-rolled dicts.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility.parameters import JobParameterSet

CANDIDATE_ID = "synthetic-candidate"
JOB_ID = "synthetic:job-1"

_RECEIPT = {
    "mode": "fixture",
    "provider": "synthetic",
    "model_id": "synthetic",
    "prompt_version": "1",
    "schema_version": "0.2.0-draft",
    "input_hash": "hash",
    "produced_at": "2026-09-20T10:00:00+00:00",
}

#: (country_code, authorized_to_work, requires_sponsorship)
WorkAuth = tuple[str, "bool | None", "bool | None"]


def answer_evidence_id(constraint_id: str, answer_key: str) -> str:
    return f"ev-q-{constraint_id}-{answer_key}"


def work_auth_evidence_id(country_code: str) -> str:
    return f"ev-q-work-auth-{country_code}"


def _answer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, date):
        return "date"
    if isinstance(value, list):
        return "multi_choice"
    return "single_choice"


def candidate(
    *,
    answers: dict[tuple[str, str], Any] | None = None,
    unknown_answers: Iterable[tuple[str, str, str]] = (),
    work_auth: Iterable[WorkAuth] = (),
    allowed_countries: list[str] | None = None,
    citizenships: list[str] | None = None,
) -> CandidateProfile:
    """A candidate with known answers, unknown answers and declarations.

    Args:
        answers: {(constraint_id, answer_key): value}; the answer type is
            inferred from the value (date, bool, int, list or choice string).
        unknown_answers: (constraint_id, answer_key, answer_type) answered
            with state "unknown".
        work_auth: (country, authorized_to_work, requires_sponsorship).
        allowed_countries: the declared country perimeter, or None.
        citizenships: declared additional citizenships.
    """

    evidence: list[dict[str, Any]] = []
    eligibility_answers: dict[str, list[dict[str, Any]]] = {}

    for (constraint_id, answer_key), value in (answers or {}).items():
        evidence_id = answer_evidence_id(constraint_id, answer_key)
        evidence.append(
            {
                "evidence_id": evidence_id,
                "document_id": "q-1",
                "quote": f"{answer_key}: {value}",
                "field_path": f"eligibility_answers.{constraint_id}.{answer_key}",
            }
        )
        eligibility_answers.setdefault(constraint_id, []).append(
            {
                "constraint_id": constraint_id,
                "answer_key": answer_key,
                "state": "known",
                "answer_type": _answer_type(value),
                "value": value.isoformat() if isinstance(value, date) else value,
                "evidence_ids": [evidence_id],
                "source_document_id": "q-1",
            }
        )

    for constraint_id, answer_key, answer_type in unknown_answers:
        eligibility_answers.setdefault(constraint_id, []).append(
            {
                "constraint_id": constraint_id,
                "answer_key": answer_key,
                "state": "unknown",
                "answer_type": answer_type,
                "value": None,
                "evidence_ids": [],
                "source_document_id": "q-1",
            }
        )

    declarations = []
    for country_code, authorized, sponsorship in work_auth:
        evidence_id = work_auth_evidence_id(country_code)
        evidence.append(
            {
                "evidence_id": evidence_id,
                "document_id": "q-1",
                "quote": f"Work authorization for {country_code}",
                "field_path": f"declarations.work_authorizations.{country_code}",
            }
        )
        declarations.append(
            {
                "country_code": country_code,
                "authorized_to_work": authorized,
                "requires_sponsorship": sponsorship,
                "evidence_ids": [evidence_id],
            }
        )

    preferred = list(allowed_countries or [])
    return CandidateProfile.model_validate(
        {
            "schema_version": "0.2.0-draft",
            "candidate_id": CANDIDATE_ID,
            "cv_document_id": "cv-1",
            "skills": [],
            "education": [],
            "experience": [],
            "preferences": {
                "allowed_country_codes": allowed_countries,
                "preferred_country_codes": preferred,
                "preferred_role_families": [],
                "preferred_industries": [],
            },
            "declarations": {
                "additional_citizenships": citizenships or [],
                "work_authorizations": declarations,
            },
            "eligibility_answers": eligibility_answers,
            "provenance": {
                "questionnaire_document_ids": ["q-1"],
                "clarification_document_ids": [],
                "documents": {
                    "cv-1": {
                        "document_id": "cv-1",
                        "kind": "cv",
                        "text": "Synthetic CV.",
                        "content_hash": "h-cv",
                        "source_ref": "synthetic",
                    },
                    "q-1": {
                        "document_id": "q-1",
                        "kind": "questionnaire",
                        "text": "Synthetic questionnaire.",
                        "content_hash": "h-q",
                        "source_ref": "synthetic",
                    },
                },
                "evidence": evidence,
                "extraction": _RECEIPT,
            },
        }
    )


#: (requirement_id, constraint_id, modality) or with a 4th item: classification.
Req = tuple


def requirement_evidence_id(requirement_id: str) -> str:
    return f"ev-job-{requirement_id}"


def job(
    *,
    locations: Iterable[tuple["str | None", "str | None"]] = (("NL", "Amsterdam"),),
    requirements: Iterable[Req] = (),
    job_id: str = JOB_ID,
    extra_evidence: Iterable[str] = (),
) -> JobRecord:
    """A job with the given locations and requirements.

    Each requirement is (requirement_id, constraint_id, modality) for a hard
    constraint, or (requirement_id, None, modality, classification) for a
    fit/informational one. Every requirement and location gets evidence.
    """

    source, source_job_id = job_id.split(":", 1)
    evidence: list[dict[str, Any]] = []
    location_rows = []
    for index, (country_code, city) in enumerate(locations):
        evidence_id = f"ev-job-location-{index}"
        evidence.append(
            {
                "evidence_id": evidence_id,
                "document_id": "job-doc",
                "quote": f"Location: {city or '?'}, {country_code or '?'}",
                "field_path": "locations",
            }
        )
        location_rows.append(
            {"country_code": country_code, "city": city, "evidence_ids": [evidence_id]}
        )

    requirement_rows = []
    for row in requirements:
        requirement_id, constraint_id, modality = row[:3]
        classification = row[3] if len(row) > 3 else "hard_constraint"
        evidence_id = requirement_evidence_id(requirement_id)
        evidence.append(
            {
                "evidence_id": evidence_id,
                "document_id": "job-doc",
                "quote": f"Requirement {requirement_id}",
                "field_path": "facts.requirements",
            }
        )
        requirement_rows.append(
            {
                "requirement_id": requirement_id,
                "text": f"Requirement {requirement_id}",
                "classification": classification,
                "modality": modality,
                "constraint_id": constraint_id,
                "evidence_ids": [evidence_id],
            }
        )

    for evidence_id in extra_evidence:
        evidence.append(
            {
                "evidence_id": evidence_id,
                "document_id": "job-doc",
                "quote": f"Quote {evidence_id}",
                "field_path": "facts.requirements",
            }
        )

    return JobRecord.model_validate(
        {
            "schema_version": "0.2.0-draft",
            "job_id": job_id,
            "source": source,
            "source_job_id": source_job_id,
            "company": "Nestella",
            "title": "Finance Intern",
            "url": "https://example.invalid/job",
            "description": {
                "document_id": "job-doc",
                "kind": "job",
                "text": "Synthetic posting.",
                "content_hash": "h-job",
                "source_ref": "synthetic",
            },
            "source_documents": [],
            "locations": location_rows,
            "first_seen_at": "2026-09-20T10:00:00+00:00",
            "last_seen_at": "2026-09-20T10:00:00+00:00",
            "active_state": "active",
            "discovery_kind": "synthetic_scenario",
            "facts": {
                "skills": [],
                "experience": [],
                "education": [],
                "requirements": requirement_rows,
            },
            "evidence": evidence,
        }
    )


def parameters(
    *entries: tuple[str, str, dict[str, Any]],
    job_id: str = JOB_ID,
    evidence_ids: list[str] | None = None,
) -> JobParameterSet:
    """A parameter layer: entries are (requirement_id, constraint_id, params).

    Each entry cites its requirement's evidence unless `evidence_ids` is given.
    """

    return JobParameterSet.model_validate(
        {
            "layer_version": "0.1-temporary",
            "entries": [
                {
                    "job_id": job_id,
                    "requirement_id": requirement_id,
                    "constraint_id": constraint_id,
                    "parameters": params,
                    "evidence_ids": evidence_ids
                    or [requirement_evidence_id(requirement_id)],
                    "origin": "curated",
                }
                for requirement_id, constraint_id, params in entries
            ],
        }
    )
