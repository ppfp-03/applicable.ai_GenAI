"""Tests for shared Applicable.ai data contracts."""

from datetime import timezone

import pytest
from pydantic import ValidationError

from oi.contracts import ExtractionReceipt, SourceDocument


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
