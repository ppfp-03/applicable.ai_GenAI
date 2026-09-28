"""Tests for the session storage of the extracted candidate profile."""

import pytest
import streamlit as st

from core import store
from oi.intelligence.extraction import extract_candidate
from tests.test_candidate_extraction import FakeModelClient, make_cv


@pytest.fixture(autouse=True)
def fresh_session():
    st.session_state.clear()
    store.init()
    yield
    st.session_state.clear()


def extracted(content_hash: str = "sha256-of-cv-bytes"):
    return extract_candidate(make_cv(content_hash=content_hash), FakeModelClient())


def test_init_starts_with_no_candidate_and_no_error() -> None:
    assert store.candidate() is None
    assert store.extraction_error() is None


def test_init_keeps_an_existing_candidate() -> None:
    profile = extracted()
    store.set_candidate(profile)

    store.init()

    assert store.candidate() is profile


def test_set_candidate_stores_the_profile() -> None:
    profile = extracted()

    store.set_candidate(profile)

    assert store.candidate() is profile
    assert store.extraction_error() is None


def test_set_candidate_clears_an_earlier_error() -> None:
    store.set_extraction_error("KIMI_API_KEY is not set.")

    store.set_candidate(extracted())

    assert store.extraction_error() is None


def test_set_extraction_error_stores_the_message_and_drops_the_profile() -> None:
    store.set_candidate(extracted())

    store.set_extraction_error("Kimi request failed.")

    assert store.extraction_error() == "Kimi request failed."
    assert store.candidate() is None


def test_has_candidate_for_matches_the_extraction_input_hash() -> None:
    store.set_candidate(extracted(content_hash="abc123"))

    assert store.has_candidate_for("abc123")
    assert not store.has_candidate_for("def456")


def test_has_candidate_for_is_false_without_a_profile() -> None:
    assert not store.has_candidate_for("abc123")
