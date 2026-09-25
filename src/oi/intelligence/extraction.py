"""Orchestration for candidate extraction.

This module owns the application-side flow: it takes an ingested document,
hands its text to a model client, and stamps the result with provenance.

The provider it calls is a transport detail. Everything here that constitutes
a decision -- which id the profile carries, what the receipt records, when the
work happened -- is made in this layer, not in the provider.
"""

from __future__ import annotations

from datetime import datetime, timezone

from oi.contracts import CandidateProfile, ExtractionReceipt, SourceDocument
from oi.providers.model_client import ModelClient


def extract_candidate(
    document: SourceDocument,
    model_client: ModelClient,
) -> CandidateProfile:
    """Extract a candidate profile from an ingested document.

    Flow: SourceDocument -> model client -> CandidateProfile.

    The document's identity carries over to the profile, and an
    ExtractionReceipt records how the profile was produced, so a downstream
    reader can tell a live model extraction from any other origin.

    Args:
        document: An ingested document, as produced by `oi.io.document_loader`.
        model_client: The client used to perform the extraction.

    Returns:
        A CandidateProfile with `candidate_id` set from the document and
        `extraction` populated.

    Raises:
        ValueError: If the document carries no text.
        ExtractionError: Propagated from the provider when the request fails
            or the response cannot be parsed. Never swallowed -- a failed
            extraction must not look like an empty profile.
    """
    if not document.text.strip():
        raise ValueError(
            f"Document '{document.document_id}' has no text to extract from."
        )

    profile = model_client.extract_candidate_profile(document.text)

    profile.candidate_id = document.document_id
    profile.extraction = ExtractionReceipt(
        mode="live",
        provider=getattr(model_client, "provider_name", "unknown"),
        model_id=getattr(model_client, "model_id", None),
        produced_at=datetime.now(timezone.utc).isoformat(),
    )

    return profile
