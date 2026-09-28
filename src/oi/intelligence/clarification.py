"""Apply a structured clarification answer to a candidate profile (CLAR-01).

This module turns the user's answer to an existing `ClarificationRequest`
into structured candidate data: one current `EligibilityAnswer` at the
request's canonical destination, backed by a clarification `SourceDocument`
and `EvidenceRef` in the profile's provenance. It is deterministic and never
calls a model.

It does not detect gaps, write questions or recompute eligibility/ranking;
those belong to later work. See
docs/agent/tasks/CLAR01_APPLY_CLARIFICATION_ANSWER.md.
"""

from __future__ import annotations

import hashlib
from typing import Any

from oi.contracts import (
    AnswerState,
    AnswerType,
    CandidateProfile,
    ClarificationRequest,
    DocumentKind,
    EligibilityAnswer,
    EvidenceRef,
    SourceDocument,
    eligibility_field_path_constraint_id,
)

#: Destinations this increment can write, with the answer type each takes.
#:
#: A deliberately small local allowlist, not a RuleCatalogue: it holds only
#: the answer key approved in D-040 and is to be replaced when the
#: RuleCatalogue exists. Do not add entries here without a new approval.
SUPPORTED_DESTINATIONS: dict[tuple[str, str], AnswerType] = {
    ("HC_MIN_EXPERIENCE", "has_corporate_finance_experience"): AnswerType.BOOLEAN,
}

#: `source_ref` recorded on every clarification answer document.
CLARIFICATION_SOURCE_REF = "clarification_answer"

#: Hex characters of the content hash used in a clarification document ID.
DOCUMENT_ID_HASH_PREFIX_LENGTH = 16

_BOOLEAN_ANSWER_TEXT = {True: "Yes", False: "No", None: "Unknown"}


class ClarificationAnswerError(ValueError):
    """The request is unsupported here or the answer does not fit it."""


def apply_clarification_answer(
    candidate: CandidateProfile,
    request: ClarificationRequest,
    answer: bool | None,
) -> CandidateProfile:
    """Return a new profile with `answer` applied as the current answer.

    The answer replaces any existing answer for the same constraint and
    answer key (upsert). Earlier provenance is kept and the new clarification
    document and evidence are added, so a correction stays traceable.

    Args:
        candidate: The current profile. Never mutated.
        request: The clarification being answered.
        answer: `True` or `False` for a known answer, `None` for an explicit
            "unknown". Nothing else is accepted or coerced.

    Returns:
        A new CandidateProfile, fully revalidated by the contract.

    Raises:
        ClarificationAnswerError: If the request's destination is not
            supported, is inconsistent, or the answer does not fit it.
    """
    constraint_id, answer_key = _supported_destination(request)
    _check_boolean_answer(answer)

    payload = candidate.model_dump()
    provenance = payload["provenance"]

    text = f"Question: {request.question}\nAnswer: {_BOOLEAN_ANSWER_TEXT[answer]}"
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    document_id = _next_document_id(
        provenance,
        f"clarification:{request.question_id}:"
        f"{content_hash[:DOCUMENT_ID_HASH_PREFIX_LENGTH]}",
    )
    document = SourceDocument(
        document_id=document_id,
        kind=DocumentKind.QUESTIONNAIRE,
        text=text,
        content_hash=content_hash,
        source_ref=CLARIFICATION_SOURCE_REF,
    )
    evidence = EvidenceRef(
        evidence_id=f"ev-{document_id}",
        document_id=document_id,
        quote=text,
        field_path=request.field_path,
    )
    new_answer = EligibilityAnswer(
        constraint_id=constraint_id,
        answer_key=answer_key,
        state=AnswerState.UNKNOWN if answer is None else AnswerState.KNOWN,
        answer_type=AnswerType.BOOLEAN,
        value=answer,
        evidence_ids=[evidence.evidence_id],
        source_document_id=document_id,
    )

    provenance["documents"][document_id] = document.model_dump()
    provenance["evidence"].append(evidence.model_dump())
    provenance["clarification_document_ids"].append(document_id)

    existing = payload["eligibility_answers"].get(constraint_id, [])
    payload["eligibility_answers"][constraint_id] = _upsert(
        existing, answer_key, new_answer.model_dump()
    )

    return CandidateProfile.model_validate(payload)


def _supported_destination(request: ClarificationRequest) -> tuple[str, str]:
    """Return (constraint_id, answer_key) for a request this module can apply."""

    field_path = request.field_path
    if field_path is None:
        raise ClarificationAnswerError(
            f"request '{request.question_id}' has no field_path destination"
        )

    path_constraint_id = eligibility_field_path_constraint_id(field_path)
    if path_constraint_id is None:
        raise ClarificationAnswerError(
            f"destination '{field_path}' is not supported by CLAR-01"
        )

    # The contract already enforces this; a request built without validation
    # must not slip past it here.
    if (
        request.constraint_id is not None
        and request.constraint_id != path_constraint_id
    ):
        raise ClarificationAnswerError(
            f"constraint_id '{request.constraint_id}' conflicts with "
            f"destination '{field_path}'"
        )

    answer_key = field_path.split(".")[2]
    expected_type = SUPPORTED_DESTINATIONS.get((path_constraint_id, answer_key))
    if expected_type is None:
        raise ClarificationAnswerError(
            f"destination '{field_path}' is not supported by CLAR-01"
        )

    if request.answer_type != expected_type:
        # Formatted as received: an unvalidated request may carry a value
        # that is not an AnswerType at all.
        received = getattr(request.answer_type, "value", request.answer_type)
        raise ClarificationAnswerError(
            f"destination '{field_path}' takes {expected_type.value} answers, "
            f"not {received!r}"
        )

    return path_constraint_id, answer_key


def _check_boolean_answer(answer: Any) -> None:
    # `type(...) is bool` keeps 1/0 out; strings and containers never coerce.
    if answer is not None and type(answer) is not bool:
        raise ClarificationAnswerError(
            "boolean clarification answers must be True, False or None, "
            f"not {type(answer).__name__} {answer!r}"
        )


def _next_document_id(provenance: dict[str, Any], base: str) -> str:
    """Return `<base>:<n>` for the smallest n >= 1 not yet used in provenance.

    Every application is its own provenance event, so answering the same
    question the same way again still gets a new document. The occurrence is
    derived only from what the profile already holds: deterministic, with no
    randomness or clock. A candidate is skipped if either its document ID or
    its evidence ID is taken.
    """

    evidence_ids = {item["evidence_id"] for item in provenance["evidence"]}
    occurrence = 1
    while True:
        document_id = f"{base}:{occurrence}"
        if (
            document_id not in provenance["documents"]
            and f"ev-{document_id}" not in evidence_ids
        ):
            return document_id
        occurrence += 1


def _upsert(
    answers: list[dict[str, Any]], answer_key: str, new_answer: dict[str, Any]
) -> list[dict[str, Any]]:
    """Make `new_answer` the only answer for its key, at the first old slot."""

    result: list[dict[str, Any]] = []
    placed = False
    for answer in answers:
        if answer["answer_key"] != answer_key:
            result.append(answer)
        elif not placed:
            result.append(new_answer)
            placed = True
    if not placed:
        result.append(new_answer)
    return result
