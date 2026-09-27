"""Onboarding step 2 shows the extracted profile, never the demo one."""

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from ui import onboarding_markup as M
from oi.intelligence.extraction import extract_candidate
from oi.providers.model_client import ExtractedLanguage
from tests.test_candidate_extraction import FakeModelClient, fact, make_cv, make_fields

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")

#: Values the mockup shows for its demo candidate. None may appear as extracted.
DEMO_VALUES = ["Giulia Rossi", "Fudan", "EU citizen", "China X1", "Mandarin", "Financial modelling", "Page 2 of 2"]


#: What a card holds for when it is opened, hidden until then (ui/js/expand.js).
OPENED = re.compile(r'<div class="xp-full">(.*?)</div><span class="xp-ic"', re.S)


def step2(profile=None, opened: bool = False) -> str:
    """The step's markup as shown, or with `opened` also what each card
    shows once opened."""
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"
    if profile is not None:
        at.session_state[store.CANDIDATE] = profile
    at.run()
    assert not at.exception
    page = "".join(m.value for m in at.markdown)
    return page if opened else OPENED.sub('<span class="xp-ic"', page)


def opened_card(page: str, title: str) -> str:
    """What the card titled `title` shows once opened."""
    return OPENED.search(page.split(f"<b>{title}</b>", 1)[1]).group(1)


def profile(**fields):
    return extract_candidate(make_cv(), FakeModelClient(fields=make_fields(**fields)))


LANGUAGE_LINE = "Languages: English (C1), Mandarin HSK 4, Japanese JLPT N2, Italian (native), Spanish (fluent)"


def lang(code: str, level: str, quote: str) -> ExtractedLanguage:
    return ExtractedLanguage(language=code, level=level, quote=quote)


def speaker(*languages: ExtractedLanguage):
    """A profile read from a CV that also states `languages` on LANGUAGE_LINE."""
    cv = make_cv(make_cv().text + LANGUAGE_LINE + "\n")
    return extract_candidate(cv, FakeModelClient(fields=make_fields(languages=list(languages))))


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


def test_a_read_cv_without_languages_says_none_are_stated() -> None:
    page = step2(profile())

    for title in ["Work authorization", "Sponsorship", "Languages"]:
        assert f"<b>{title}</b>" in page
    # Work authorization and sponsorship are declared by the user instead
    # (tests/test_onboarding_work_auth.py); only work authorization is required.
    assert page.count('Required · add it in <span class="p-link') == 1
    assert page.count('Not declared yet · add it in <span class="p-link') == 1
    card = page.split("<b>Languages</b>", 1)[1].split('<div class="w-card', 1)[0]
    assert card.startswith('<span class="w-b ne"><i></i>Not found</span>')
    assert '<div class="p-v">Not stated in your CV</div>' in card
    assert "Not read from your CV" not in page
    assert '<span class="tg">Languages</span>' not in page


def test_languages_are_marked_not_read_without_a_profile() -> None:
    page = step2()

    assert "<b>Languages</b>" in page
    assert page.count("Not read from your CV") == 1


# --- languages ----------------------------------------------------------------


def test_languages_read_from_the_cv_are_shown_on_their_own_scale() -> None:
    page = step2(speaker(
        lang("en", "C1", "English (C1)"),
        lang("zh", "HSK 4", "Mandarin HSK 4"),
        lang("ja", "JLPT N2", "Japanese JLPT N2"),
        lang("it", "Native", "Italian (native)"),
    ))

    card = page.split("<b>Languages</b>", 1)[1].split('<div class="w-card', 1)[0]
    assert '<span class="w-b ok"><i></i>Found</span>' in card
    for label, quote in [
        ("English · C1", "English (C1)"),
        ("Mandarin · HSK 4", "Mandarin HSK 4"),
        ("Japanese · JLPT N2", "Japanese JLPT N2"),
        ("Italian · native", "Italian (native)"),
    ]:
        assert f'<span class="w-chip" title="{quote}">{label}</span>' in card
    assert "From your CV · 4 quotes</div>" in card
    assert "Not read from your CV" not in page


def test_language_quotes_appear_on_the_cv_panel() -> None:
    page = step2(speaker(lang("zh", "HSK 4", "Mandarin HSK 4")))

    panel = page.split('<div class="p-page">', 1)[1]
    assert '<span class="tg">Languages</span><div style="font-size:12px;line-height:1.5;color:var(--t1)">Mandarin HSK 4</div>' in panel
    assert "Your CV<span>4 quotes</span>" in page
    # Languages are not one of the three CV sections the header counts.
    assert "3 of 3 sections found in your CV" in page


def test_fluent_is_shown_as_the_cv_states_it() -> None:
    # Stored as SELF:fluent; what it counts as is the rule's concern, not the card's.
    page = step2(speaker(lang("es", "Fluent", "Spanish (fluent)")))

    assert '<span class="w-chip" title="Spanish (fluent)">Spanish · fluent</span>' in page


def test_a_native_language_in_other_words_is_shown_as_native() -> None:
    # DEMO-05: "mother tongue" is native (D-049), not "level not stated".
    line = "Italian - Mother tongue"
    cv = make_cv(make_cv().text + line + "\n")
    page = step2(extract_candidate(cv, FakeModelClient(fields=make_fields(languages=[lang("it", "Mother tongue", line)]))))

    assert f'<span class="w-chip" title="{line}">Italian · native</span>' in page
    assert "level not stated" not in page


def test_a_language_without_a_readable_level_is_still_listed() -> None:
    page = step2(speaker(lang("de", "", "Italian (native)")))

    assert "German · level not stated</span>" in page


def test_an_unknown_language_code_is_shown_as_the_code() -> None:
    page = step2(speaker(lang("pt", "C1", "English (C1)")))

    assert "PT · C1</span>" in page


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
    page = step2(profile(skills=[fact("<img src=x onerror=alert(1)>", "Python")]), opened=True)

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


# --- a card opened in full --------------------------------------------------


def test_every_card_opens() -> None:
    page = step2(profile(), opened=True)

    for title in ["Skills", "Education", "Experience", "Work authorization", "Sponsorship", "Languages"]:
        assert f'aria-label="Open {title}"' in page
    assert page.count('<div class="xp-full">') == 6


def test_an_opened_card_lists_every_role_with_its_quote() -> None:
    card = opened_card(step2(profile(experience=ROLES), opened=True), "Experience")

    for i in range(1, 6):
        assert f'<div class="xp-it"><div class="p-v">Role {i}</div>' in card
    assert card.count('<div class="xp-q">Summer Analyst, Mediobanco, June-August 2025</div>') == 5
    assert "p-e" not in card  # nothing is cut
    assert "more</div>" not in card


def test_an_opened_card_lists_every_skill_and_each_quote_once() -> None:
    skills = [fact(f"Skill {i}", "Skills: Python") for i in range(1, 11)]

    card = opened_card(step2(profile(skills=skills), opened=True), "Skills")

    for i in range(1, 11):
        assert f">Skill {i}</span>" in card
    assert '<span class="w-chip">+' not in card
    assert card.count('<div class="xp-q">Skills: Python</div>') == 1


def test_an_opened_required_card_offers_no_dead_button() -> None:
    card = opened_card(step2(profile(), opened=True), "Work authorization")

    assert card == '<div class="p-v">Required · add it in Edit profile</div>'


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


# --- the Languages tab --------------------------------------------------------


def languages_editor():
    """The editor on a CV stating English C1 and Mandarin HSK 4."""
    return open_editor(speaker(lang("en", "C1", "English (C1)"), lang("zh", "HSK 4", "Mandarin HSK 4")))


def test_each_language_has_a_language_and_a_level_field() -> None:
    at = languages_editor()
    rev = at.session_state["ed_rev"]
    assert at.selectbox(key=f"ed-lang-{rev}-0").value == "en"
    assert at.selectbox(key=f"ed-lvl-{rev}-0").value == "CEFR:C1"
    assert at.selectbox(key=f"ed-lang-{rev}-1").value == "zh"
    # Levels stay on the language's own scale.
    assert at.selectbox(key=f"ed-lvl-{rev}-1").options == ["HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6", "Fluent", "Native"]
    # A language already listed is not offered again.
    assert "zh" not in at.selectbox(key=f"ed-lang-{rev}-0").options


def test_unchanged_languages_stay_backed_by_the_cv() -> None:
    at = languages_editor()
    at.button(key="ed-save").click().run()
    saved = at.session_state[store.CANDIDATE].eligibility_answers["HC_LANGUAGE"]
    assert [(a.answer_key, a.value) for a in saved] == [("level_en", "CEFR:C1"), ("level_zh", "HSK:4")]
    assert not any(store.is_edited(at.session_state[store.CANDIDATE], a) for a in saved)


def test_a_changed_level_and_an_added_language_are_saved_as_the_users_word() -> None:
    at = languages_editor()
    # One run: after it the dialog is not drawn again, as nothing reopens it.
    at.selectbox(key=f"ed-lvl-{at.session_state['ed_rev']}-0").set_value("CEFR:C2")
    at.session_state["ed_draft"]["languages"].append(["it", "SELF:native"])  # a row added and filled in
    at.button(key="ed-save").click().run()
    assert not at.exception
    p = at.session_state[store.CANDIDATE]
    saved = p.eligibility_answers["HC_LANGUAGE"]
    assert [(a.answer_key, a.value) for a in saved] == [("level_en", "CEFR:C2"), ("level_zh", "HSK:4"), ("level_it", "SELF:native")]
    assert [store.is_edited(p, a) for a in saved] == [True, False, True]


def test_adding_a_language_adds_an_empty_row() -> None:
    at = languages_editor()
    at.button(key="ed-add-languages").click().run()
    assert at.session_state["ed_draft"]["languages"][-1] == [None, None]


def test_an_added_language_needs_a_level() -> None:
    at = languages_editor()
    at.session_state["ed_draft"]["languages"].append(["de", None])
    at.button(key="ed-save").click().run()
    assert at.session_state["ed_error"] == "Choose a level for German."
    assert len(at.session_state[store.CANDIDATE].eligibility_answers["HC_LANGUAGE"]) == 2


def test_removing_a_language_removes_its_answer() -> None:
    at = languages_editor()
    at.button(key=f"ed-del-languages-{at.session_state['ed_rev']}-0").click()
    at.button(key="ed-save").click().run()
    saved = at.session_state[store.CANDIDATE].eligibility_answers["HC_LANGUAGE"]
    assert [a.answer_key for a in saved] == ["level_zh"]
