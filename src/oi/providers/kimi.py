"""Kimi (Moonshot AI) API adapter.

A transport boundary: authenticate, send the prompt, request structured
output, parse the reply. No application policy lives here -- provenance and
orchestration belong to `oi.intelligence`.

Kimi K3 is reached here through NVIDIA's OpenAI-compatible inference API, so
this uses the `openai` SDK pointed at NVIDIA's base URL rather than a bespoke
HTTP client. Pointing KIMI_BASE_URL/KIMI_MODEL elsewhere (for example at
Moonshot's own endpoint) works without code changes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from oi.contracts import CandidateProfile
from oi.providers.model_client import ExtractedFields, ExtractionError

#: NVIDIA's OpenAI-compatible inference endpoint.
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

#: Kimi K3 as served by NVIDIA. Override per-instance or via KIMI_MODEL.
DEFAULT_MODEL = "moonshotai/kimi-k3"

#: Extraction instructions live in version control as a reviewable file,
#: not inline, so prompt changes show up in diffs.
PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "prompts" / "candidate_extraction.md"
)


class KimiClient:
    """Thin client for candidate extraction via the Kimi API.

    Credentials are read from the environment at construction time. The caller
    loads any .env file beforehand; this class does not read one and keeps no
    global or module-level state.

    Args:
        api_key: Explicit key. Defaults to the KIMI_API_KEY environment
            variable, which is required if no key is passed.
        model_id: Model to call. Defaults to KIMI_MODEL, then DEFAULT_MODEL.
        base_url: API endpoint. Defaults to KIMI_BASE_URL, then
            DEFAULT_BASE_URL.

    Raises:
        RuntimeError: If no API key is available.
    """

    provider_name = "kimi"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        key = api_key or os.environ.get("KIMI_API_KEY")
        if not key:
            raise RuntimeError(
                "KIMI_API_KEY is not set. Export it, or copy .env.example to "
                ".env and load it before constructing KimiClient."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "The 'openai' package is required to talk to Kimi's "
                "OpenAI-compatible API. Install it with: "
                "pip install -r requirements.txt"
            ) from exc

        self.model_id = model_id or os.environ.get("KIMI_MODEL") or DEFAULT_MODEL
        self.base_url = (
            base_url or os.environ.get("KIMI_BASE_URL") or DEFAULT_BASE_URL
        )
        self._client = OpenAI(api_key=key, base_url=self.base_url)

    def _load_prompt(self) -> str:
        """Read the extraction instructions from the prompts directory."""
        try:
            return PROMPT_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            raise ExtractionError(
                f"Could not read the extraction prompt at {PROMPT_PATH}."
            ) from exc

    def extract_candidate_profile(self, document_text: str) -> CandidateProfile:
        """Ask Kimi to extract candidate facts from CV text.

        Args:
            document_text: The plain text of the candidate's CV.

        Returns:
            A CandidateProfile carrying the extracted fields. `candidate_id` is
            left empty and `extraction` is unset -- the caller assigns both.

        Raises:
            ValueError: If `document_text` is empty.
            ExtractionError: If the request fails, or the reply cannot be
                parsed into the expected structure.
        """
        if not document_text.strip():
            raise ValueError("Cannot extract a profile from empty document text.")

        from openai import OpenAIError

        try:
            response = self._client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": self._load_prompt()},
                    {"role": "user", "content": document_text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "candidate_fields",
                        "schema": ExtractedFields.model_json_schema(),
                        "strict": True,
                    },
                },
                temperature=0.0,
            )
        except OpenAIError as exc:
            raise ExtractionError(
                f"Kimi request failed for model '{self.model_id}': {exc}"
            ) from exc

        if not response.choices:
            raise ExtractionError("Kimi returned a response with no choices.")

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ExtractionError("Kimi returned an empty response body.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ExtractionError(
                f"Kimi did not return valid JSON. Raw text was: {content[:200]!r}"
            ) from exc

        try:
            fields = ExtractedFields.model_validate(payload)
        except ValidationError as exc:
            raise ExtractionError(
                f"Kimi response did not match the expected schema: {exc}"
            ) from exc

        return fields.to_profile()
