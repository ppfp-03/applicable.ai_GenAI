"""Shared data contracts for the candidate intelligence pipeline.

These models are the common vocabulary between PDF extraction, model-based
extraction, the candidate profile, and the UI layer. They carry data only:
no validation rules, no business logic.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SourceDocument(BaseModel):
    """A raw input document (e.g. a CV) and its extracted text.

    Provenance is recorded in two independent fields:

    source_ref
        Where the document came from -- its origin (e.g. "uploaded_pdf").
    extraction_method
        How the text was obtained from it (e.g. "native_pdf", "ocr").

    Keeping these separate lets the same origin be read by different means:
    an uploaded PDF may be parsed natively or, when it is a scan, via OCR.
    """

    document_id: str
    kind: str
    text: str
    content_hash: Optional[str] = None
    source_ref: Optional[str] = None
    extraction_method: str


class EvidenceRef(BaseModel):
    """A quote from a source document backing one field of a profile."""

    evidence_id: str
    document_id: str
    quote: str
    field_path: str


class ExtractionReceipt(BaseModel):
    """Provenance of an extraction run: how and by what it was produced."""

    mode: str
    provider: str
    model_id: Optional[str] = None
    produced_at: Optional[str] = None


class CandidateProfile(BaseModel):
    """Structured view of a candidate, with its supporting evidence."""

    candidate_id: str
    name: Optional[str] = None
    skills: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    languages: list[str] = []
    evidence: list[EvidenceRef] = []
    extraction: Optional[ExtractionReceipt] = None
