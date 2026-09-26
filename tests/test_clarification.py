"""Tests for applying a structured clarification answer (CLAR-01)."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from oi.contracts import CandidateProfile, ClarificationRequest, EligibilityAnswer
from oi.intelligence.clarification import (
    ClarificationAnswerError,
    apply_clarification_answer,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "v0.2.0-draft"

CONSTRAINT_ID = "HC_MIN_EXPERIENCE"
ANSWER_KEY = "has_corporate_finance_experience"
FIELD_PATH = f"eligibility_answers.{CONSTRAINT_ID}.{ANSWER_KEY}"
QUESTION = "Have you worked in corporate finance?"


def load_candidate() -> CandidateProfile:
    """The shared candidate fixture, which has no HC_MIN_EXPERIENCE answer."""

    payload = json.loads((FIXTURE_ROOT / "candidate_profile.json").read_text())
    return CandidateProfile.model_validate(payload)


def make_request(**overrides: Any) -> ClarificationRequest:
    payload: dict[str, Any] = {
        "question_id": "clarify-corp-fin-001",
        "field_path": FIELD_PATH,
        "constraint_id": CONSTRAINT_ID,
        "question": QUESTION,
        "answer_type": "boolean",
        "allowed_choices": None,
        "reason": "The role requires prior corporate finance experience.",
        "job_ids": ["synthetic:job-001"],
        "evidence_ids": ["ev-job-experience-001"],
        "priority": "high",
    }
    payload.update(overrides)
    return ClarificationRequest(**payload)


def current_answers(profile: CandidateProfile) -> list[EligibilityAnswer]:
    return [
        answer
        for answer in profile.eligibility_answers.get(CONSTRAINT_ID, [])
        if answer.answer_key == ANSWER_KEY
    ]


def the_answer(profile: CandidateProfile) -> EligibilityAnswer:
    answers = current_answers(profile)
    assert len(answers) == 1
    return answers[0]


def with_questionnaire_false_answer() -> CandidateProfile:
    """Fixture profile that already records `False` from the questionnaire."""

    payload = load_candidate().model_dump(mode="json")
    payload["provenance"]["evidence"].append(
        {
            "evidence_id": "ev-questionnaire-corp-fin",
            "document_id": "questionnaire-001",
            "quote": "Synthetic onboarding questionnaire answers.",
            "field_path": FIELD_PATH,
        }
    )
    payload["eligibility_answers"][CONSTRAINT_ID] = [
        {
            "constraint_id": CONSTRAINT_ID,
            "answer_key": ANSWER_KEY,
            "state": "known",
            "answer_type": "boolean",
            "value": False,
            "evidence_ids": ["ev-questionnaire-corp-fin"],
            "source_document_id": "questionnaire-001",
        }
    ]
    return CandidateProfile.model_validate(payload)


# ─────────────────────────── Accepted answers ───────────────────────────


@pytest.mark.parametrize(
    ("answer", "state"),
    [(True, "known"), (False, "known"), (None, "unknown")],
)
def test_answer_is_written_at_the_canonical_destination(
    answer: bool | None, state: str
) -> None:
    updated = apply_clarification_answer(load_candidate(), make_request(), answer)

    written = the_answer(updated)
    assert written.constraint_id == CONSTRAINT_ID
    assert written.answer_key == ANSWER_KEY
    assert written.answer_type.value == "boolean"
    assert written.state.value == state
    assert written.value is answer


# ─────────────────────────────── Provenance ───────────────────────────────


@pytest.mark.parametrize(
    ("answer", "answer_text"), [(True, "Yes"), (False, "No"), (None, "Unknown")]
)
def test_answer_is_backed_by_resolvable_clarification_provenance(
    answer: bool | None, answer_text: str
) -> None:
    original = load_candidate()
    updated = apply_clarification_answer(original, make_request(), answer)
    provenance = updated.provenance
    written = the_answer(updated)

    document = provenance.documents[written.source_document_id]
    expected_text = f"Question: {QUESTION}\nAnswer: {answer_text}"
    expected_hash = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    assert document.kind.value == "questionnaire"
    assert document.source_ref == "clarification_answer"
    assert document.text == expected_text
    assert document.content_hash == expected_hash
    assert document.document_id == (
        f"clarification:clarify-corp-fin-001:{expected_hash[:16]}:1"
    )

    assert document.document_id in provenance.clarification_document_ids
    assert document.document_id not in provenance.questionnaire_document_ids

    evidence_by_id = {ref.evidence_id: ref for ref in provenance.evidence}
    assert len(written.evidence_ids) == 1
    evidence = evidence_by_id[written.evidence_ids[0]]
    assert evidence.document_id == document.document_id
    assert evidence.field_path == FIELD_PATH
    assert evidence.quote in document.text

    # Job-side evidence stays job-side.
    assert "ev-job-experience-001" not in evidence_by_id


# ────────────────────────────── Preservation ──────────────────────────────


def test_unrelated_profile_data_and_earlier_provenance_are_preserved() -> None:
    original = load_candidate()
    updated = apply_clarification_answer(original, make_request(), True)

    for field in ("schema_version", "candidate_id", "cv_document_id", "skills",
                  "education", "experience", "preferences", "declarations"):
        assert getattr(updated, field) == getattr(original, field)

    other_constraints = {
        key: value
        for key, value in updated.eligibility_answers.items()
        if key != CONSTRAINT_ID
    }
    assert other_constraints == original.eligibility_answers

    old, new = original.provenance, updated.provenance
    assert new.extraction == old.extraction
    assert new.questionnaire_document_ids == old.questionnaire_document_ids
    assert new.clarification_document_ids[:-1] == old.clarification_document_ids
    assert new.evidence[:-1] == old.evidence
    assert {key: new.documents[key] for key in old.documents} == old.documents
    assert len(new.documents) == len(old.documents) + 1


def test_input_profile_is_not_mutated() -> None:
    original = load_candidate()
    before = original.model_dump(mode="json")

    apply_clarification_answer(original, make_request(), True)

    assert original.model_dump(mode="json") == before


def test_result_survives_a_json_round_trip() -> None:
    updated = apply_clarification_answer(load_candidate(), make_request(), None)

    reloaded = CandidateProfile.model_validate_json(updated.model_dump_json())

    assert reloaded == updated
    assert the_answer(reloaded).value is None


# ───────────────────────────────── Upsert ─────────────────────────────────


def test_new_answer_replaces_existing_answer_and_keeps_old_provenance() -> None:
    original = with_questionnaire_false_answer()
    assert the_answer(original).value is False

    updated = apply_clarification_answer(original, make_request(), True)

    written = the_answer(updated)
    assert written.value is True
    assert written.source_document_id.startswith("clarification:")

    evidence_ids = {ref.evidence_id for ref in updated.provenance.evidence}
    assert "ev-questionnaire-corp-fin" in evidence_ids
    assert written.evidence_ids[0] in evidence_ids
    assert "questionnaire-001" in updated.provenance.documents
    assert written.source_document_id in updated.provenance.documents


def test_correcting_a_clarification_keeps_both_clarification_documents() -> None:
    first = apply_clarification_answer(load_candidate(), make_request(), False)
    second = apply_clarification_answer(first, make_request(), True)

    old_document_id = the_answer(first).source_document_id
    new_document_id = the_answer(second).source_document_id
    assert new_document_id != old_document_id
    assert the_answer(second).value is True
    assert old_document_id in second.provenance.documents
    assert {old_document_id, new_document_id} <= set(
        second.provenance.clarification_document_ids
    )


def test_true_false_true_records_three_distinct_provenance_events() -> None:
    base = load_candidate()
    snapshots = [base.model_dump(mode="json")]

    first = apply_clarification_answer(base, make_request(), True)
    snapshots.append(first.model_dump(mode="json"))
    second = apply_clarification_answer(first, make_request(), False)
    snapshots.append(second.model_dump(mode="json"))
    third = apply_clarification_answer(second, make_request(), True)

    # One active structured answer, carrying the final value.
    written = the_answer(third)
    assert written.value is True
    assert written.state.value == "known"

    document_ids = [
        the_answer(profile).source_document_id for profile in (first, second, third)
    ]
    evidence_ids = [
        the_answer(profile).evidence_ids[0] for profile in (first, second, third)
    ]
    assert len(set(document_ids)) == 3
    assert len(set(evidence_ids)) == 3

    # The two True answers share content, so they differ only by occurrence.
    true_hash = hashlib.sha256(
        f"Question: {QUESTION}\nAnswer: Yes".encode("utf-8")
    ).hexdigest()[:16]
    assert document_ids[0] == f"clarification:clarify-corp-fin-001:{true_hash}:1"
    assert document_ids[2] == f"clarification:clarify-corp-fin-001:{true_hash}:2"

    # The current answer points at the third application's provenance.
    assert written.source_document_id == document_ids[2]
    assert written.evidence_ids == [evidence_ids[2]]
    assert document_ids[2] not in second.provenance.documents

    provenance = third.provenance
    evidence_by_id = {ref.evidence_id: ref for ref in provenance.evidence}
    base_ids = base.provenance.clarification_document_ids
    assert provenance.clarification_document_ids == base_ids + document_ids
    for document_id, evidence_id in zip(document_ids, evidence_ids):
        document = provenance.documents[document_id]
        evidence = evidence_by_id[evidence_id]
        assert evidence.document_id == document_id
        assert evidence.quote in document.text

    # Every earlier profile instance is untouched.
    for profile, before in zip((base, first, second), snapshots):
        assert profile.model_dump(mode="json") == before


def test_occurrence_whose_evidence_id_is_taken_is_skipped() -> None:
    yes_hash = hashlib.sha256(
        f"Question: {QUESTION}\nAnswer: Yes".encode("utf-8")
    ).hexdigest()[:16]
    first_id = f"clarification:clarify-corp-fin-001:{yes_hash}:1"

    # Occurrence 1's document ID is free, but its evidence ID is already used
    # by an unrelated entry, which must survive untouched.
    payload = load_candidate().model_dump(mode="json")
    squatter = {
        "evidence_id": f"ev-{first_id}",
        "document_id": "questionnaire-001",
        "quote": "Synthetic onboarding questionnaire answers.",
        "field_path": "skills",
    }
    payload["provenance"]["evidence"].append(squatter)
    profile = CandidateProfile.model_validate(payload)
    assert first_id not in profile.provenance.documents

    updated = apply_clarification_answer(profile, make_request(), True)

    written = the_answer(updated)
    assert written.source_document_id == (
        f"clarification:clarify-corp-fin-001:{yes_hash}:2"
    )
    assert written.evidence_ids == [f"ev-{written.source_document_id}"]
    assert first_id not in updated.provenance.documents
    evidence_by_id = {ref.evidence_id: ref for ref in updated.provenance.evidence}
    assert evidence_by_id[f"ev-{first_id}"].model_dump() == squatter


# ─────────────────────────────── Rejections ───────────────────────────────


@pytest.mark.parametrize(
    "answer", [1, 0, "yes", "no", "true", "false", [True], {"value": True}, 1.0]
)
def test_non_canonical_answer_values_are_rejected(answer: Any) -> None:
    original = load_candidate()

    with pytest.raises(ClarificationAnswerError):
        apply_clarification_answer(original, make_request(), answer)


@pytest.mark.parametrize(
    "overrides",
    [
        {"field_path": "preferences.preferred_industries", "constraint_id": None},
        {
            "field_path": "declarations.work_authorizations.GB.requires_sponsorship",
            "constraint_id": None,
        },
        {"field_path": f"eligibility_answers.{CONSTRAINT_ID}.years_of_experience"},
        {
            "field_path": "eligibility_answers.HC_GRAD_WINDOW.expected_graduation_date",
            "constraint_id": "HC_GRAD_WINDOW",
        },
        {"field_path": None},
    ],
)
def test_unsupported_destinations_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ClarificationAnswerError):
        apply_clarification_answer(load_candidate(), make_request(**overrides), True)


def test_constraint_destination_mismatch_is_rejected_by_contract() -> None:
    with pytest.raises(ValidationError):
        make_request(constraint_id="HC_GRAD_WINDOW")


def test_constraint_destination_mismatch_is_rejected_by_engine() -> None:
    valid = make_request()
    unchecked = ClarificationRequest.model_construct(
        **{**valid.model_dump(), "constraint_id": "HC_GRAD_WINDOW"}
    )

    with pytest.raises(ClarificationAnswerError):
        apply_clarification_answer(load_candidate(), unchecked, True)


@pytest.mark.parametrize(
    "overrides",
    [
        {"answer_type": "text"},
        {"answer_type": "single_choice", "allowed_choices": ["yes", "no"]},
    ],
)
def test_wrong_answer_type_for_destination_is_rejected(
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(ClarificationAnswerError):
        apply_clarification_answer(load_candidate(), make_request(**overrides), True)


def test_unvalidated_invalid_answer_type_is_rejected_by_engine() -> None:
    valid = make_request()
    unchecked = ClarificationRequest.model_construct(
        **{**valid.model_dump(), "answer_type": "bogus"}
    )

    with pytest.raises(ClarificationAnswerError, match="'bogus'"):
        apply_clarification_answer(load_candidate(), unchecked, True)
