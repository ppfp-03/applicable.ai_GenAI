"""Gemini API adapter.

This module is a transport boundary and nothing more. It knows how to talk to
the Gemini API: authenticate, send a prompt, ask for structured output, and
turn the reply into contract objects. It holds no application policy -- no
provenance stamping, no orchestration, no decisions about what to do with a
result. That lives in `oi.intelligence`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError

from oi.contracts import CandidateProfile

#: Default model. Overridable per-instance, or via GEMINI_MODEL.
DEFAULT_MODEL = "gemini-2.5-flash"

#: The extraction instructions, kept in version control as a reviewable file
#: rather than inline, so prompt changes show up in diffs.
PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "prompts" / "candidate_extraction.md"
)


class _ExtractedFields(BaseModel):
    """The subset of a candidate profile the model is asked to produce.

    Deliberately narrower than CandidateProfile: the model is given no way to
    populate `candidate_id`, `evidence` or `extraction`. Those are assigned by
    the application, so the model cannot invent its own provenance.
    """

    name: Optional[str] = None
    skills: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    languages: list[str] = []


class GeminiExtractionError(RuntimeError):
    """Raised when a Gemini request fails or returns an unusable response."""


class GeminiClient:
    """Thin client for candidate extraction via the Gemini API.

    The API key is read from the environment at construction time. The caller
    is responsible for loading any .env file beforehand -- this class does not
    read one, and keeps no global or module-level state.

    Args:
        api_key: Explicit key. Defaults to the GEMINI_API_KEY environment
            variable.
        model_id: Model to call. Defaults to GEMINI_MODEL, then DEFAULT_MODEL.

    Raises:
        RuntimeError: If no API key is available.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Export it, or copy .env.example to "
                ".env and load it before constructing GeminiClient."
            )

        from google import genai

        self.model_id = model_id or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
        self._client = genai.Client(api_key=key)

    def _load_prompt(self) -> str:
        """Read the extraction instructions from the prompts directory."""
        try:
            return PROMPT_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            raise GeminiExtractionError(
                f"Could not read the extraction prompt at {PROMPT_PATH}."
            ) from exc

    def extract_candidate_profile(self, document_text: str) -> CandidateProfile:
        """Ask Gemini to extract candidate facts from CV text.

        Args:
            document_text: The plain text of the candidate's CV.

        Returns:
            A CandidateProfile carrying the extracted fields. `candidate_id` is
            left empty and `extraction` is unset -- the caller assigns both.

        Raises:
            ValueError: If `document_text` is empty.
            GeminiExtractionError: If the request fails, or the reply cannot be
                parsed into the expected structure.
        """
        if not document_text.strip():
            raise ValueError("Cannot extract a profile from empty document text.")

        from google.genai import errors as genai_errors
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=self._load_prompt(),
            response_mime_type="application/json",
            response_schema=_ExtractedFields,
            temperature=0.0,
        )

        try:
            response = self._client.models.generate_content(
                model=self.model_id,
                contents=document_text,
                config=config,
            )
        except genai_errors.APIError as exc:
            raise GeminiExtractionError(
                f"Gemini request failed for model '{self.model_id}': {exc}"
            ) from exc

        parsed = response.parsed
        if parsed is None:
            raise GeminiExtractionError(
                "Gemini returned no parsable structured output. Raw text was: "
                f"{(response.text or '')[:200]!r}"
            )

        try:
            fields = _ExtractedFields.model_validate(parsed)
        except ValidationError as exc:
            raise GeminiExtractionError(
                f"Gemini response did not match the expected schema: {exc}"
            ) from exc

        return CandidateProfile(
            candidate_id="",
            name=fields.name,
            skills=fields.skills,
            education=fields.education,
            experience=fields.experience,
            languages=fields.languages,
        )
