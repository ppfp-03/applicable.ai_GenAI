"""The user's edits to the profile read from the CV, and their provenance (FR-02)."""

import pytest
import streamlit as st

from core import store
from oi.contracts import CandidateProfile, DocumentKind
from oi.intelligence.extraction import extract_candidate
from oi.providers.model_client import ExtractedLanguage
from tests.test_candidate_extraction import FakeModelClient, fact, make_cv, make_fields

CV = "cv-001"
MSC = "MSc Finance, Bocconi University"
ANALYST = "Summer Analyst at Mediobanco"


def profile(**fields) -> CandidateProfile:
    return extract_candidate(make_cv(), FakeModelClient(fields=make_fields(**fields)))


def sources(p: CandidateProfile, field: str) -> list[tuple[str, str]]:
    """Each value of a section with the document its evidence comes from."""
    docs = {e.evidence_id: e.document_id for e in p.provenance.evidence}
    return [(v.value, docs[v.evidence_ids[0]]) for v in getattr(p, field)]


def test_unchanged_values_keep_their_cv_evidence() -> None:
    before = profile()

    after = store.apply_edits(before, {"skills": ["Python"], "education": [MSC], "experience": [ANALYST]})

    assert after == before
    assert after.provenance.questionnaire_document_ids == []


def test_edited_and_added_values_are_backed_by_the_users_own_document() -> None:
    after = store.apply_edits(profile(), {"experience": [ANALYST, "Intern at Acme, 2024"], "education": ["MSc Finance"]})

    assert sources(after, "experience") == [(ANALYST, CV), ("Intern at Acme, 2024", "profile-edit-1")]
    assert sources(after, "education") == [("MSc Finance", "profile-edit-1")]
    assert sources(after, "skills") == [("Python", CV)]
    doc = after.provenance.documents["profile-edit-1"]
    assert doc.kind is DocumentKind.QUESTIONNAIRE
    assert after.provenance.questionnaire_document_ids == ["profile-edit-1"]
    quotes = {e.quote for e in after.provenance.evidence if e.document_id == "profile-edit-1"}
    assert quotes == {"Intern at Acme, 2024", "MSc Finance"}


def test_edits_keep_the_languages_read_from_the_cv() -> None:
    text = make_cv().text + "German C1\n"
    fields = make_fields(languages=[ExtractedLanguage(language="de", level="C1", quote="German C1")])
    before = extract_candidate(make_cv(text), FakeModelClient(fields=fields))

    after = store.apply_edits(before, {"skills": []})

    assert after.eligibility_answers == before.eligibility_answers
    (answer,) = after.eligibility_answers["HC_LANGUAGE"]
    assert answer.evidence_ids[0] in {e.evidence_id for e in after.provenance.evidence}


def test_removed_values_leave_no_evidence_behind() -> None:
    after = store.apply_edits(profile(), {"education": []})

    assert after.education == []
    assert {e.field_path for e in after.provenance.evidence} == {"skills", "experience"}


def test_blank_values_are_dropped_and_whitespace_collapsed() -> None:
    after = store.apply_edits(profile(), {"skills": ["Python", "  ", "", "  SQL   and  dbt "]})

    assert [v.value for v in after.skills] == ["Python", "SQL and dbt"]


def test_edit_documents_nothing_refers_to_are_dropped() -> None:
    first = store.apply_edits(profile(), {"skills": ["Python", "SQL"]})

    second = store.apply_edits(first, {"skills": ["Python", "Excel"]})

    assert sources(second, "skills") == [("Python", CV), ("Excel", "profile-edit-2")]
    assert set(second.provenance.documents) == {CV, "profile-edit-2"}
    assert second.provenance.questionnaire_document_ids == ["profile-edit-2"]


def test_earlier_edits_that_are_kept_keep_their_document() -> None:
    first = store.apply_edits(profile(), {"skills": ["Python", "SQL"]})

    second = store.apply_edits(first, {"skills": ["Python", "SQL", "Excel"]})

    assert sources(second, "skills") == [("Python", CV), ("SQL", "profile-edit-1"), ("Excel", "profile-edit-2")]
    assert store.is_edited(second, second.skills[1])
    assert not store.is_edited(second, second.skills[0])


def test_several_experiences_stay_distinct_entries() -> None:
    p = profile(experience=[fact(ANALYST, "Summer Analyst, Mediobanco, June-August 2025"), fact("Tutor", "Giulia Rossi")])

    after = store.apply_edits(p, {"experience": [ANALYST, "Tutor", "Intern at Acme"]})

    assert [v.value for v in after.experience] == [ANALYST, "Tutor", "Intern at Acme"]


@pytest.fixture
def session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def test_save_edits_replaces_the_stored_profile(session) -> None:
    store.set_candidate(profile())

    store.save_edits({"skills": ["Python", "SQL"]})

    assert [v.value for v in store.candidate().skills] == ["Python", "SQL"]


@pytest.mark.parametrize(
    ("value", "parts"),
    [
        ("MSc in International Management · Fudan University · Sep 2025 – Jul 2027",
         ("MSc in International Management", "Fudan University", "Sep 2025 – Jul 2027")),
        ("Analyst · Acme", ("Analyst", "Acme", "")),
        ("Analyst · 2024", ("Analyst", "", "2024")),
        ("Analyst", ("Analyst", "", "")),
        ("", ("", "", "")),
        # Not in the format: kept whole, for the user to split.
        ("Personal Consultant, UniCredit S.p.A., Apr 2025 – Jul 2025",
         ("Personal Consultant, UniCredit S.p.A., Apr 2025 – Jul 2025", "", "")),
        ("a · b · c · 2024", ("a · b · c · 2024", "", "")),
    ],
)
def test_split_entry(value, parts) -> None:
    assert store.split_entry(value) == parts


def test_join_entry_leaves_out_parts_not_stated() -> None:
    assert store.join_entry(" Analyst ", "", "2024") == "Analyst · 2024"
    assert store.join_entry("", "", "  ") == ""
    value = "MSc · Fudan University · Sep 2025 – Jul 2027"
    assert store.join_entry(*store.split_entry(value)) == value
