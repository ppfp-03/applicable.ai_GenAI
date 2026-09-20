"""Tests for shared Applicable.ai data contracts."""

from datetime import timezone

import pytest
from pydantic import ValidationError

from oi.contracts import (
    ExtractionReceipt,
    JobRecord,
    RequirementFact,
    SourceDocument,
)


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
