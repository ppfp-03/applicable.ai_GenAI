"""Onboarding step 2: work authorization and sponsorship are mandatory.

They are declared by the user in the Edit profile dialog, for the countries
listed in config/markets.json. Until they are, no later step opens.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from oi.intelligence.extraction import extract_candidate
from tests.test_candidate_extraction import FakeModelClient, make_cv, make_fields

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")
EU = ["IT", "ES", "FR", "DE", "NL", "LU", "DK", "IE"]


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


def answer(at, authorized, sponsorship):
    pills(at, "ed-wa-auth").set_value(authorized)
    pills(at, "ed-wa-sp").set_value(sponsorship)
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
    assert at.button(key="next").disabled
    shown = page(at)
    assert shown.count("Required · add it in Edit profile") == 2
    assert "Add your work authorization and sponsorship in Edit profile to continue." in shown


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
    assert len(pills(at, "ed-wa-sp").options) == 14  # every country, then "None of these"


def test_with_a_cv_the_work_authorization_tab_comes_after_the_cv_sections() -> None:
    at = editor(at_step2(cv=True))
    assert [t.label for t in at.tabs] == ["Experience", "Education", "Skills", "Work authorization"]


def test_saving_without_answers_keeps_the_editor_open() -> None:
    at = answer(editor(at_step2()), [], [])
    assert declared(at) is None
    assert "ed_draft" in at.session_state
    assert "where you are currently authorized to work" in at.session_state["ed_error"]


def test_none_cannot_be_combined_with_countries() -> None:
    at = answer(editor(at_step2()), ["NONE", "GB"], ["NONE"])
    assert declared(at) is None
    assert "can’t be combined" in at.session_state["ed_error"]


def test_a_country_cannot_be_both_authorized_and_need_sponsorship() -> None:
    at = answer(editor(at_step2()), ["EU"], ["IT", "SG"])
    assert declared(at) is None
    assert "Italy" in at.session_state["ed_error"]


def test_eu_selects_every_eu_country_and_the_step_opens() -> None:
    at = answer(editor(at_step2()), ["EU", "CH"], ["CN", "SG"])

    assert declared(at) == {"authorized": [*EU, "CH"], "sponsorship": ["CN", "SG"]}
    assert "ed_draft" not in at.session_state
    at.run()
    assert not at.button(key="next").disabled
    shown = page(at)
    assert "EU, Switzerland" in shown
    assert "China, Singapore" in shown
    assert shown.count("Declared by you") == 2


def test_none_everywhere_is_a_complete_answer() -> None:
    at = answer(editor(at_step2()), ["NONE"], ["NONE"])
    assert declared(at) == {"authorized": [], "sponsorship": []}
    at.run()
    shown = page(at)
    assert "None of our countries" in shown
    assert "Not needed anywhere" in shown


def test_the_declared_uk_answer_prefills_step_6() -> None:
    cases = [(["GB"], ["NONE"], "yes"), (["EU"], ["GB"], "no"), (["EU"], ["NONE"], "unsure")]
    for authorized, sponsorship, uk in cases:
        at = answer(editor(at_step2()), authorized, sponsorship)
        assert at.session_state[store.ANSWERS]["uk_work"] == uk
        assert at.session_state["ob_uk"] == uk


def test_confirming_after_the_declaration_moves_on() -> None:
    at = at_step2(declared={"authorized": ["GB"], "sponsorship": []})
    at.button(key="next").click().run()
    assert not at.exception
    assert at.session_state["ob_step"] == "3a"


def test_the_editor_reopens_on_the_saved_declaration() -> None:
    at = editor(at_step2(declared={"authorized": [*EU, "HK"], "sponsorship": []}))
    assert pills(at, "ed-wa-auth").value == ["EU", "HK"]
    assert pills(at, "ed-wa-sp").value == ["NONE"]


def test_cancel_leaves_the_declaration_unset() -> None:
    at = editor(at_step2())
    pills(at, "ed-wa-auth").set_value(["GB"])
    at.button(key="ed-cancel").click().run()
    assert declared(at) is None
    assert at.button(key="next").disabled


# --- Each question needs its own explicit answer -----------------------------


def test_only_the_authorization_answer_is_not_enough() -> None:
    at = answer(editor(at_step2()), ["GB"], [])
    assert declared(at) is None
    assert "employer sponsorship" in at.session_state["ed_error"]


def test_only_the_sponsorship_answer_is_not_enough() -> None:
    at = answer(editor(at_step2()), [], ["NONE"])
    assert declared(at) is None
    assert "currently authorized to work" in at.session_state["ed_error"]


def test_the_eu_shortcut_stores_iso_country_codes_only() -> None:
    from oi.contracts import validate_country_code

    at = answer(editor(at_step2()), ["EU"], ["NONE"])
    stored = declared(at)
    assert "EU" not in stored["authorized"]
    assert stored["authorized"] == EU
    assert [validate_country_code(c) for c in stored["authorized"]] == EU


def test_the_questions_do_not_equate_visa_citizenship_and_authorization() -> None:
    at = editor(at_step2())
    assert pills(at, "ed-wa-auth").label == "In which countries are you currently authorized to work?"
    assert pills(at, "ed-wa-sp").label == "In which countries would you require employer sponsorship?"
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
    assert at.button(key="next").disabled
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
    assert at.button(key="next").disabled
    at.button(key="oo-st5").click().run()
    assert at.session_state["ob_step"] == "2"


# --- Step 5-7 use the declared UK answer --------------------------------------


def at_step(step, authorized, sponsorship):
    """The onboarding page at `step`, after a declaration made through the store."""
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"
    at.session_state[store.ANSWERS] = {"uk_work": None}
    at.run()
    answer(editor(at), authorized, sponsorship)
    at.session_state["ob_step"] = step
    at.session_state["ob_tick"] = 5  # the shortlist animation has finished
    at.run()
    assert not at.exception
    return at


def test_a_declared_uk_answer_is_not_reset_to_unknown_in_step_5() -> None:
    for authorized, sponsorship, uk in ((["GB"], ["NONE"], "yes"), (["NONE"], ["GB"], "no")):
        at = at_step("5", authorized, sponsorship)
        assert at.session_state[store.ANSWERS]["uk_work"] == uk
        assert "Your UK work authorization is already declared" in page(at)
        assert at.button(key="next").label == "View shortlist"


def test_a_known_uk_answer_is_not_asked_again() -> None:
    at = at_step("5", ["GB"], ["NONE"])
    at.button(key="next").click().run()
    assert at.session_state["ob_step"] == "7"  # step 6 skipped
    assert "Declared by you" in page(at)
    assert "text-decoration:line-through\">Unknown" not in page(at)

    at.button(key="back").click().run()
    assert at.session_state["ob_step"] == "5"

    at.button(key="oo-st6").click().run()
    assert at.session_state["ob_step"] == "7"


def test_an_unsettled_uk_is_still_asked_in_step_6() -> None:
    at = at_step("5", ["EU"], ["NONE"])  # neither authorized in nor sponsored for the UK
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
