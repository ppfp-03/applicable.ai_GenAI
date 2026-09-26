"""Orchestration for candidate extraction.

This module owns the application-side flow: it takes an ingested CV, hands
its text to a model client, and turns the reply into a contract-valid
CandidateProfile.

The provider it calls is a transport detail. Everything here that constitutes
a decision -- which facts are backed by the document, which ids they carry,
what the receipt records, when the work happened -- is made in this layer,
not in the provider.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

from oi.contracts import (
    CONTRACT_VERSION,
    CandidatePreferences,
    CandidateProfile,
    CandidateProvenance,
    DocumentKind,
    EvidenceRef,
    ExtractionMode,
    ExtractionReceipt,
    SourceDocument,
    SupportedText,
    UserDeclarations,
)
from oi.providers.model_client import (
    ExtractedFact,
    ModelClient,
    load_candidate_prompt,
)

logger = logging.getLogger(__name__)

#: Profile fields filled from the CV, with the short name used in evidence ids.
CV_FIELDS = (
    ("skills", "skill"),
    ("education", "education"),
    ("experience", "experience"),
)


def extract_candidate(
    document: SourceDocument,
    model_client: ModelClient,
) -> CandidateProfile:
    """Extract an evidence-backed candidate profile from an ingested CV.

    Flow: SourceDocument -> model client -> quote check -> CandidateProfile.

    A fact survives only if its quote can be found in the document. Each
    surviving fact gets an EvidenceRef holding the quote exactly as it appears
    in the document, and an ExtractionReceipt records how the profile was
    produced. Everything the CV cannot tell us (preferences, declarations,
    eligibility answers) starts empty for the questionnaire to fill.

    Args:
        document: An ingested CV, as produced by `oi.io.pdf.extract_pdf_text`.
        model_client: The client used to perform the extraction.

    Returns:
        A CandidateProfile that passes contract validation.

    Raises:
        ValueError: If the document is not a CV or carries no text.
        ExtractionError: Propagated from the provider when the request fails
            or the response cannot be parsed. Never swallowed -- a failed
            extraction must not look like an empty profile.
    """
    if document.kind is not DocumentKind.CV:
        raise ValueError(
            f"Document '{document.document_id}' has kind '{document.kind.value}', "
            "not 'cv'."
        )
    if not document.text.strip():
        raise ValueError(
            f"Document '{document.document_id}' has no text to extract from."
        )

    prompt = load_candidate_prompt()

    started = time.perf_counter()
    fields = model_client.extract_candidate_fields(document.text)
    latency_ms = round((time.perf_counter() - started) * 1000)

    evidence: list[EvidenceRef] = []
    supported: dict[str, list[SupportedText]] = {}
    for field_name, short_name in CV_FIELDS:
        supported[field_name] = []
        for fact in getattr(fields, field_name):
            quote = _find_quote(fact, document.text)
            if quote is None:
                logger.warning(
                    "Dropped %s fact %r from '%s': quote not found in document.",
                    field_name,
                    fact.value,
                    document.document_id,
                )
                continue
            evidence_id = (
                f"ev-{document.document_id}-{short_name}-"
                f"{len(supported[field_name]) + 1:03d}"
            )
            evidence.append(
                EvidenceRef(
                    evidence_id=evidence_id,
                    document_id=document.document_id,
                    quote=quote,
                    field_path=field_name,
                )
            )
            supported[field_name].append(
                SupportedText(value=fact.value.strip(), evidence_ids=[evidence_id])
            )

    receipt = ExtractionReceipt(
        mode=ExtractionMode.LIVE,
        provider=model_client.provider_name,
        model_id=model_client.model_id,
        prompt_version=prompt.version,
        schema_version=CONTRACT_VERSION,
        input_hash=document.content_hash,
        produced_at=datetime.now(timezone.utc),
        latency_ms=latency_ms,
    )

    return CandidateProfile(
        schema_version=CONTRACT_VERSION,
        candidate_id=document.document_id,
        cv_document_id=document.document_id,
        skills=supported["skills"],
        education=supported["education"],
        experience=supported["experience"],
        preferences=CandidatePreferences(
            preferred_country_codes=[],
            preferred_role_families=[],
            preferred_industries=[],
        ),
        declarations=UserDeclarations(
            additional_citizenships=[],
            work_authorizations=[],
        ),
        eligibility_answers={},
        provenance=CandidateProvenance(
            questionnaire_document_ids=[],
            clarification_document_ids=[],
            documents={document.document_id: document},
            evidence=evidence,
            extraction=receipt,
        ),
    )


def _find_quote(fact: ExtractedFact, text: str) -> str | None:
    """Locate a fact's quote in the document and return it verbatim.

    Matching tolerates differences in whitespace only: PDF text breaks lines
    mid-sentence, and a model quoting it will usually join them. Every other
    character must match exactly. The returned quote is the document's own
    span, so it can be highlighted in the source later.

    Returns None when the fact or its quote is blank, or the quote is absent.
    """
    if not fact.value.strip():
        return None
    words = fact.quote.split()
    if not words:
        return None
    match = re.search(r"\s+".join(map(re.escape, words)), text)
    return match.group(0) if match else None
