"""Tests for shared Applicable.ai data contracts."""

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from oi.contracts import (
    CONTRACT_VERSION,
    SNAPSHOT_CONTRACT_VERSION,
    CandidatePreferences,
    CandidateProfile,
    ClarificationRequest,
    EligibilityAnswer,
    ExtractionReceipt,
    JobRecord,
    JobSnapshot,
    QuarantineSummary,
    RequirementFact,
    SourceDocument,
    SourceManifestEntry,
    UserDeclarations,
    WorkAuthorizationDeclaration,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "v0.2.0-draft"


def test_source_document_accepts_valid_cv() -> None:
    document = SourceDocument(
        document_id="cv-001",
        kind="cv",
        text="Synthetic CV text",
        content_hash="abc123",
        source_ref="uploaded_pdf",
    )

    assert document.kind.value == "cv"


def test_source_document_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        SourceDocument(
            document_id="cv-001",
            kind="curriculum",
            text="Synthetic CV text",
            content_hash="abc123",
            source_ref="uploaded_pdf",
        )


def test_source_document_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SourceDocument(
            document_id="cv-001",
            kind="cv",
            text="Synthetic CV text",
            content_hash="abc123",
            source_ref="uploaded_pdf",
            unexpected_field="not allowed",
        )


def test_source_document_rejects_empty_required_text() -> None:
    with pytest.raises(ValidationError):
        SourceDocument(
            document_id="cv-001",
            kind="cv",
            text="",
            content_hash="abc123",
            source_ref="uploaded_pdf",
        )


def test_extraction_receipt_normalizes_timestamp_to_utc() -> None:
    receipt = ExtractionReceipt(
        mode="live",
        provider="test-provider",
        model_id="test-model",
        prompt_version="1",
        schema_version="0.2.0-draft",
        input_hash="abc123",
        produced_at="2026-09-18T17:30:00+08:00",
        latency_ms=250,
    )

    assert receipt.produced_at.utcoffset() == timezone.utc.utcoffset(receipt.produced_at)
    assert receipt.produced_at.hour == 9


def test_extraction_receipt_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        ExtractionReceipt(
            mode="live",
            provider="test-provider",
            model_id="test-model",
            prompt_version="1",
            schema_version="0.2.0-draft",
            input_hash="abc123",
            produced_at="2026-09-18T17:30:00",
            latency_ms=250,
        )


def test_extraction_receipt_rejects_negative_latency() -> None:
    with pytest.raises(ValidationError):
        ExtractionReceipt(
            mode="live",
            provider="test-provider",
            model_id="test-model",
            prompt_version="1",
            schema_version="0.2.0-draft",
            input_hash="abc123",
            produced_at="2026-09-18T17:30:00+08:00",
            latency_ms=-1,
        )


def make_description_document(**overrides: object) -> dict[str, object]:
    """Minimal valid primary job description payload."""

    payload: dict[str, object] = {
        "document_id": "job-doc-001",
        "kind": "job",
        "text": "Synthetic job description text",
        "content_hash": "hash-job-001",
        "source_ref": "synthetic_fixture",
    }
    payload.update(overrides)
    return payload


def make_job_record(**overrides: object) -> dict[str, object]:
    """Minimal valid JobRecord payload."""

    payload: dict[str, object] = {
        "schema_version": "0.2.0-draft",
        "job_id": "synthetic:job-001",
        "source": "synthetic",
        "source_job_id": "job-001",
        "company": "Synthetic Company",
        "title": "Junior Analyst",
        "url": "https://example.invalid/jobs/job-001",
        "description": make_description_document(),
        "source_documents": [],
        "locations": [],
        "source_published_at": None,
        "source_updated_at": None,
        "deadline_at": None,
        "first_seen_at": "2026-09-18T08:00:00+00:00",
        "last_seen_at": "2026-09-19T08:00:00+00:00",
        "active_state": "active",
        "discovery_kind": "initial_snapshot",
        "facts": None,
        "evidence": [],
        "extraction": None,
    }
    payload.update(overrides)
    return payload


def test_requirement_fact_accepts_hard_constraint_with_constraint_id() -> None:
    fact = RequirementFact(
        requirement_id="req-001",
        text="Must hold an EU work permit",
        classification="hard_constraint",
        modality="mandatory",
        constraint_id="work_authorization_eu",
        evidence_ids=["ev-001"],
    )

    assert fact.classification.value == "hard_constraint"
    assert fact.constraint_id == "work_authorization_eu"


def test_requirement_fact_rejects_hard_constraint_without_constraint_id() -> None:
    with pytest.raises(ValidationError):
        RequirementFact(
            requirement_id="req-001",
            text="Must hold an EU work permit",
            classification="hard_constraint",
            modality="mandatory",
            constraint_id=None,
            evidence_ids=["ev-001"],
        )


def test_requirement_fact_rejects_constraint_id_on_non_hard_requirement() -> None:
    with pytest.raises(ValidationError):
        RequirementFact(
            requirement_id="req-002",
            text="Strong interest in financial markets",
            classification="fit",
            modality="preferred",
            constraint_id="work_authorization_eu",
            evidence_ids=["ev-002"],
        )


def test_job_record_accepts_valid_payload() -> None:
    record = JobRecord(**make_job_record())

    assert record.job_id == "synthetic:job-001"
    assert record.description.kind.value == "job"
    assert record.first_seen_at.utcoffset() == timezone.utc.utcoffset(
        record.first_seen_at
    )


def test_job_record_rejects_incorrectly_namespaced_job_id() -> None:
    with pytest.raises(ValidationError):
        JobRecord(**make_job_record(job_id="job-001"))


def test_job_record_rejects_non_job_primary_description() -> None:
    with pytest.raises(ValidationError):
        JobRecord(
            **make_job_record(
                description=make_description_document(kind="ats_metadata")
            )
        )


def test_job_record_rejects_duplicate_primary_description_document() -> None:
    with pytest.raises(ValidationError):
        JobRecord(
            **make_job_record(
                source_documents=[
                    make_description_document(kind="ats_metadata"),
                ]
            )
        )


def test_job_record_rejects_last_seen_before_first_seen() -> None:
    with pytest.raises(ValidationError):
        JobRecord(
            **make_job_record(
                first_seen_at="2026-09-19T08:00:00+00:00",
                last_seen_at="2026-09-18T08:00:00+00:00",
            )
        )


def test_job_record_rejects_invalid_schema_version() -> None:
    with pytest.raises(ValidationError):
        JobRecord(**make_job_record(schema_version="0.1.0-draft"))


def test_job_record_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        JobRecord(**make_job_record(unexpected_field="not allowed"))


def load_fixture(filename: str) -> dict[str, Any]:
    """Read one shared contract fixture as a plain JSON payload."""

    return json.loads((FIXTURE_ROOT / filename).read_text())


def make_candidate_profile(**overrides: Any) -> dict[str, Any]:
    """Candidate fixture payload, deep-copied so tests can mutate freely."""

    payload = load_fixture("candidate_profile.json")
    payload.update(copy.deepcopy(overrides))
    return payload


def make_clarification_request(**overrides: Any) -> dict[str, Any]:
    """Clarification fixture payload, deep-copied so tests can mutate freely."""

    payload = load_fixture("clarification_request.json")
    payload.update(copy.deepcopy(overrides))
    return payload


def make_preferences(**overrides: Any) -> dict[str, Any]:
    """Minimal valid CandidatePreferences payload."""

    payload: dict[str, Any] = {
        "allowed_country_codes": ["IT", "NL"],
        "preferred_country_codes": ["NL"],
        "preferred_role_families": ["finance_analyst"],
        "preferred_industries": ["banking"],
    }
    payload.update(copy.deepcopy(overrides))
    return payload


def make_eligibility_answer(**overrides: Any) -> dict[str, Any]:
    """Minimal valid EligibilityAnswer payload."""

    payload: dict[str, Any] = {
        "constraint_id": "graduation_window",
        "answer_key": "expected_graduation_date",
        "state": "known",
        "answer_type": "date",
        "value": "2027-07-15",
        "evidence_ids": [],
        "source_document_id": "questionnaire-001",
    }
    payload.update(copy.deepcopy(overrides))
    return payload


# --- fixture round-trips -------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("candidate_profile.json", CandidateProfile),
        ("clarification_request.json", ClarificationRequest),
        ("job_record.json", JobRecord),
    ],
)
def test_shared_fixture_round_trips(filename: str, model: type) -> None:
    payload = load_fixture(filename)

    parsed = model.model_validate(payload)
    reparsed = model.model_validate_json(parsed.model_dump_json())

    assert reparsed == parsed


def test_candidate_fixture_parses_iso_date_answer_as_date() -> None:
    profile = CandidateProfile.model_validate(load_fixture("candidate_profile.json"))

    answer = profile.eligibility_answers["graduation_window"][0]

    assert answer.value == date(2027, 7, 15)


# --- candidate profile shape and references ------------------------------


def test_candidate_profile_rejects_invalid_schema_version() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(**make_candidate_profile(schema_version="0.1.0-draft"))


def test_candidate_profile_rejects_unresolved_evidence_id() -> None:
    payload = make_candidate_profile()
    payload["skills"][0]["evidence_ids"] = ["ev-does-not-exist"]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_unresolved_work_authorization_evidence() -> None:
    payload = make_candidate_profile()
    payload["declarations"]["work_authorizations"][0]["evidence_ids"] = [
        "ev-does-not-exist"
    ]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_evidence_pointing_at_unknown_document() -> None:
    payload = make_candidate_profile()
    payload["provenance"]["evidence"][0]["document_id"] = "document-does-not-exist"

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_duplicate_evidence_id_same_document() -> None:
    payload = make_candidate_profile()
    evidence = payload["provenance"]["evidence"]
    duplicate = copy.deepcopy(evidence[0])
    duplicate["quote"] = "A different quote carrying an already-used evidence_id"
    evidence.append(duplicate)

    with pytest.raises(ValidationError, match="evidence_id must be unique"):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_duplicate_evidence_id_across_documents() -> None:
    payload = make_candidate_profile()
    evidence = payload["provenance"]["evidence"]
    duplicate = copy.deepcopy(evidence[0])
    assert duplicate["document_id"] == "cv-001"
    duplicate["document_id"] = "questionnaire-001"
    evidence.append(duplicate)

    with pytest.raises(ValidationError, match="evidence_id must be unique"):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_document_registry_key_mismatch() -> None:
    payload = make_candidate_profile()
    documents = payload["provenance"]["documents"]
    documents["cv-001"]["document_id"] = "cv-999"

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_answer_with_unknown_source_document() -> None:
    payload = make_candidate_profile()
    answer = payload["eligibility_answers"]["relocation_willingness"][0]
    answer["source_document_id"] = "document-does-not-exist"

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_missing_cv_document() -> None:
    payload = make_candidate_profile()
    del payload["provenance"]["documents"]["cv-001"]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_unregistered_cv_document_id() -> None:
    payload = make_candidate_profile(cv_document_id="cv-does-not-exist")

    with pytest.raises(ValidationError, match="not registered in provenance.documents"):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_cv_document_id_of_wrong_kind() -> None:
    payload = make_candidate_profile(cv_document_id="questionnaire-001")

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_unresolved_questionnaire_document() -> None:
    payload = make_candidate_profile()
    payload["provenance"]["questionnaire_document_ids"] = ["questionnaire-does-not-exist"]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_questionnaire_document_of_wrong_kind() -> None:
    payload = make_candidate_profile()
    payload["provenance"]["questionnaire_document_ids"] = ["cv-001"]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_clarification_document_of_wrong_kind() -> None:
    payload = make_candidate_profile()
    payload["provenance"]["clarification_document_ids"] = ["cv-001"]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_eligibility_key_constraint_mismatch() -> None:
    payload = make_candidate_profile()
    answers = payload["eligibility_answers"].pop("relocation_willingness")
    payload["eligibility_answers"]["some_other_constraint"] = answers

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_rejects_answer_evidence_from_another_document() -> None:
    payload = make_candidate_profile()
    answer = payload["eligibility_answers"]["graduation_window"][0]
    # Evidence resolves, but belongs to the CV rather than to the source document.
    answer["evidence_ids"] = ["ev-cv-skill-001"]

    with pytest.raises(ValidationError):
        CandidateProfile(**payload)


def test_candidate_profile_accepts_arbitrary_answer_key_for_a_constraint() -> None:
    # The contract validates path shape only. Whether an answer key belongs to a
    # constraint is RuleCatalogue business and must not be checked here.
    payload = make_candidate_profile()
    answer = payload["eligibility_answers"]["relocation_willingness"][0]
    answer["answer_key"] = "some_unlisted_answer_key"

    profile = CandidateProfile(**payload)

    assert (
        profile.eligibility_answers["relocation_willingness"][0].answer_key
        == "some_unlisted_answer_key"
    )


def test_candidate_profile_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(**make_candidate_profile(unexpected_field="not allowed"))


# --- preferences and country codes ---------------------------------------


def test_preferences_accept_null_allowed_country_codes() -> None:
    preferences = CandidatePreferences(
        **make_preferences(allowed_country_codes=None, preferred_country_codes=["JP"])
    )

    assert preferences.allowed_country_codes is None


def test_preferences_accept_non_empty_allowed_country_codes() -> None:
    preferences = CandidatePreferences(**make_preferences())

    assert preferences.allowed_country_codes == ["IT", "NL"]


def test_preferences_reject_empty_allowed_country_codes() -> None:
    with pytest.raises(ValidationError):
        CandidatePreferences(**make_preferences(allowed_country_codes=[]))


def test_preferences_reject_preferred_country_outside_allowed_perimeter() -> None:
    with pytest.raises(ValidationError):
        CandidatePreferences(
            **make_preferences(
                allowed_country_codes=["IT"], preferred_country_codes=["NL"]
            )
        )


@pytest.mark.parametrize("country_codes", [["XX"], ["nl"], ["NL", "NL"]])
def test_preferences_reject_invalid_lowercase_or_duplicate_countries(
    country_codes: list[str],
) -> None:
    with pytest.raises(ValidationError):
        CandidatePreferences(
            **make_preferences(
                allowed_country_codes=None, preferred_country_codes=country_codes
            )
        )


@pytest.mark.parametrize("country_codes", [["XX"], ["it"], ["IT", "IT"]])
def test_declarations_reject_invalid_lowercase_or_duplicate_citizenships(
    country_codes: list[str],
) -> None:
    with pytest.raises(ValidationError):
        UserDeclarations(
            additional_citizenships=country_codes, work_authorizations=[]
        )


@pytest.mark.parametrize("country_code", ["XX", "nl"])
def test_work_authorization_rejects_invalid_country_code(country_code: str) -> None:
    with pytest.raises(ValidationError):
        WorkAuthorizationDeclaration(
            country_code=country_code,
            authorized_to_work=True,
            requires_sponsorship=False,
            evidence_ids=[],
        )


def test_declarations_reject_duplicate_work_authorization_country() -> None:
    with pytest.raises(ValidationError):
        UserDeclarations(
            additional_citizenships=[],
            work_authorizations=[
                {
                    "country_code": "NL",
                    "authorized_to_work": True,
                    "requires_sponsorship": False,
                    "evidence_ids": [],
                },
                {
                    "country_code": "NL",
                    "authorized_to_work": False,
                    "requires_sponsorship": True,
                    "evidence_ids": [],
                },
            ],
        )


def test_work_authorization_fields_are_independently_nullable() -> None:
    declarations = UserDeclarations(
        additional_citizenships=[],
        work_authorizations=[
            {
                "country_code": "NL",
                "authorized_to_work": None,
                "requires_sponsorship": True,
                "evidence_ids": [],
            },
            {
                "country_code": "GB",
                "authorized_to_work": True,
                "requires_sponsorship": None,
                "evidence_ids": [],
            },
        ],
    )

    assert declarations.work_authorizations[0].authorized_to_work is None
    assert declarations.work_authorizations[1].requires_sponsorship is None


def test_declarations_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        UserDeclarations(
            additional_citizenships=[],
            work_authorizations=[],
            unexpected_field="not allowed",
        )


# --- eligibility answers --------------------------------------------------


def test_eligibility_answer_rejects_unknown_state_with_value() -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(
            **make_eligibility_answer(
                state="unknown", answer_type="boolean", value=True
            )
        )


def test_eligibility_answer_rejects_known_state_without_value() -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(
            **make_eligibility_answer(
                state="known", answer_type="boolean", value=None
            )
        )


@pytest.mark.parametrize(
    ("answer_type", "value"),
    [
        ("boolean", True),
        ("integer", 3),
        ("text", "free text answer"),
        ("single_choice", "yes"),
        ("multi_choice", ["english", "italian"]),
        ("date", "2027-07-15"),
    ],
)
def test_eligibility_answer_accepts_matching_answer_type(
    answer_type: str, value: Any
) -> None:
    answer = EligibilityAnswer(
        **make_eligibility_answer(answer_type=answer_type, value=value)
    )

    assert answer.answer_type.value == answer_type


@pytest.mark.parametrize(
    ("answer_type", "value"),
    [
        ("integer", True),
        ("boolean", 1),
        ("boolean", 0),
        ("integer", "3"),
        ("text", 3),
        ("single_choice", ["yes"]),
        ("multi_choice", "english"),
        ("multi_choice", ["english", 3]),
        ("date", "15-07-2027"),
        ("date", 20270715),
    ],
)
def test_eligibility_answer_rejects_answer_type_value_mismatch(
    answer_type: str, value: Any
) -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(
            **make_eligibility_answer(answer_type=answer_type, value=value)
        )


@pytest.mark.parametrize(
    "value",
    [
        "20270715",
        "2027-W28-4",
        "2027-196",
        "2027-7-15",
        "15-07-2027",
        "2027-07-15T00:00:00",
        "2027-13-01",
        "2027-02-30",
        "",
    ],
)
def test_eligibility_answer_rejects_non_calendar_iso_date_strings(value: str) -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(**make_eligibility_answer(answer_type="date", value=value))


def test_eligibility_answer_accepts_exact_calendar_date_string() -> None:
    answer = EligibilityAnswer(
        **make_eligibility_answer(answer_type="date", value="2027-07-15")
    )

    assert answer.value == date(2027, 7, 15)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2027, 7, 15, 0, 0),
        datetime(2027, 7, 15, 10, 30),
        1815000000.0,
        1815000000,
    ],
)
def test_eligibility_answer_rejects_non_date_objects_for_date_answers(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(**make_eligibility_answer(answer_type="date", value=value))


@pytest.mark.parametrize(
    "value",
    [
        ("english", "italian"),
        {"english", "italian"},
        frozenset({"english"}),
    ],
)
def test_eligibility_answer_rejects_non_list_containers_for_multi_choice(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(
            **make_eligibility_answer(answer_type="multi_choice", value=value)
        )


def test_eligibility_answer_rejects_empty_answer_key() -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(**make_eligibility_answer(answer_key=""))


def test_eligibility_answer_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EligibilityAnswer(**make_eligibility_answer(unexpected_field="not allowed"))


# --- clarification requests and candidate field paths --------------------


@pytest.mark.parametrize(
    "field_path",
    [
        "preferences.allowed_country_codes",
        "preferences.preferred_country_codes",
        "preferences.preferred_role_families",
        "preferences.preferred_industries",
        "declarations.additional_citizenships",
        "declarations.work_authorizations.NL.authorized_to_work",
        "declarations.work_authorizations.GB.requires_sponsorship",
        "eligibility_answers.graduation_window.expected_graduation_date",
    ],
)
def test_clarification_accepts_every_approved_field_path_family(
    field_path: str,
) -> None:
    request = ClarificationRequest(
        **make_clarification_request(
            field_path=field_path,
            constraint_id=None,
            answer_type="text",
            allowed_choices=None,
        )
    )

    assert request.field_path == field_path


@pytest.mark.parametrize(
    "field_path",
    [
        "preferences.unknown_destination",
        "skills",
        "declarations.work_authorizations.nl.authorized_to_work",
        "declarations.work_authorizations.XX.authorized_to_work",
        "declarations.work_authorizations.NL.is_citizen",
        "eligibility_answers.graduation_window",
        "eligibility_answers..expected_graduation_date",
        "eligibility_answers.graduation_window.",
        "",
    ],
)
def test_clarification_rejects_unsupported_field_paths(field_path: str) -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(**make_clarification_request(field_path=field_path))


def test_clarification_rejects_field_path_conflicting_with_constraint_id() -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(
            **make_clarification_request(
                field_path="eligibility_answers.graduation_window.expected_graduation_date",
                constraint_id="relocation_willingness",
            )
        )


def test_clarification_accepts_non_eligibility_path_with_constraint_id() -> None:
    request = ClarificationRequest(
        **make_clarification_request(
            field_path="declarations.work_authorizations.NL.authorized_to_work",
            constraint_id="work_authorization_nl",
            answer_type="boolean",
            allowed_choices=None,
        )
    )

    assert request.constraint_id == "work_authorization_nl"


def test_clarification_rejects_missing_field_path_and_constraint_id() -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(
            **make_clarification_request(field_path=None, constraint_id=None)
        )


@pytest.mark.parametrize("answer_type", ["single_choice", "multi_choice"])
@pytest.mark.parametrize("allowed_choices", [None, []])
def test_clarification_rejects_choice_without_allowed_choices(
    answer_type: str, allowed_choices: list[str] | None
) -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(
            **make_clarification_request(
                answer_type=answer_type, allowed_choices=allowed_choices
            )
        )


@pytest.mark.parametrize("answer_type", ["boolean", "text", "date", "integer"])
def test_clarification_rejects_allowed_choices_on_non_choice_types(
    answer_type: str,
) -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(
            **make_clarification_request(
                answer_type=answer_type, allowed_choices=["yes", "no"]
            )
        )


def test_clarification_rejects_unsupported_priority() -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(**make_clarification_request(priority="urgent"))


def test_clarification_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(
            **make_clarification_request(unexpected_field="not allowed")
        )


# --- job snapshot envelope (0.2.1-draft) ---------------------------------


SNAPSHOT_FIXTURE_ROOT = (
    Path(__file__).parent / "fixtures" / "contracts" / "v0.2.1-draft"
)


def load_snapshot_fixture() -> dict[str, Any]:
    """Read the shared snapshot fixture as a mutable JSON payload."""

    return json.loads(
        (SNAPSHOT_FIXTURE_ROOT / "job_snapshot.json").read_text(encoding="utf-8")
    )


def make_job_snapshot(**overrides: Any) -> dict[str, Any]:
    """Snapshot fixture payload, deep-copied so tests can mutate freely."""

    payload = load_snapshot_fixture()
    payload.update(copy.deepcopy(overrides))
    return payload


def make_source_manifest_entry(**overrides: Any) -> dict[str, Any]:
    """Minimal valid SourceManifestEntry payload."""

    payload: dict[str, Any] = {
        "source": "synthetic",
        "source_ref": "synthetic_fixture",
        "retrieved_at": "2026-09-20T11:30:00+00:00",
        "record_count": 2,
        "redistribution_allowed": True,
    }
    payload.update(copy.deepcopy(overrides))
    return payload


def make_quarantine_summary(**overrides: Any) -> dict[str, Any]:
    """Minimal valid QuarantineSummary payload."""

    payload: dict[str, Any] = {
        "reason": "missing_job_description_text",
        "count": 1,
    }
    payload.update(copy.deepcopy(overrides))
    return payload


def test_snapshot_fixture_round_trips() -> None:
    payload = load_snapshot_fixture()

    parsed = JobSnapshot.model_validate(payload)
    reparsed = JobSnapshot.model_validate_json(parsed.model_dump_json())

    assert reparsed == parsed
    assert parsed.schema_version == SNAPSHOT_CONTRACT_VERSION


def test_snapshot_fixture_keeps_frozen_job_payload_version() -> None:
    snapshot = JobSnapshot.model_validate(load_snapshot_fixture())

    assert [job.schema_version for job in snapshot.jobs] == [
        CONTRACT_VERSION,
        CONTRACT_VERSION,
    ]


@pytest.mark.parametrize("schema_version", ["0.2.0-draft", "0.2.2-draft", "0.2.1"])
def test_snapshot_rejects_other_schema_versions(schema_version: str) -> None:
    with pytest.raises(ValidationError):
        JobSnapshot(**make_job_snapshot(schema_version=schema_version))


def test_snapshot_normalizes_created_at_to_utc() -> None:
    snapshot = JobSnapshot(
        **make_job_snapshot(created_at="2026-09-20T20:00:00+08:00")
    )

    assert snapshot.created_at == datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def test_snapshot_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        JobSnapshot(**make_job_snapshot(created_at="2026-09-20T12:00:00"))


def test_snapshot_rejects_empty_snapshot_id() -> None:
    with pytest.raises(ValidationError):
        JobSnapshot(**make_job_snapshot(snapshot_id=""))


def test_snapshot_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        JobSnapshot(**make_job_snapshot(unexpected_field="not allowed"))


def test_snapshot_accepts_empty_collections() -> None:
    snapshot = JobSnapshot(
        **make_job_snapshot(
            jobs=[], documents={}, source_manifest=[], quarantine=[]
        )
    )

    assert snapshot.jobs == []
    assert snapshot.documents == {}


def test_manifest_entry_normalizes_retrieved_at_to_utc() -> None:
    entry = SourceManifestEntry(
        **make_source_manifest_entry(retrieved_at="2026-09-20T19:30:00+08:00")
    )

    assert entry.retrieved_at == datetime(2026, 9, 20, 11, 30, tzinfo=timezone.utc)


def test_manifest_entry_rejects_naive_retrieved_at() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry(
            **make_source_manifest_entry(retrieved_at="2026-09-20T11:30:00")
        )


def test_manifest_entry_accepts_zero_record_count() -> None:
    entry = SourceManifestEntry(**make_source_manifest_entry(record_count=0))

    assert entry.record_count == 0


def test_manifest_entry_rejects_negative_record_count() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry(**make_source_manifest_entry(record_count=-1))


@pytest.mark.parametrize("record_count", ["2", "", True, False])
def test_manifest_entry_rejects_non_integer_record_count(
    record_count: Any,
) -> None:
    """A count is an int, so a numeric string or a bool is a defect."""

    with pytest.raises(ValidationError):
        SourceManifestEntry(
            **make_source_manifest_entry(record_count=record_count)
        )


def test_manifest_entry_allows_unknown_redistribution() -> None:
    entry = SourceManifestEntry(
        **make_source_manifest_entry(redistribution_allowed=None)
    )

    assert entry.redistribution_allowed is None


@pytest.mark.parametrize(
    "redistribution_allowed", [1, 0, "true", "false", "yes", ""]
)
def test_manifest_entry_rejects_pseudo_boolean_redistribution(
    redistribution_allowed: Any,
) -> None:
    """Redistribution is a declared permission; only a real bool or null."""

    with pytest.raises(ValidationError):
        SourceManifestEntry(
            **make_source_manifest_entry(
                redistribution_allowed=redistribution_allowed
            )
        )


@pytest.mark.parametrize("field_name", ["source", "source_ref"])
def test_manifest_entry_rejects_empty_strings(field_name: str) -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry(**make_source_manifest_entry(**{field_name: ""}))


def test_manifest_entry_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry(
            **make_source_manifest_entry(unexpected_field="not allowed")
        )


@pytest.mark.parametrize("count", [0, -1])
def test_quarantine_summary_rejects_non_positive_count(count: int) -> None:
    with pytest.raises(ValidationError):
        QuarantineSummary(**make_quarantine_summary(count=count))


@pytest.mark.parametrize("count", ["1", "", True, False])
def test_quarantine_summary_rejects_non_integer_count(count: Any) -> None:
    """A count is an int, so a numeric string or a bool is a defect."""

    with pytest.raises(ValidationError):
        QuarantineSummary(**make_quarantine_summary(count=count))


def test_quarantine_summary_rejects_empty_reason() -> None:
    with pytest.raises(ValidationError):
        QuarantineSummary(**make_quarantine_summary(reason=""))


def test_quarantine_summary_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        QuarantineSummary(
            **make_quarantine_summary(unexpected_field="not allowed")
        )


def test_snapshot_rejects_registry_key_that_disagrees_with_document_id() -> None:
    payload = make_job_snapshot()
    payload["documents"]["renamed-key"] = payload["documents"].pop("job-ats-001")

    with pytest.raises(ValidationError):
        JobSnapshot(**payload)


def test_snapshot_rejects_unregistered_job_description() -> None:
    payload = make_job_snapshot()
    del payload["documents"]["job-doc-001"]

    with pytest.raises(ValidationError):
        JobSnapshot(**payload)


def test_snapshot_rejects_unregistered_job_source_document() -> None:
    payload = make_job_snapshot()
    del payload["documents"]["job-ats-001"]

    with pytest.raises(ValidationError):
        JobSnapshot(**payload)


def test_snapshot_rejects_conflicting_registry_copy_of_description() -> None:
    payload = make_job_snapshot()
    payload["documents"]["job-doc-001"]["text"] = "Diverged registry copy."

    with pytest.raises(ValidationError):
        JobSnapshot(**payload)


def test_snapshot_rejects_conflicting_registry_copy_of_source_document() -> None:
    payload = make_job_snapshot()
    payload["documents"]["job-ats-001"]["content_hash"] = "diverged-hash"

    with pytest.raises(ValidationError):
        JobSnapshot(**payload)


def test_snapshot_rejects_job_evidence_document_missing_from_registry() -> None:
    payload = make_job_snapshot()
    payload["jobs"][0]["evidence"][0]["document_id"] = "job-doc-unknown"

    with pytest.raises(ValidationError):
        JobSnapshot(**payload)
