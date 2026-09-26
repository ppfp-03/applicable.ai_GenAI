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
    # Languages is not read; work authorization and sponsorship are declared
    # by the user instead (tests/test_onboarding_work_auth.py).
    assert page.count("Not read from your CV") == 1
    assert page.count("Required · add it in Edit profile") == 2


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


ROLES = [fact(f"Role {i}", "Summer Analyst, Mediobanco, June-August 2025") for i in range(1, 6)]


def test_each_role_is_its_own_line() -> None:
    page = step2(profile(experience=ROLES[:3]))

    for i in range(1, 4):
        assert f'<div class="p-v p-e" title="Summer Analyst, Mediobanco, June-August 2025">Role {i}</div>' in page
    assert "more</div>" not in page


def test_roles_beyond_the_card_are_counted() -> None:
    page = step2(profile(experience=ROLES))

    assert ">Role 3</div>" in page
    assert "Role 4" not in page
    assert '<div class="p-m">+2 more</div>' in page


def test_edited_values_are_marked_and_kept_off_the_cv_panel() -> None:
    edited = store.apply_edits(profile(), {"experience": ["Summer Analyst at Mediobanco", "Intern at Acme"]})

    page = step2(edited)

    assert '<div class="p-v p-e" title="Edited by you">Intern at Acme</div>' in page
    assert "From your CV · 1 quote · 1 edited by you</div>" in page
    assert "Intern at Acme" not in page.split('<div class="p-page">', 1)[1]
    assert "Your CV<span>3 quotes</span>" in page


def test_the_edit_button_is_always_offered() -> None:
    # Without a CV the editor still takes the mandatory work authorization.
    def buttons(p=None) -> list[str]:
        at = AppTest.from_file(ONBOARDING, default_timeout=30)
        at.session_state["ob_step"] = "2"
        if p is not None:
            at.session_state[store.CANDIDATE] = p
        at.run()
        return [b.label for b in at.button]

    assert "Edit profile" in buttons()
    assert "Edit profile" in buttons(profile())
    assert "Edit profile" in step2(profile())
    assert "Edit profile" in step2()


# --- the Edit profile dialog ------------------------------------------------


#: A saved declaration, so these tests exercise the CV sections alone.
DECLARED = {"authorized": ["IT"], "sponsorship": []}


def open_editor(p):
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"
    at.session_state[store.CANDIDATE] = p
    at.session_state[store.WORK_AUTH] = DECLARED
    at.run()
    at.button(key="oo-edit").click().run()
    assert not at.exception
    return at


def test_each_part_of_an_entry_has_its_own_field() -> None:
    value = "MSc in International Management · Fudan University · Sep 2025 – Jul 2027"
    at = open_editor(profile(education=[fact(value, "MSc Finance, Bocconi University, 2026")]))

    fields = {t.label: t.value for t in at.text_input if t.key.startswith("ed-education-")}
    assert fields == {"Degree": "MSc in International Management", "Institution": "Fudan University", "Dates": "Sep 2025 – Jul 2027"}


def test_the_editor_starts_from_the_profile() -> None:
    p = profile(experience=ROLES[:3])

    at = open_editor(p)

    entries = [t.value for t in at.text_input if t.key.startswith("ed-experience-")]
    assert entries == ["Role 1", "", "", "Role 2", "", "", "Role 3", "", ""]
    assert [t.value for t in at.text_input if t.key.startswith("ed-education-")] == ["MSc Finance, Bocconi University", "", ""]
    assert [b.label for b in at.button if b.key.startswith("ed-chip-")] == ["Python"]


def test_removing_and_adding_entries_changes_only_the_draft() -> None:
    at = open_editor(profile(experience=ROLES[:3]))

    # One run: after it the dialog is not drawn again, as nothing reopens it.
    at.button(key=f"ed-del-experience-{at.session_state['ed_rev']}-0").click()
    at.button(key="ed-add-education").click().run()

    assert at.session_state["ed_draft"]["experience"] == ["Role 2", "Role 3"]
    assert at.session_state["ed_draft"]["education"] == ["MSc Finance, Bocconi University", ""]
    assert [f.value for f in at.session_state[store.CANDIDATE].experience] == ["Role 1", "Role 2", "Role 3"]


def test_saving_applies_the_edits_with_their_provenance() -> None:
    at = open_editor(profile())
    rev = at.session_state["ed_rev"]

    at.text_input(key=f"ed-experience-{rev}-0-1").input("Mediobanco")
    at.text_input(key=f"ed-experience-{rev}-0-2").input("Jun 2025 – Aug 2025")
    at.text_input(key="ed-skill-new").input("SQL")  # typed, never confirmed with Enter
    at.button(key="ed-save").click().run()

    saved = at.session_state[store.CANDIDATE]
    assert [f.value for f in saved.experience] == ["Summer Analyst at Mediobanco · Mediobanco · Jun 2025 – Aug 2025"]
    assert [f.value for f in saved.skills] == ["Python", "SQL"]
    assert store.is_edited(saved, saved.experience[0])
    assert not store.is_edited(saved, saved.skills[0])
    assert "ed_draft" not in at.session_state


def test_cancel_keeps_the_profile() -> None:
    before = profile()
    at = open_editor(before)

    at.text_input(key=f"ed-experience-{at.session_state['ed_rev']}-0-0").input("Something else")
    at.button(key="ed-cancel").click().run()

    assert at.session_state[store.CANDIDATE] == before
    assert "ed_draft" not in at.session_state
