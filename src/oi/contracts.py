"""Shared serializable data contracts for Applicable.ai.

These models validate data shape and types only.
Business rules such as eligibility and ranking live elsewhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


CONTRACT_VERSION = "0.2.0-draft"



class ContractModel(BaseModel):
    """Base class for all shared cross-group contracts."""

    model_config = ConfigDict(extra="forbid")


class DocumentKind(str, Enum):
    """Supported source-document categories."""

    CV = "cv"
    JOB = "job"
    QUESTIONNAIRE = "questionnaire"
    ATS_METADATA = "ats_metadata"


class ExtractionMode(str, Enum):
    """How a semantic extraction result was produced."""

    LIVE = "live"
    CACHE = "cache"
    FIXTURE = "fixture"


class SourceDocument(ContractModel):
    """Raw source text plus stable provenance."""

    document_id: str = Field(min_length=1)
    kind: DocumentKind
    text: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)


class EvidenceRef(ContractModel):
    """A source quote supporting one structured field."""

    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    field_path: str = Field(min_length=1)


class SupportedText(ContractModel):
    """Text value together with the evidence that supports it."""

    value: str = Field(min_length=1)
    evidence_ids: list[str]


class ExtractionReceipt(ContractModel):
    """Provenance and reproducibility metadata for an extraction."""

    mode: ExtractionMode
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    input_hash: str = Field(min_length=1)
    produced_at: AwareDatetime
    latency_ms: int | None = Field(default=None, ge=0)

    @field_validator("produced_at")
    @classmethod
    def normalize_produced_at_to_utc(cls, value: datetime) -> datetime:
        """Serialize extraction timestamps consistently in UTC."""

        return value.astimezone(timezone.utc)
