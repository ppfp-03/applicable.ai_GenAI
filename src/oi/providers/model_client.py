"""The provider-agnostic contract the intelligence layer depends on.

The pipeline talks to an LLM only through `ModelClient`. Anything vendor
-specific -- endpoints, SDKs, auth, response shapes -- lives behind an
implementation of this protocol, so swapping providers touches the provider
package and nothing else.

This module also holds the two pieces every provider needs and none of them
should define privately: the schema the model is asked to fill in, and the
error type raised when a provider cannot deliver a usable answer.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel

from oi.contracts import CandidateProfile


class ExtractionError(RuntimeError):
    """Raised when a provider request fails or returns an unusable response.

    Deliberately provider-neutral: callers handle extraction failure without
    knowing which vendor was behind it.
    """


class ExtractedFields(BaseModel):
    """The subset of a candidate profile a model is asked to produce.

    Narrower than CandidateProfile on purpose. `candidate_id`, `evidence` and
    `extraction` are absent, so no model can populate its own identifiers or
    invent its own provenance -- the application assigns those.
    """

    name: Optional[str] = None
    skills: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    languages: list[str] = []

    def to_profile(self) -> CandidateProfile:
        """Build an un-stamped CandidateProfile from these fields.

        `candidate_id` is left empty and `extraction` unset; the orchestration
        layer fills both in.
        """
        return CandidateProfile(
            candidate_id="",
            name=self.name,
            skills=self.skills,
            education=self.education,
            experience=self.experience,
            languages=self.languages,
        )


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

    def extract_candidate_profile(self, document_text: str) -> CandidateProfile:
        """Extract candidate facts from CV text.

        Returns a CandidateProfile with `candidate_id` empty and `extraction`
        unset -- provenance is the caller's responsibility.

        Raises:
            ValueError: If `document_text` is empty.
            ExtractionError: If the request fails or the reply is unusable.
        """
        ...
