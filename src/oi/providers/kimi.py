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
from typing import Any, Optional

from pydantic import ValidationError

from oi.providers.model_client import (
    ExtractedFields,
    ExtractionError,
    load_candidate_prompt,
)

#: NVIDIA's OpenAI-compatible inference endpoint.
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

#: Kimi K3 as served by NVIDIA. Override per-instance or via KIMI_MODEL.
DEFAULT_MODEL = "moonshotai/kimi-k3"

#: Seconds before a single HTTP request is abandoned. Extraction of a
#: one-page CV has been observed to take 60-90s, occasionally longer.
REQUEST_TIMEOUT_SECONDS = 120.0

#: How many times a reply with no content is requested before giving up.
#: The NVIDIA endpoint sometimes returns HTTP 200 with finish_reason "stop"
#: and content null (a degenerate generation); asking again usually works.
#: Only that case is retried here -- HTTP errors are left to the SDK's own
#: retries, so the two never multiply.
MAX_ATTEMPTS = 3


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
        self._client = OpenAI(
            api_key=key, base_url=self.base_url, timeout=REQUEST_TIMEOUT_SECONDS
        )

    def extract_candidate_fields(self, document_text: str) -> ExtractedFields:
        """Ask Kimi to extract candidate facts, with quotes, from CV text.

        Args:
            document_text: The plain text of the candidate's CV.

        Returns:
            The model's facts, each paired with the quote it claims supports
            it. Quotes are unverified here; the caller checks them.

        Raises:
            ValueError: If `document_text` is empty.
            ExtractionError: If the request fails, every attempt comes back
                empty, or the reply cannot be parsed into the expected
                structure.
        """
        if not document_text.strip():
            raise ValueError("Cannot extract a profile from empty document text.")

        from openai import OpenAIError

        prompt = load_candidate_prompt()
        for _ in range(MAX_ATTEMPTS):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {"role": "system", "content": prompt.text},
                        {"role": "user", "content": document_text},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "candidate_fields",
                            "schema": prompt.schema,
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
            if content and content.strip():
                break
        else:
            raise ExtractionError(
                f"Kimi returned an empty response body on all {MAX_ATTEMPTS} "
                f"attempts ({_empty_reply_diagnostics(response)})."
            )

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ExtractionError(
                f"Kimi did not return valid JSON. Raw text was: {content[:200]!r}"
            ) from exc

        try:
            return ExtractedFields.model_validate(payload)
        except ValidationError as exc:
            raise ExtractionError(
                f"Kimi response did not match the expected schema: {exc}"
            ) from exc


def _empty_reply_diagnostics(response: Any) -> str:
    """Describe an empty reply without repeating any model output.

    Reports only metadata -- never the content or reasoning text, which could
    echo the CV back into logs and error messages.
    """
    choice = response.choices[0]
    usage = getattr(response, "usage", None)
    tokens = getattr(usage, "completion_tokens", None)
    reasoning = getattr(choice.message, "reasoning_content", None)
    return (
        f"last attempt: finish_reason={getattr(choice, 'finish_reason', None)!r}, "
        f"completion_tokens={'unknown' if tokens is None else tokens}, "
        f"reasoning_content={'present' if reasoning else 'absent'}"
    )
