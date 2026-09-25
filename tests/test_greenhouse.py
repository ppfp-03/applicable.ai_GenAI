from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from oi.contracts import JobSnapshot, SourceManifestEntry
from oi.io import greenhouse as greenhouse_module
from oi.io.greenhouse import (
    GreenhouseFetchError,
    GreenhouseNormalizationError,
    fetch_greenhouse_job,
    greenhouse_job_to_record,
    normalize_greenhouse_content,
)

OBSERVED_AT = datetime(2026, 9, 21, 0, 30, tzinfo=timezone.utc)


def documented_rothesay_shaped_payload(**overrides: object) -> dict[str, object]:
    """Network-free Greenhouse-shaped fixture, not a captured live response."""

    payload: dict[str, object] = {
        "id": 8784142002,
        "internal_job_id": 123456,
        "title": "2027 Summer Internship Programme - Trading and Asset Origination",
        "company_name": "Rothesay Graduates",
        "first_published": "2026-09-04T09:15:00Z",
        "updated_at": "2026-09-10T13:20:00+00:00",
        "application_deadline": "2026-11-08T23:59:00+00:00",
        "location": {"name": "London"},
        "content": (
            "&lt;p&gt;Application deadline: 8th November 2026&lt;/p&gt;"
            "&lt;p&gt;Eligibility: Penultimate year students graduating in "
            "Summer 2028&lt;/p&gt;"
            "&lt;ul&gt;&lt;li&gt;Fluency in English is a prerequisite."
            "&lt;/li&gt;&lt;/ul&gt;"
        ),
        "absolute_url": (
            "https://job-boards.greenhouse.io/rothesaygraduates/jobs/8784142002"
        ),
        "language": "en",
    }
    payload.update(overrides)
    return payload


def build_record(payload: dict[str, object] | None = None):
    return greenhouse_job_to_record(
        documented_rothesay_shaped_payload() if payload is None else payload,
        board_token="rothesaygraduates",
        observed_at=OBSERVED_AT,
    )


def test_documented_greenhouse_shape_converts_to_valid_job_record() -> None:
    record = build_record()

    assert record.company == "Rothesay Graduates"
    assert record.title == (
        "2027 Summer Internship Programme - Trading and Asset Origination"
    )
    assert record.locations[0].city == "London"
    assert record.locations[0].country_code is None
    assert record.active_state.value == "unknown"
    assert record.discovery_kind.value == "initial_snapshot"


def test_namespaced_job_id_is_stable() -> None:
    record = build_record()

    assert record.source_job_id == "8784142002"
    assert record.job_id == "greenhouse:8784142002"


def test_first_published_and_updated_at_remain_distinct() -> None:
    record = build_record()

    assert record.source_published_at == datetime(
        2026, 9, 4, 9, 15, tzinfo=timezone.utc
    )
    assert record.source_updated_at == datetime(
        2026, 9, 10, 13, 20, tzinfo=timezone.utc
    )
    assert record.source_published_at != record.source_updated_at


def test_missing_first_published_does_not_fall_back_to_updated_at() -> None:
    payload = documented_rothesay_shaped_payload()
    del payload["first_published"]

    record = build_record(payload)

    assert record.source_published_at is None
    assert record.source_updated_at == datetime(
        2026, 9, 10, 13, 20, tzinfo=timezone.utc
    )


def test_missing_application_deadline_stays_null() -> None:
    payload = documented_rothesay_shaped_payload()
    del payload["application_deadline"]

    record = build_record(payload)

    assert record.deadline_at is None


def test_description_html_and_entities_normalize_to_readable_non_empty_text() -> None:
    normalized = normalize_greenhouse_content(
        "&amp;lt;p&amp;gt;R&amp;amp;D role&amp;lt;/p&amp;gt;"
        "&amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;First item&amp;lt;/li&amp;gt;"
        "&amp;lt;li&amp;gt;Second item&amp;lt;/li&amp;gt;&amp;lt;/ul&amp;gt;"
    )

    assert normalized == "R&D role\n- First item\n- Second item"


def test_empty_or_unusable_description_fails_visibly() -> None:
    with pytest.raises(GreenhouseNormalizationError):
        build_record(documented_rothesay_shaped_payload(content="   "))

    with pytest.raises(GreenhouseNormalizationError):
        build_record(documented_rothesay_shaped_payload(content="<p>   </p>"))


def test_source_metadata_document_is_deterministic() -> None:
    first = build_record().source_documents[0]
    second = build_record().source_documents[0]

    assert first.text == second.text
    assert first.content_hash == second.content_hash
    parsed = json.loads(first.text)
    assert parsed["id"] == 8784142002
    assert parsed["location"] == {"name": "London"}


def test_evidence_references_resolve_and_quotes_are_in_source_documents() -> None:
    record = build_record()
    documents = {
        record.description.document_id: record.description,
        **{document.document_id: document for document in record.source_documents},
    }

    for reference in record.evidence:
        assert reference.document_id in documents
        assert reference.quote in documents[reference.document_id].text

    location_evidence_id = record.locations[0].evidence_ids[0]
    assert any(
        reference.evidence_id == location_evidence_id
        for reference in record.evidence
    )


def test_group_a_ingestion_leaves_facts_and_extraction_null() -> None:
    record = build_record()

    assert record.facts is None
    assert record.extraction is None


def test_record_can_be_wrapped_in_snapshot_and_round_trip() -> None:
    record = build_record()
    documents = {
        record.description.document_id: record.description,
        **{document.document_id: document for document in record.source_documents},
    }
    snapshot = JobSnapshot(
        schema_version="0.2.1-draft",
        snapshot_id="greenhouse-rothesay-smoke-001",
        created_at=OBSERVED_AT,
        jobs=[record],
        documents=documents,
        source_manifest=[
            SourceManifestEntry(
                source="greenhouse",
                source_ref=(
                    "https://boards-api.greenhouse.io/v1/boards/"
                    "rothesaygraduates/jobs/8784142002"
                ),
                retrieved_at=OBSERVED_AT,
                record_count=1,
                redistribution_allowed=None,
            )
        ],
        quarantine=[],
    )

    reparsed = JobSnapshot.model_validate_json(snapshot.model_dump_json())

    assert reparsed == snapshot


class FakeResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_fetch_uses_public_get_endpoint_and_validates_requested_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = documented_rothesay_shaped_payload()
    observed: dict[str, object] = {}

    def fake_urlopen(request, timeout: float):
        observed["url"] = request.full_url
        observed["method"] = request.get_method()
        observed["authorization"] = request.headers.get("Authorization")
        observed["timeout"] = timeout
        return FakeResponse(payload)

    monkeypatch.setattr(greenhouse_module, "urlopen", fake_urlopen)

    returned = fetch_greenhouse_job(
        "rothesaygraduates", "8784142002", timeout_s=7.5
    )

    assert returned == payload
    assert observed == {
        "url": (
            "https://boards-api.greenhouse.io/v1/boards/"
            "rothesaygraduates/jobs/8784142002"
        ),
        "method": "GET",
        "authorization": None,
        "timeout": 7.5,
    }


def test_fetch_rejects_response_for_different_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        greenhouse_module,
        "urlopen",
        lambda request, timeout: FakeResponse(
            documented_rothesay_shaped_payload(id=999999)
        ),
    )

    with pytest.raises(GreenhouseFetchError):
        fetch_greenhouse_job("rothesaygraduates", "8784142002")


def test_normalization_rejects_naive_source_timestamps() -> None:
    with pytest.raises(GreenhouseNormalizationError):
        build_record(
            documented_rothesay_shaped_payload(
                first_published="2026-09-04T09:15:00"
            )
        )


def test_observed_at_must_be_timezone_aware() -> None:
    with pytest.raises(GreenhouseNormalizationError):
        greenhouse_job_to_record(
            documented_rothesay_shaped_payload(),
            board_token="rothesaygraduates",
            observed_at=datetime(2026, 9, 21, 0, 30),
        )
