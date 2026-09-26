"""The provider-agnostic contract the intelligence layer depends on.

The pipeline talks to an LLM only through `ModelClient`. Anything vendor
-specific -- endpoints, SDKs, auth, response shapes -- lives behind an
implementation of this protocol, so swapping providers touches the provider
package and nothing else.

This module also holds the pieces every provider needs and none of them
should define privately: the schema the model is asked to fill in, the
extraction prompt, and the error type raised when a provider cannot deliver a
usable answer.

Providers return `ExtractedFields` or `ExtractedJobFields`, never a domain
contract. Turning model output into a `CandidateProfile` or an enriched
`JobRecord` -- verifying quotes, minting evidence ids, recording provenance --
is `oi.intelligence.extraction`'s and `oi.intelligence.job_extraction`'s job.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from oi.contracts import RequirementClassification, RequirementModality

#: Extraction instructions live in version control as a reviewable file,
#: not inline, so prompt changes show up in diffs.
_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
CANDIDATE_PROMPT_PATH = _PROMPTS_DIR / "candidate_extraction.md"
JOB_PROMPT_PATH = _PROMPTS_DIR / "job_extraction.md"


class ExtractionError(RuntimeError):
    """Raised when a provider request fails or returns an unusable response.

    Deliberately provider-neutral: callers handle extraction failure without
    knowing which vendor was behind it.
    """


@dataclass(frozen=True)
class Prompt:
    """Everything the model is given besides the document, plus its version.

    Providers send `text` as instructions and `schema` as the structured
    output format, so the version recorded in the ExtractionReceipt covers
    exactly what the model saw.
    """

    text: str
    schema: dict[str, Any]
    version: str


def model_input_version(text: str, schema: dict[str, Any]) -> str:
    """Hash prompt text and output schema into one deterministic version.

    Both are serialized as one canonical JSON document (sorted keys, fixed
    separators), so equal inputs always give equal versions and any edit to
    either -- including a field or description change in the schema --
    gives a new one.
    """
    canonical = json.dumps(
        {"prompt": text, "schema": schema},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def _load_prompt(path: Path, output: type[BaseModel]) -> Prompt:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExtractionError(
            f"Could not read the extraction prompt at {path}."
        ) from exc
    schema = output.model_json_schema()
    return Prompt(text=text, schema=schema, version=model_input_version(text, schema))


def load_candidate_prompt() -> Prompt:
    """Read the candidate extraction prompt and version it with its schema.

    Raises:
        ExtractionError: If the prompt file cannot be read.
    """
    return _load_prompt(CANDIDATE_PROMPT_PATH, ExtractedFields)


def load_job_prompt() -> Prompt:
    """Read the job extraction prompt and version it with its schema.

    Raises:
        ExtractionError: If the prompt file cannot be read.
    """
    return _load_prompt(JOB_PROMPT_PATH, ExtractedJobFields)


class ExtractedFact(BaseModel):
    """One fact the model read from the CV, with the text that supports it."""

    model_config = ConfigDict(extra="forbid")

    value: str = Field(description="The fact, kept close to the CV's wording.")
    quote: str = Field(
        description="A passage copied verbatim from the CV that states the fact."
    )


class ExtractedLanguage(BaseModel):
    """One human language the CV states, with the level as the CV writes it."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(
        description="ISO 639-1 code of the language, in lower case, e.g. 'en' or 'zh'."
    )
    level: str = Field(
        description="The proficiency exactly as the CV states it, e.g. 'C1', "
        "'HSK 4', 'JLPT N2', 'Fluent' or 'Native'; empty when none is stated."
    )
    quote: str = Field(
        description="A passage copied verbatim from the CV that states the "
        "language and its level."
    )


class ExtractedFields(BaseModel):
    """What a model is asked to produce from a CV -- and nothing more.

    Ids, evidence ids, timestamps and the extraction receipt are absent, so no
    model can populate its own identifiers or invent its own provenance; the
    application assigns those. Every field is required and extra keys are
    forbidden, which keeps the JSON schema valid for strict structured output.
    """

    model_config = ConfigDict(extra="forbid")

    skills: list[ExtractedFact]
    education: list[ExtractedFact]
    experience: list[ExtractedFact]
    languages: list[ExtractedLanguage]


class ExtractedJobFact(BaseModel):
    """One fact the model read from a job description, with its support."""

    model_config = ConfigDict(extra="forbid")

    value: str = Field(description="The fact, kept close to the posting's wording.")
    quote: str = Field(
        description="A passage copied verbatim from the posting that states the fact."
    )


class ExtractedRequirement(BaseModel):
    """One requirement the model read from a job description.

    Classification, modality and constraint id are the model's proposal. The
    intelligence layer decides whether a proposed hard constraint is allowed
    to stand.
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="The requirement, kept close to the posting's wording.")
    quote: str = Field(
        description="A passage copied verbatim from the posting that states it."
    )
    classification: RequirementClassification
    modality: RequirementModality
    constraint_id: str | None = Field(
        description="An approved constraint id for a hard constraint, else null."
    )


class ExtractedJobFields(BaseModel):
    """What a model is asked to produce from a job description -- and no more.

    As with `ExtractedFields`, ids, evidence ids and provenance are absent so
    the application assigns them. Every field is required and extra keys are
    forbidden, which keeps the JSON schema valid for strict structured output.
    """

    model_config = ConfigDict(extra="forbid")

    skills: list[ExtractedJobFact]
    experience: list[ExtractedJobFact]
    education: list[ExtractedJobFact]
    requirements: list[ExtractedRequirement]


@runtime_checkable
class ModelClient(Protocol):
    """What the intelligence layer requires of any LLM provider.

    Implementations are expected to:
      * read their own credentials (never receiving them from the caller),
      * expose the model actually used as `model_id`, for the receipt,
      * expose a short `provider_name` identifying the vendor,
      * raise ExtractionError on failure rather than returning empty data.
    """

    #: Identifier of the model used, recorded in the ExtractionReceipt.
    model_id: str

    #: Short vendor name (e.g. "kimi"), recorded in the ExtractionReceipt.
    provider_name: str

    def extract_candidate_fields(self, document_text: str) -> ExtractedFields:
        """Extract candidate facts, each with a supporting quote, from CV text.

        Raises:
            ValueError: If `document_text` is empty.
            ExtractionError: If the request fails or the reply is unusable.
        """
        ...

    def extract_job_fields(self, description_text: str) -> ExtractedJobFields:
        """Extract job facts and requirements, each with a quote, from a posting.

        Raises:
            ValueError: If `description_text` is empty.
            ExtractionError: If the request fails or the reply is unusable.
        """
        ...
