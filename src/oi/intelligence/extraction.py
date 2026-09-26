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
    AnswerState,
    AnswerType,
    CandidatePreferences,
    CandidateProfile,
    CandidateProvenance,
    DocumentKind,
    EligibilityAnswer,
    EvidenceRef,
    ExtractionMode,
    ExtractionReceipt,
    SourceDocument,
    SupportedText,
    UserDeclarations,
)
from oi.intelligence.eligibility.catalogue import (
    LANGUAGE_CONSTRAINT_ID,
    LANGUAGE_SCALES,
    LanguageLevel,
    language_level_key,
)
from oi.providers.model_client import (
    ExtractedLanguage,
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

#: An ISO 639-1 language code, as the prompt asks the model to write it.
LANGUAGE_CODE = re.compile(r"^[a-z]{2}$")


def _level_pattern(level: LanguageLevel) -> re.Pattern[str]:
    """How a CV writes `level`: "C1", "HSK 4", "N2", "fluent", "native"."""
    if level.scale == "HSK":
        body = rf"HSK\s*-?\s*(?:level\s*)?{level.level}"
    elif level == LanguageLevel("SELF", "native"):
        body = r"(?<!non-)(?<!non )native"
    else:
        body = re.escape(level.level)
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


#: Every supported level, with the pattern that recognises it in text.
LEVEL_PATTERNS = {
    level: _level_pattern(level)
    for level in (
        LanguageLevel(scale, name)
        for scale, names in LANGUAGE_SCALES.items()
        for name in names
    )
}


def extract_candidate(
    document: SourceDocument,
    model_client: ModelClient,
) -> CandidateProfile:
    """Extract an evidence-backed candidate profile from an ingested CV.

    Flow: SourceDocument -> model client -> quote check -> CandidateProfile.

    A fact survives only if its quote can be found in the document. Each
    surviving fact gets an EvidenceRef holding the quote exactly as it appears
    in the document, and an ExtractionReceipt records how the profile was
    produced. Each language the CV states becomes an HC_LANGUAGE answer,
    known when its level can be read (`_read_level`) and unknown otherwise.
    Everything the CV cannot tell us (preferences, declarations, other
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
            quote = _find_quote(fact.value, fact.quote, document.text)
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

    languages = _language_answers(fields.languages, document, evidence)

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
        eligibility_answers={LANGUAGE_CONSTRAINT_ID: languages} if languages else {},
        provenance=CandidateProvenance(
            questionnaire_document_ids=[],
            clarification_document_ids=[],
            documents={document.document_id: document},
            evidence=evidence,
            extraction=receipt,
        ),
    )


def _language_answers(
    stated: list[ExtractedLanguage],
    document: SourceDocument,
    evidence: list[EvidenceRef],
) -> list[EligibilityAnswer]:
    """HC_LANGUAGE answers for the languages the CV states, sourced to the CV.

    A language survives only with a valid ISO 639-1 code and a quote found in
    the document; its EvidenceRef is appended to `evidence`. The level keeps
    the scale it was stated on.
    """
    answers: list[EligibilityAnswer] = []
    for language in stated:
        code = language.language.strip().lower()
        quote = _find_quote(code, language.quote, document.text)
        if not LANGUAGE_CODE.match(code) or quote is None:
            logger.warning(
                "Dropped language %r from '%s': invalid code or quote not found "
                "in document.",
                language.language,
                document.document_id,
            )
            continue
        key = language_level_key(code)
        evidence_id = f"ev-{document.document_id}-language-{len(answers) + 1:03d}"
        evidence.append(
            EvidenceRef(
                evidence_id=evidence_id,
                document_id=document.document_id,
                quote=quote,
                field_path=f"eligibility_answers.{LANGUAGE_CONSTRAINT_ID}.{key}",
            )
        )
        level = _read_level(language.level, quote)
        answers.append(
            EligibilityAnswer(
                constraint_id=LANGUAGE_CONSTRAINT_ID,
                answer_key=key,
                state=AnswerState.KNOWN if level else AnswerState.UNKNOWN,
                answer_type=AnswerType.SINGLE_CHOICE,
                value=level.code if level else None,
                evidence_ids=[evidence_id],
                source_document_id=document.document_id,
            )
        )
    return answers


def _read_level(level_text: str, quote: str) -> LanguageLevel | None:
    """The one supported level `level_text` names, if the quote states it too.

    A level on a named scale (CEFR, HSK, JLPT) wins over "fluent" or "native"
    stated beside it. Anything else -- no level, several levels, a level the
    CV does not state in the quote, a scale outside LANGUAGE_SCALES -- reads
    as None: an unknown level is never mapped onto a known one.
    """
    found = [level for level, pattern in LEVEL_PATTERNS.items() if pattern.search(level_text)]
    named = [level for level in found if level.scale != "SELF"] or found
    if len(named) != 1:
        return None
    (level,) = named
    return level if LEVEL_PATTERNS[level].search(quote) else None


def _find_quote(value: str, quote: str, text: str) -> str | None:
    """Locate a fact's quote in the document and return it verbatim.

    Matching tolerates differences in whitespace only: PDF text breaks lines
    mid-sentence, and a model quoting it will usually join them. Every other
    character must match exactly. The returned quote is the document's own
    span, so it can be highlighted in the source later.

    Returns None when the fact or its quote is blank, or the quote is absent.
    """
    if not value.strip():
        return None
    words = quote.split()
    if not words:
        return None
    match = re.search(r"\s+".join(map(re.escape, words)), text)
    return match.group(0) if match else None
