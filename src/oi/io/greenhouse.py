"""Greenhouse Job Board API ingestion for Group A.

This module fetches one public Greenhouse job post and normalizes only the
source-owned fields needed by the frozen shared JobRecord contract. Semantic
job extraction, eligibility, and ranking remain outside this layer.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from oi.contracts import (
    CONTRACT_VERSION,
    ActiveState,
    DiscoveryKind,
    DocumentKind,
    EvidenceRef,
    JobLocation,
    JobRecord,
    SourceDocument,
)

GREENHOUSE_API_ROOT = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseFetchError(RuntimeError):
    """Raised when one public Greenhouse job cannot be fetched safely."""


class GreenhouseNormalizationError(ValueError):
    """Raised when a Greenhouse payload cannot form a valid JobRecord."""


class _ReadableHtmlParser(HTMLParser):
    """Convert source HTML to deterministic readable text without rendering it."""

    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "main",
        "nav",
        "p",
        "section",
        "table",
        "tr",
        "ul",
        "ol",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def _line_break(self) -> None:
        if self._parts and self._parts[-1] != "\n":
            self._parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag == "br":
            self._line_break()
        elif tag == "li":
            self._line_break()
            self._parts.append("- ")
        elif tag in self._BLOCK_TAGS:
            self._line_break()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "li" or tag in self._BLOCK_TAGS:
            self._line_break()

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        lines = []
        for raw_line in "".join(self._parts).splitlines():
            normalized = " ".join(raw_line.split())
            if normalized:
                lines.append(normalized)
        return "\n".join(lines)


def _non_empty_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise GreenhouseNormalizationError(
            f"Greenhouse field '{field}' must be a non-empty string"
        )
    return value.strip()


def _source_job_id(payload: dict[str, Any]) -> str:
    value = payload.get("id")
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise GreenhouseNormalizationError(
            "Greenhouse field 'id' must be an integer or non-empty string"
        )
    normalized = str(value).strip()
    if not normalized:
        raise GreenhouseNormalizationError(
            "Greenhouse field 'id' must be an integer or non-empty string"
        )
    return normalized


def _endpoint(board_token: str, job_id: str) -> str:
    token = board_token.strip()
    post_id = str(job_id).strip()
    if not token:
        raise ValueError("board_token must be non-empty")
    if not post_id:
        raise ValueError("job_id must be non-empty")
    return (
        f"{GREENHOUSE_API_ROOT}/{quote(token, safe='')}/jobs/"
        f"{quote(post_id, safe='')}"
    )


def fetch_greenhouse_job(
    board_token: str,
    job_id: str,
    *,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Fetch one public Greenhouse job and return its decoded JSON object.

    The public Job Board API requires no authentication for GET requests.
    Identity is checked here so a caller cannot normalize a different post than
    the one it requested.
    """

    url = _endpoint(board_token, job_id)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Applicable.ai Opportunity Intelligence/0.1",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_s) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise GreenhouseFetchError(
                    f"Greenhouse returned HTTP {status} for job {job_id}"
                )
            body = response.read()
        decoded = body.decode("utf-8")
        payload = json.loads(decoded)
    except GreenhouseFetchError:
        raise
    except (
        HTTPError,
        URLError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise GreenhouseFetchError(
            f"Could not fetch Greenhouse job {job_id} from board '{board_token}'"
        ) from error

    if not isinstance(payload, dict):
        raise GreenhouseFetchError("Greenhouse job response must be a JSON object")

    returned_id = payload.get("id")
    if isinstance(returned_id, bool) or str(returned_id).strip() != str(job_id).strip():
        raise GreenhouseFetchError(
            f"Greenhouse returned job id '{returned_id}' for requested id '{job_id}'"
        )

    return payload


def normalize_greenhouse_content(content: str) -> str:
    """Convert Greenhouse HTML/entity-encoded content to deterministic text."""

    if not isinstance(content, str) or not content.strip():
        raise GreenhouseNormalizationError(
            "Greenhouse field 'content' must be a non-empty string"
        )

    # Greenhouse's API documentation shows editor HTML represented through
    # entities. Decode a bounded number of times so both once- and twice-escaped
    # source content become parseable without an unbounded transform loop.
    decoded = content
    for _ in range(2):
        unescaped = html.unescape(decoded)
        if unescaped == decoded:
            break
        decoded = unescaped

    parser = _ReadableHtmlParser()
    parser.feed(decoded)
    parser.close()
    normalized = parser.text().strip()
    if not normalized:
        raise GreenhouseNormalizationError(
            "Greenhouse job description is empty after HTML normalization"
        )
    return normalized


def _parse_optional_timestamp(payload: dict[str, Any], field: str) -> datetime | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GreenhouseNormalizationError(
            f"Greenhouse field '{field}' must be null or a non-empty timestamp string"
        )

    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise GreenhouseNormalizationError(
            f"Greenhouse field '{field}' is not a valid ISO-8601 timestamp"
        ) from error

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GreenhouseNormalizationError(
            f"Greenhouse field '{field}' must include a timezone"
        )
    return parsed.astimezone(timezone.utc)


def _location_name(payload: dict[str, Any]) -> str | None:
    location = payload.get("location")
    if location is None:
        return None
    if not isinstance(location, dict):
        raise GreenhouseNormalizationError(
            "Greenhouse field 'location' must be null or an object"
        )
    value = location.get("name")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GreenhouseNormalizationError(
            "Greenhouse field 'location.name' must be null or a non-empty string"
        )
    return value.strip()


def _metadata_payload(payload: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for field in (
        "id",
        "internal_job_id",
        "company_name",
        "title",
        "first_published",
        "updated_at",
        "application_deadline",
        "absolute_url",
        "language",
    ):
        if field in payload:
            metadata[field] = payload[field]

    if "location" in payload:
        location = payload.get("location")
        if location is None:
            metadata["location"] = None
        elif isinstance(location, dict):
            metadata["location"] = {"name": location.get("name")}
        else:
            raise GreenhouseNormalizationError(
                "Greenhouse field 'location' must be null or an object"
            )

    return metadata


def _stable_json(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _metadata_evidence(
    *,
    source_job_id: str,
    metadata_document_id: str,
    field_path: str,
    source_value: str,
    suffix: str,
) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"greenhouse:{source_job_id}:{suffix}",
        document_id=metadata_document_id,
        quote=source_value,
        field_path=field_path,
    )


def greenhouse_job_to_record(
    payload: dict[str, Any],
    *,
    board_token: str,
    observed_at: datetime,
) -> JobRecord:
    """Convert one Greenhouse API payload into the frozen shared JobRecord."""

    if not isinstance(payload, dict):
        raise GreenhouseNormalizationError("Greenhouse payload must be a JSON object")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise GreenhouseNormalizationError("observed_at must be timezone-aware")

    source_job_id = _source_job_id(payload)
    company = _non_empty_string(payload, "company_name")
    title = _non_empty_string(payload, "title")
    absolute_url = _non_empty_string(payload, "absolute_url")
    raw_content = _non_empty_string(payload, "content")
    description_text = normalize_greenhouse_content(raw_content)

    published_at = _parse_optional_timestamp(payload, "first_published")
    updated_at = _parse_optional_timestamp(payload, "updated_at")
    deadline_at = _parse_optional_timestamp(payload, "application_deadline")
    location_name = _location_name(payload)

    endpoint = _endpoint(board_token, source_job_id)
    description_document_id = f"greenhouse:{source_job_id}:description"
    metadata_document_id = f"greenhouse:{source_job_id}:ats_metadata"

    description_document = SourceDocument(
        document_id=description_document_id,
        kind=DocumentKind.JOB,
        text=description_text,
        content_hash=_sha256_text(description_text),
        source_ref=endpoint,
    )

    metadata_text = _stable_json(_metadata_payload(payload))
    metadata_document = SourceDocument(
        document_id=metadata_document_id,
        kind=DocumentKind.ATS_METADATA,
        text=metadata_text,
        content_hash=_sha256_text(metadata_text),
        source_ref=endpoint,
    )

    evidence: list[EvidenceRef] = []
    locations: list[JobLocation] = []

    if location_name is not None:
        location_evidence = _metadata_evidence(
            source_job_id=source_job_id,
            metadata_document_id=metadata_document_id,
            field_path="locations",
            source_value=location_name,
            suffix="location",
        )
        evidence.append(location_evidence)
        # Greenhouse exposes one structured location name. For this bounded
        # source adapter we preserve that source-supported label verbatim and
        # deliberately do not infer a country code from it.
        locations.append(
            JobLocation(
                country_code=None,
                city=location_name,
                evidence_ids=[location_evidence.evidence_id],
            )
        )

    timestamp_fields = (
        ("first_published", "source_published_at", published_at, "published"),
        ("updated_at", "source_updated_at", updated_at, "updated"),
        ("application_deadline", "deadline_at", deadline_at, "deadline"),
    )
    for source_field, field_path, parsed_value, suffix in timestamp_fields:
        if parsed_value is None:
            continue
        original = payload[source_field]
        evidence.append(
            _metadata_evidence(
                source_job_id=source_job_id,
                metadata_document_id=metadata_document_id,
                field_path=field_path,
                source_value=original,
                suffix=suffix,
            )
        )

    observed_utc = observed_at.astimezone(timezone.utc)
    return JobRecord(
        schema_version=CONTRACT_VERSION,
        job_id=f"greenhouse:{source_job_id}",
        source="greenhouse",
        source_job_id=source_job_id,
        company=company,
        title=title,
        url=absolute_url,
        description=description_document,
        source_documents=[metadata_document],
        locations=locations,
        source_published_at=published_at,
        source_updated_at=updated_at,
        deadline_at=deadline_at,
        first_seen_at=observed_utc,
        last_seen_at=observed_utc,
        active_state=ActiveState.UNKNOWN,
        discovery_kind=DiscoveryKind.INITIAL_SNAPSHOT,
        facts=None,
        evidence=evidence,
        extraction=None,
    )
