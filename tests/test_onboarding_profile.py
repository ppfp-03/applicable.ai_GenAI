"""Onboarding step 2 shows the extracted profile, never the demo one."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from ui import onboarding_markup as M
from oi.intelligence.extraction import extract_candidate
from tests.test_candidate_extraction import FakeModelClient, fact, make_cv, make_fields

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")

#: Values the mockup shows for its demo candidate. None may appear as extracted.
DEMO_VALUES = ["Giulia Rossi", "Fudan", "EU citizen", "China X1", "Mandarin", "Financial modelling", "Page 2 of 2"]


def step2(profile=None) -> str:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"
    if profile is not None:
        at.session_state[store.CANDIDATE] = profile
    at.run()
    assert not at.exception
    return "".join(m.value for m in at.markdown)


def profile(**fields):
    return extract_candidate(make_cv(), FakeModelClient(fields=make_fields(**fields)))


def test_without_a_profile_nothing_is_shown_as_extracted() -> None:
    page = step2()

    assert "No CV read yet" in page
    assert "Upload your CV in step 1" in page
    assert '<span class="w-b ok">' not in page
    for value in DEMO_VALUES:
        assert value not in page


def test_extracted_facts_and_their_quotes_are_shown() -> None:
    page = step2(profile())

    for value in ["Python", "MSc Finance, Bocconi University", "Summer Analyst at Mediobanco"]:
        assert value in page
    # Each quote appears on the CV panel and as the hover text of its fact.
    for quote in ["Skills: Python", "MSc Finance, Bocconi University, 2026", "Summer Analyst, Mediobanco, June-August 2025"]:
        assert f'title="{quote}"' in page
        assert f"{quote}</div>" in page
    assert "3 of 3 sections found in your CV" in page
    assert "Your CV<span>3 quotes</span>" in page
    for value in DEMO_VALUES:
        assert value not in page


def test_sections_the_cv_extraction_does_not_read_are_marked_not_read() -> None:
    page = step2(profile())

    for title in ["Work authorization", "Sponsorship", "Languages"]:
        assert f"<b>{title}</b>" in page
    assert page.count("Not read from your CV") == 3


def test_a_section_with_no_facts_says_it_is_not_stated() -> None:
    page = step2(profile(education=[]))

    assert "2 of 3 sections found in your CV" in page
    assert "Not stated in your CV" in page
    assert '<span class="tg">Education</span>' not in page


def test_long_skill_lists_are_summarised() -> None:
    page = step2(profile(skills=[fact(f"Skill {i}", "Python") for i in range(1, 11)]))

    assert "Skill 8" in page
    assert "Skill 9" not in page
    assert '<span class="w-chip">+2</span>' in page


def test_quote_counts_count_distinct_quotes_not_facts() -> None:
    # Three skills read from the same line of the CV.
    skills = [fact(s, "Skills: Python") for s in ["Python", "Excel", "Valuation"]]

    page = step2(profile(skills=skills))

    assert "From your CV · 1 quote</div>" in page
    assert "Your CV<span>3 quotes</span>" in page
    assert page.count("Skills: Python</div>") == 1


def test_missing_mockup_markup_fails_loudly(monkeypatch) -> None:
    monkeypatch.setattr(M, "S_2", M.S_2.replace("Page 2 of 2", "Page 1 of 1"))
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"

    at.run()

    assert at.exception
    assert "Step 2 mockup markup has changed" in at.exception[0].message


def test_backslashes_in_cv_text_are_shown_as_written() -> None:
    page = step2(profile(skills=[fact(r"C\1 and \g<0>", "Python")]))

    assert r"C\1 and \g&lt;0&gt;" in page


def test_cv_text_is_escaped() -> None:
    page = step2(profile(skills=[fact("<img src=x onerror=alert(1)>", "Python")]))

    assert "&lt;img src=x onerror=alert(1)&gt;" in page
    assert "<img src=x" not in page
