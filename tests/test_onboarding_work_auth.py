"""Onboarding step 2: work authorization and sponsorship are mandatory.

They are declared by the user in the Edit profile dialog, for the countries
listed in config/markets.json. Until they are, no later step opens.
"""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from oi.intelligence.extraction import extract_candidate
from tests.test_candidate_extraction import FakeModelClient, make_cv, make_fields

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")
EU = ["IT", "ES", "FR", "DE", "NL", "LU", "DK", "IE"]
OTHERS = ["GB", "CH", "CN", "HK", "SG"]
STORIES = json.loads((Path(__file__).resolve().parents[1] / "data" / "stories.json").read_text("utf-8"))["stories"]


def at_step2(declared=None, cv=False, step="2"):
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = step
    if declared is not None:
        at.session_state[store.WORK_AUTH] = declared
    if cv:
        at.session_state[store.CANDIDATE] = extract_candidate(make_cv(), FakeModelClient(fields=make_fields()))
    at.run()
    assert not at.exception
    return at


def declared(at):
    """The saved declaration; the page alone does not run store.init()."""
    return at.session_state[store.WORK_AUTH] if store.WORK_AUTH in at.session_state else None


def page(at) -> str:
    return "".join(m.value for m in at.markdown)


def editor(at):
    at.button(key="oo-edit").click().run()
    assert not at.exception
    return at


def pills(at, key):
    return next(b for b in at.get("button_group") if b.key == key)


def answer(at, authorized):
    pills(at, "ed-wa-auth").set_value(authorized)
    at.button(key="ed-save").click().run()
    assert not at.exception
    return at


# --- The gate ---------------------------------------------------------------


def test_the_platform_countries_come_from_config() -> None:
    codes = [c["code"] for c in store.markets()]
    assert codes == [*EU, "GB", "CH", "CN", "HK", "SG"]
    assert list(store.eu_codes()) == EU


def test_without_a_declaration_step_2_cannot_be_confirmed() -> None:
    at = at_step2()
    shown = page(at)
    assert shown.count('Required · add it in <span class="p-link') == 2
    assert "Add your work authorization and sponsorship in Edit profile to continue." in shown
    at.button(key="next").click().run()
    assert not at.exception
    assert at.session_state["ob_step"] == "2"
    shown = page(at)
    assert shown.count("Complete the missing information to continue: work authorization and sponsorship.") == 1
    assert shown.count("p-s miss") == 2
    at.run()  # said once: a later run does not repeat it
    assert "Complete the missing information" not in page(at)


def test_each_required_card_has_a_call_to_action_opening_the_editor() -> None:
    at = at_step2()
    shown = page(at)
    assert "+ Add work authorization" in shown and "+ Add sponsorship" in shown
    for key in ("oo-wa", "oo-sp"):
        opened = at_step2()
        opened.button(key=key).click().run()
        assert not opened.exception
        assert [t.label for t in opened.tabs] == ["Work authorization"]


def test_the_calls_to_action_open_the_work_authorization_tab_even_with_a_cv() -> None:
    for key in ("oo-wa", "oo-sp"):
        at = at_step2(cv=True)
        at.button(key=key).click().run()
        assert not at.exception
        assert at.session_state["ed_tab"] == "Work authorization"


#: Every way into the profile editor from step 2: the top chip, each card's
#: call to action, and the "Edit profile" link inside each required card.
ENTRY_POINTS = ("oo-edit", "oo-wa", "oo-sp", "oo-wa-link", "oo-sp-link")


def test_every_entry_point_opens_the_same_editor_on_work_authorization() -> None:
    for key in ENTRY_POINTS:
        at = at_step2()
        at.button(key=key).click().run()
        assert not at.exception, key
        assert [t.label for t in at.tabs] == ["Work authorization"], key
        assert {b.key for b in at.get("button_group")} == {"ed-wa-auth", "ed-wa-sp"}, key
        assert at.button(key="ed-save") and at.button(key="ed-cancel"), key


def test_saving_is_the_same_whichever_entry_point_opened_the_editor() -> None:
    results = {}
    for key in ENTRY_POINTS:
        at = at_step2()
        at.button(key=key).click().run()
        answer(at, ["EU", "GB"], ["CN", "SG"])
        results[key] = (declared(at), at.session_state[store.ANSWERS]["uk_work"], at.session_state["ob_uk"])
    assert len({repr(r) for r in results.values()}) == 1, results
    assert results["oo-edit"] == ({"authorized": [*EU, "GB"], "sponsorship": ["CN", "SG"]}, "yes", "yes")


def test_each_required_card_links_its_edit_profile_text_to_the_editor() -> None:
    shown = page(at_step2())
    assert shown.count('Required · add it in <span class="p-link') == 2
    assert '<span class="p-link wa-link">Edit profile</span>' in shown
    assert '<span class="p-link sp-link">Edit profile</span>' in shown
    for key in ("oo-wa-link", "oo-sp-link"):
        at = at_step2(cv=True)
        at.button(key=key).click().run()
        assert not at.exception
        assert at.session_state["ed_tab"] == "Work authorization"


def test_once_declared_the_required_calls_to_action_are_gone() -> None:
    at = at_step2(declared={"authorized": EU, "sponsorship": []})
    assert "+ Add work authorization" not in page(at)
    assert 'class="p-link' not in page(at)
    assert not [b for b in at.button if b.key in ("oo-wa", "oo-sp", "oo-wa-link", "oo-sp-link")]


def test_the_step_pills_cannot_skip_past_step_2() -> None:
    at = at_step2()
    at.button(key="oo-st3").click().run()
    assert at.session_state["ob_step"] == "2"
    at.button(key="oo-st1").click().run()  # going back is allowed
    assert at.session_state["ob_step"] == "1"


def test_a_step_link_past_step_2_lands_on_step_2() -> None:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.query_params["step"] = "4"
    at.run()
    assert not at.exception
    assert at.session_state["ob_step"] == "2"


# --- The editor ---------------------------------------------------------------


def test_without_a_cv_the_editor_shows_only_work_authorization() -> None:
    at = editor(at_step2())
    assert [t.label for t in at.tabs] == ["Work authorization"]
    assert pills(at, "ed-wa-auth").options == [
        "EU · all EU countries", "United Kingdom", "Switzerland", "China", "Hong Kong", "Singapore", "None of these"]


def test_one_question_answers_both_authorization_and_sponsorship() -> None:
    at = editor(at_step2())
    assert [b.key for b in at.get("button_group")] == ["ed-wa-auth"]
    assert pills(at, "ed-wa-auth").label == "Where can you work without employer sponsorship?"
    assert "Every country you leave out is saved as needing employer sponsorship." in page(at)


def test_with_a_cv_the_work_authorization_tab_comes_after_the_cv_sections() -> None:
    at = editor(at_step2(cv=True))
    assert [t.label for t in at.tabs] == ["Experience", "Education", "Skills", "Languages", "Work authorization"]


def test_saving_without_an_answer_keeps_the_editor_open() -> None:
    at = answer(editor(at_step2()), [])
    assert declared(at) is None
    assert "ed_draft" in at.session_state
    assert "without employer sponsorship" in at.session_state["ed_error"]


def test_none_cannot_be_combined_with_countries() -> None:
    at = answer(editor(at_step2()), ["NONE", "GB"])
    assert declared(at) is None
    assert "can’t be combined" in at.session_state["ed_error"]


def test_the_countries_left_out_are_saved_as_needing_sponsorship() -> None:
    at = answer(editor(at_step2()), ["EU", "GB"])
    assert declared(at) == {"authorized": [*EU, "GB"], "sponsorship": ["CH", "CN", "HK", "SG"]}


def test_authorized_everywhere_needs_sponsorship_nowhere() -> None:
    at = answer(editor(at_step2()), ["EU", *OTHERS])
    assert declared(at) == {"authorized": [*EU, *OTHERS], "sponsorship": []}
    at.run()
    assert "Not needed anywhere" in page(at)


def test_the_store_still_refuses_a_country_both_authorized_and_sponsored() -> None:
    try:
        store.set_work_auth(["IT"], ["IT"])
    except ValueError as exc:
        assert "Italy" in str(exc)
    else:
        raise AssertionError("expected a ValueError")


def test_eu_selects_every_eu_country_and_the_step_opens() -> None:
    at = answer(editor(at_step2()), ["EU", "CH"])

    assert declared(at) == {"authorized": [*EU, "CH"], "sponsorship": ["GB", "CN", "HK", "SG"]}
    assert "ed_draft" not in at.session_state
    at.run()
    assert not at.button(key="next").disabled
    shown = page(at)
    assert "EU, Switzerland" in shown
    assert "United Kingdom, China, Hong Kong, Singapore" in shown
    assert shown.count("Declared by you") == 2


def test_none_of_these_means_sponsorship_everywhere() -> None:
    at = answer(editor(at_step2()), ["NONE"])
    assert declared(at) == {"authorized": [], "sponsorship": [*EU, *OTHERS]}
    at.run()
    shown = page(at)
    assert "None of our countries" in shown
    assert "EU, United Kingdom, Switzerland, China, Hong Kong, Singapore" in shown


def test_the_declared_uk_answer_prefills_step_6() -> None:
    for authorized, uk in ((["GB"], "yes"), (["EU"], "no")):
        at = answer(editor(at_step2()), authorized)
        assert at.session_state[store.ANSWERS]["uk_work"] == uk
        assert at.session_state["ob_uk"] == uk


# --- The EU, as one choice or country by country ---------------------------------


def test_the_eu_can_be_answered_country_by_country() -> None:
    at = editor(at_step2(declared={"authorized": ["IT", "GB"], "sponsorship": [*EU[1:], *OTHERS[1:]]}))
    assert at.checkbox(key="ed-eu-split").value
    assert pills(at, "ed-wa-auth").options[:8] == [
        "Italy", "Spain", "France", "Germany", "Netherlands", "Luxembourg", "Denmark", "Ireland"]
    assert pills(at, "ed-wa-auth").value == ["IT", "GB"]
    at.button(key="ed-save").click().run()
    assert declared(at) == {"authorized": ["IT", "GB"], "sponsorship": [*EU[1:], *OTHERS[1:]]}


def test_the_whole_eu_opens_as_one_choice() -> None:
    at = editor(at_step2(declared={"authorized": EU, "sponsorship": OTHERS}))
    assert not at.checkbox(key="ed-eu-split").value
    assert pills(at, "ed-wa-auth").value == ["EU"]


def test_joining_the_eu_again_drops_a_partial_eu_answer() -> None:
    at = editor(at_step2(declared={"authorized": ["IT", "GB"], "sponsorship": [*EU[1:], *OTHERS[1:]]}))
    at.checkbox(key="ed-eu-split").uncheck()
    at.button(key="ed-save").click().run()
    assert not at.exception
    assert declared(at) == {"authorized": ["GB"], "sponsorship": [*EU, *OTHERS[1:]]}


def test_confirming_after_the_declaration_moves_on() -> None:
    at = at_step2(declared={"authorized": ["GB"], "sponsorship": []})
    at.button(key="next").click().run()
    assert not at.exception
    assert at.session_state["ob_step"] == "3b"  # Explore is the first step 3 screen


def test_the_editor_reopens_on_the_saved_declaration() -> None:
    at = editor(at_step2(declared={"authorized": [*EU, "HK"], "sponsorship": ["GB", "CH", "CN", "SG"]}))
    assert pills(at, "ed-wa-auth").value == ["EU", "HK"]


def test_cancel_leaves_the_declaration_unset() -> None:
    at = editor(at_step2())
    pills(at, "ed-wa-auth").set_value(["GB"])
    at.button(key="ed-cancel").click().run()
    assert declared(at) is None
    assert "Add your work authorization and sponsorship in Edit profile to continue." in page(at)


def test_the_eu_shortcut_stores_iso_country_codes_only() -> None:
    from oi.contracts import validate_country_code

    at = answer(editor(at_step2()), ["EU"])
    stored = declared(at)
    assert "EU" not in stored["authorized"]
    assert stored["authorized"] == EU
    assert [validate_country_code(c) for c in stored["authorized"]] == EU


def test_the_question_does_not_equate_visa_citizenship_and_authorization() -> None:
    at = editor(at_step2())
    text = page(at)
    assert "visa" not in text.lower() and "citizen" not in text.lower()


# --- Save and exit ------------------------------------------------------------

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def app_at_step2():
    """The whole app, signed up and on onboarding step 2 without a declaration."""
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state[store.STAGE] = "onboarding"
    at.session_state[store.ANSWERS] = {"uk_work": None}  # as after sign-up
    at.session_state["ob_step"] = "2"
    at.switch_page("views/onboarding.py").run()
    assert not at.exception
    assert "Add your work authorization and sponsorship in Edit profile to continue." in page(at)
    return at


def test_save_and_exit_is_possible_but_completes_nothing() -> None:
    at = app_at_step2()
    at.button(key="exit").click().run()

    assert not at.exception
    assert at.session_state[store.STAGE] == "tour"  # left onboarding
    assert at.session_state[store.WORK_AUTH] is None
    assert at.session_state[store.ANSWERS]["uk_work"] is None  # nothing pretends it was answered


def test_returning_after_save_and_exit_still_requires_the_declaration() -> None:
    at = app_at_step2()
    at.button(key="exit").click().run()

    at.switch_page("views/onboarding.py").run()
    assert not at.exception
    assert at.session_state["ob_step"] == "2"
    assert "Add your work authorization and sponsorship in Edit profile to continue." in page(at)
    at.button(key="oo-st3").click().run()  # later pills stay hidden until Explore is done
    assert at.session_state["ob_step"] == "2"


# --- Step 5-7 use the declared UK answer --------------------------------------


def at_step(step, authorized=None, saved=None):
    """The onboarding page at `step`, after answering the editor with
    `authorized`, or with a declaration `saved` as it is, UK answer included."""
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"
    at.session_state[store.ANSWERS] = {"uk_work": None}
    if saved is not None:
        at.session_state[store.WORK_AUTH], uk = saved
        at.session_state[store.ANSWERS] = {"uk_work": uk}
        at.session_state["ob_uk"] = uk  # as the editor's save leaves it
    at.run()
    if saved is None:
        answer(editor(at), authorized)
    at.session_state["ob_step"] = step
    at.session_state["ob_tick"] = 5  # the shortlist animation has finished
    at.session_state["ob_swipes"] = ["r"] * len(STORIES)  # Explore done: every step pill is shown
    at.run()
    assert not at.exception
    return at


def test_a_declared_uk_answer_is_not_reset_to_unknown_in_step_5() -> None:
    for authorized, uk in ((["GB"], "yes"), (["NONE"], "no")):
        at = at_step("5", authorized)
        assert at.session_state[store.ANSWERS]["uk_work"] == uk
        assert "Your UK work authorization is already declared" in page(at)
        assert at.button(key="next").label == "View shortlist"


def test_a_known_uk_answer_is_not_asked_again() -> None:
    at = at_step("5", ["GB"])
    at.button(key="next").click().run()
    assert at.session_state["ob_step"] == "7"  # step 6 skipped
    assert "Declared by you" in page(at)
    assert "text-decoration:line-through\">Unknown" not in page(at)

    at.button(key="back").click().run()
    assert at.session_state["ob_step"] == "5"

    at.button(key="oo-st6").click().run()
    assert at.session_state["ob_step"] == "7"


def test_an_unsettled_uk_is_still_asked_in_step_6() -> None:
    # The editor always settles the UK; a declaration saved before it did may not.
    at = at_step("5", saved=({"authorized": EU, "sponsorship": []}, "unsure"))
    assert at.session_state[store.ANSWERS]["uk_work"] == "unsure"
    at.button(key="next").click().run()
    assert at.session_state["ob_step"] == "6"
    assert at.session_state["ob_uk"] == "unsure"


# --- The store keeps the declaration and the UK answer in step -----------------


def _store_script():
    import streamlit as st

    from core import store

    store.init()
    st.session_state["out"] = {}
    for name, (authorized, sponsorship) in st.session_state["cases"].items():
        store.set_work_auth(authorized, sponsorship)
        st.session_state["out"][name] = {
            "counts": store.counts(),
            "top": [v.id for v in store.ranked(store.answers())],
            "uk": store.uk(),
        }
    store.set_uk("no")
    st.session_state["after_step6"] = dict(store.work_auth())


def run_store(cases):
    at = AppTest.from_function(_store_script, default_timeout=30)
    at.session_state["cases"] = cases
    at.run()
    assert not at.exception
    return at


def test_non_uk_declarations_do_not_change_demo_eligibility_or_ranking() -> None:
    at = run_store({
        "eu": (EU, []),
        "asia": (["CN", "HK", "SG"], ["CH"]),
        "nothing": ([], []),
    })
    out = at.session_state["out"]
    assert out["eu"] == out["asia"] == out["nothing"]
    assert out["eu"]["uk"] == "unsure"


def test_a_later_uk_answer_updates_the_declaration() -> None:
    at = run_store({"uk": (["GB", "CH"], [])})
    assert at.session_state["out"]["uk"]["uk"] == "yes"
    assert at.session_state["after_step6"] == {"authorized": ["CH"], "sponsorship": ["GB"]}


def test_changing_an_answer_clears_the_last_error() -> None:
    at = editor(at_step2())
    at.session_state["ed_error"] = "Tell us where you are currently authorized to work."
    pills(at, "ed-wa-auth").set_value(["GB"]).run()
    assert "ed_error" not in at.session_state


def test_without_a_cv_the_editor_does_not_speak_of_one() -> None:
    at = editor(at_step2())
    assert "Tell us where you can work." in page(at)
    assert "Review what we read from your CV" not in page(at)
