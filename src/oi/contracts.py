"""Shared serializable data contracts for Applicable.ai.

These models validate data shape and types only.
Business rules such as eligibility and ranking live elsewhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


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


class RequirementClassification(str, Enum):
    """Semantic role of a requirement extracted from a job."""

    HARD_CONSTRAINT = "hard_constraint"
    FIT = "fit"
    INFORMATIONAL = "informational"


class RequirementModality(str, Enum):
    """How strongly the source states a requirement."""

    MANDATORY = "mandatory"
    PREFERRED = "preferred"
    OPTIONAL = "optional"
    UNSPECIFIED = "unspecified"


class ActiveState(str, Enum):
    """Observed availability state of a job."""

    ACTIVE = "active"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class DiscoveryKind(str, Enum):
    """How a job entered the dataset."""

    INITIAL_SNAPSHOT = "initial_snapshot"
    LATER_OBSERVATION = "later_observation"
    SYNTHETIC_SCENARIO = "synthetic_scenario"


class RequirementFact(ContractModel):
    """Structured intelligence-layer interpretation of a job requirement."""

    requirement_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    classification: RequirementClassification
    modality: RequirementModality
    constraint_id: str | None = Field(default=None, min_length=1)
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_constraint_link(self) -> "RequirementFact":
        """Hard constraints must map to a rule-catalogue ID only."""

        if (
            self.classification == RequirementClassification.HARD_CONSTRAINT
            and self.constraint_id is None
        ):
            raise ValueError("hard_constraint requirements need constraint_id")

        if (
            self.classification != RequirementClassification.HARD_CONSTRAINT
            and self.constraint_id is not None
        ):
            raise ValueError("constraint_id is only valid for hard_constraint")

        return self


class JobFacts(ContractModel):
    """Semantic facts extracted from a job description."""

    skills: list[SupportedText]
    experience: list[SupportedText]
    education: list[SupportedText]
    role_family: SupportedText | None = None
    requirements: list[RequirementFact]


class JobLocation(ContractModel):
    """Source-supported job location."""

    country_code: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    evidence_ids: list[str]


class JobRecord(ContractModel):
    """Normalized job shared between data/input and intelligence layers."""

    schema_version: str = Field(pattern=r"^0\.2\.0-draft$")
    job_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)

    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)

    description: SourceDocument
    source_documents: list[SourceDocument]
    locations: list[JobLocation]

    source_published_at: AwareDatetime | None = None
    source_updated_at: AwareDatetime | None = None
    deadline_at: AwareDatetime | None = None

    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime

    active_state: ActiveState
    discovery_kind: DiscoveryKind

    facts: JobFacts | None = None
    evidence: list[EvidenceRef]
    extraction: ExtractionReceipt | None = None

    @field_validator(
        "source_published_at",
        "source_updated_at",
        "deadline_at",
        "first_seen_at",
        "last_seen_at",
    )
    @classmethod
    def normalize_job_timestamps_to_utc(
        cls, value: datetime | None
    ) -> datetime | None:
        """Serialize source and observation timestamps consistently in UTC."""

        if value is None:
            return None
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_job_record(self) -> "JobRecord":
        """Validate cross-field invariants of the shared job contract."""

        expected_job_id = f"{self.source}:{self.source_job_id}"
        if self.job_id != expected_job_id:
            raise ValueError(
                f"job_id must be namespaced as '{expected_job_id}'"
            )

        if self.description.kind != DocumentKind.JOB:
            raise ValueError("description must have kind='job'")

        if any(
            document.document_id == self.description.document_id
            for document in self.source_documents
        ):
            raise ValueError(
                "description must not be duplicated in source_documents"
            )

        if self.last_seen_at < self.first_seen_at:
            raise ValueError("last_seen_at cannot be before first_seen_at")

        return self
