"""Tests for the A-owned input path: snapshot loading and PDF text extraction."""

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter

from oi.contracts import JobSnapshot
from oi.io import pdf as pdf_module
from oi.io.pdf import PdfExtractionError, extract_pdf_text
from oi.io.snapshot import load_snapshot

SNAPSHOT_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "contracts"
    / "v0.2.1-draft"
    / "job_snapshot.json"
)


# --- snapshot loader ------------------------------------------------------


def test_load_snapshot_returns_validated_snapshot() -> None:
    snapshot = load_snapshot(SNAPSHOT_FIXTURE)

    assert isinstance(snapshot, JobSnapshot)
    assert snapshot.schema_version == "0.2.1-draft"
    assert snapshot.snapshot_id == "synthetic-snapshot-001"
    assert [job.job_id for job in snapshot.jobs] == [
        "synthetic:job-001",
        "synthetic:job-002",
    ]


def test_load_snapshot_round_trips_through_serialization() -> None:
    snapshot = load_snapshot(SNAPSHOT_FIXTURE)

    reloaded = JobSnapshot.model_validate_json(snapshot.model_dump_json())

    assert reloaded == snapshot


def test_load_snapshot_does_not_modify_the_file() -> None:
    before = SNAPSHOT_FIXTURE.read_bytes()

    load_snapshot(SNAPSHOT_FIXTURE)

    assert SNAPSHOT_FIXTURE.read_bytes() == before


def test_load_snapshot_raises_for_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_snapshot(tmp_path / "absent.json")


def test_load_snapshot_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "malformed.json"
    path.write_text('{"schema_version": "0.2.1-draft",', encoding="utf-8")

    with pytest.raises(ValidationError):
        load_snapshot(path)


def test_load_snapshot_rejects_json_that_is_not_an_object(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_snapshot(path)


def test_load_snapshot_does_not_default_missing_fields(tmp_path: Path) -> None:
    payload: dict[str, Any] = json.loads(
        SNAPSHOT_FIXTURE.read_text(encoding="utf-8")
    )
    del payload["source_manifest"]
    path = tmp_path / "incomplete.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError) as error:
        load_snapshot(path)

    assert any(
        entry["loc"] == ("source_manifest",) for entry in error.value.errors()
    )


def test_load_snapshot_rejects_contract_invalid_snapshot(tmp_path: Path) -> None:
    payload = json.loads(SNAPSHOT_FIXTURE.read_text(encoding="utf-8"))
    payload["jobs"][0]["evidence"][0]["document_id"] = "job-doc-unknown"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_snapshot(path)


# --- PDF extraction -------------------------------------------------------


def build_pdf(content_stream: bytes) -> bytes:
    """Build a minimal single-page PDF holding one content stream.

    Written by hand rather than through a PDF library so the bytes under
    test stay fixed and the test needs no new dependency.
    """

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(content_stream)).encode()
        + b" >>\nstream\n"
        + content_stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_offset = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    return bytes(out)


def build_text_pdf(text: str) -> bytes:
    """Build a minimal PDF whose single page shows `text`."""

    return build_pdf(
        b"BT /F1 12 Tf 20 100 Td (" + text.encode("ascii") + b") Tj ET"
    )


class FakePage:
    """Stand-in for a pypdf page, so page text is fixed by the test."""

    def __init__(self, text: str | None, error: Exception | None = None) -> None:
        self._text = text
        self._error = error

    def extract_text(self) -> str | None:
        if self._error is not None:
            raise self._error
        return self._text


class FakeReader:
    """Stand-in for `PdfReader` over a fixed list of pages."""

    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages


def use_fake_reader(
    monkeypatch: pytest.MonkeyPatch, pages: list[FakePage]
) -> None:
    """Replace the module-level PdfReader with a fake over `pages`."""

    monkeypatch.setattr(
        pdf_module, "PdfReader", lambda _stream: FakeReader(pages)
    )


def test_extract_pdf_text_returns_source_document() -> None:
    pdf_bytes = build_text_pdf("Synthetic CV text")

    document = extract_pdf_text(pdf_bytes, "cv-001")

    assert document.document_id == "cv-001"
    assert document.kind.value == "cv"
    assert document.text == "Synthetic CV text"
    assert document.content_hash == hashlib.sha256(pdf_bytes).hexdigest()
    assert document.source_ref == "uploaded_pdf"


def test_extract_pdf_text_joins_pages_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_fake_reader(
        monkeypatch,
        [FakePage("page one"), FakePage(None), FakePage("page three")],
    )

    document = extract_pdf_text(b"%PDF-fake", "cv-002")

    assert document.text == "page one\n\npage three"


def test_extract_pdf_text_rejects_pdf_without_text() -> None:
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(build_pdf(b""), "cv-003")


def test_extract_pdf_text_rejects_whitespace_only_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_fake_reader(monkeypatch, [FakePage("   "), FakePage("\n\t")])

    with pytest.raises(PdfExtractionError):
        extract_pdf_text(b"%PDF-fake", "cv-004")


def test_extract_pdf_text_rejects_malformed_bytes() -> None:
    with pytest.raises(PdfExtractionError) as error:
        extract_pdf_text(b"this is not a pdf", "cv-005")

    assert error.value.__cause__ is not None


def test_extract_pdf_text_rejects_undecryptable_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)

    with pytest.raises(PdfExtractionError) as error:
        extract_pdf_text(buffer.getvalue(), "cv-006")

    assert error.value.__cause__ is not None


def test_extract_pdf_text_wraps_page_extraction_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause = RuntimeError("damaged content stream")
    use_fake_reader(monkeypatch, [FakePage(None, error=cause)])

    with pytest.raises(PdfExtractionError) as error:
        extract_pdf_text(b"%PDF-fake", "cv-007")

    assert error.value.__cause__ is cause


def test_pdf_extraction_error_stays_a_value_error() -> None:
    assert issubclass(PdfExtractionError, ValueError)
