"""The data processing consent: given by uploading the CV in onboarding
step 1, required before matching, and first in the Profile's summary."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from oi.providers import kimi
from tests.test_candidate_extraction import FakeModelClient, make_fields
from tests.test_io import build_text_pdf

ROOT = Path(__file__).resolve().parents[1]
ONBOARDING = str(ROOT / "views" / "onboarding.py")
APP = str(ROOT / "app.py")
DECLARED = {"authorized": ["IT"], "sponsorship": []}
NOTE = "By uploading your CV you consent to Applicable.ai processing your data"
NEEDS_CONSENT = "Upload your CV in step 1 to continue: uploading it gives your consent to data processing."
PROFILE_GATE = "Give your data processing consent first"


def page(at: AppTest) -> str:
    return "".join(m.value for m in at.markdown)


def onboarding(step: str, **state) -> AppTest:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = step
    at.session_state[store.WORK_AUTH] = DECLARED
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception
    return at


# --- Onboarding ---------------------------------------------------------------

def test_step_1_says_that_uploading_gives_the_consent() -> None:
    at = onboarding("1")
    assert NOTE in page(at)
    assert store.CONSENT not in at.session_state  # nothing is given until a CV is uploaded


def test_uploading_the_cv_gives_the_consent(monkeypatch) -> None:
    monkeypatch.setattr(kimi, "KimiClient", lambda: FakeModelClient(fields=make_fields(education=[], experience=[])))
    at = onboarding("1")
    at.file_uploader(key="ob-cv").set_value(("cv.pdf", build_text_pdf("Skills: Python"), "application/pdf"))
    at.run()
    assert not at.exception
    assert at.session_state[store.CONSENT] is True


def test_matching_does_not_start_without_the_consent() -> None:
    at = onboarding("3b", ob_swipes=["r"] * 12, ob_taught=True)
    at.button(key="next").click().run()  # Explore → Fine-tune, with the rows the swipes suggest
    assert at.session_state["ob_step"] == "3a"
    assert NEEDS_CONSENT in page(at)  # the footer says why before the press

    at.button(key="next").click().run()

    assert at.session_state["ob_step"] == "3a"
    assert NEEDS_CONSENT in page(at)


def test_a_step_pill_past_preferences_needs_the_consent() -> None:
    at = onboarding("3a", ob_swipes=["r"] * 12)
    at.button(key="oo-st4").click().run()
    assert at.session_state["ob_step"] == "3a"


def test_a_step_link_to_matching_without_consent_lands_on_the_upload() -> None:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state[store.WORK_AUTH] = DECLARED
    at.query_params["step"] = "5"
    at.run()
    assert not at.exception
    assert at.session_state["ob_step"] == "1"


def test_with_the_consent_matching_starts() -> None:
    at = onboarding("3a", ob_swipes=["r"] * 12, **{store.CONSENT: True})
    at.button(key="oo-st4").click().run()
    assert at.session_state["ob_step"] == "4"


# --- Profile ------------------------------------------------------------------

def profile(consent: bool) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    at.session_state[store.CONSENT] = consent
    at.run()
    assert not at.exception
    return at


def consent_index() -> int:
    return next(i for i, s in enumerate(store.data().sections) if s["id"] == store.CONSENT_SECTION)


def test_without_consent_only_the_consent_section_opens() -> None:
    at = profile(consent=False)
    assert PROFILE_GATE in page(at)
    assert at.session_state["profile_cur"] == consent_index()

    at.button(key="ov-sec-0").click().run()

    assert not at.exception
    assert at.session_state["profile_cur"] == consent_index()
    assert "Mark as incorrect" not in [b.label for b in at.button]


def test_giving_the_consent_in_the_profile_opens_the_other_sections() -> None:
    at = profile(consent=False)
    at.button(key="ok").click().run()

    assert not at.exception
    assert at.session_state[store.CONSENT] is True
    assert at.session_state[store.SECTIONS][store.CONSENT_SECTION] == "ok"
    assert at.session_state[store.VALUES][store.CONSENT_SECTION][store.CONSENT_LABEL] == "Given"
    assert PROFILE_GATE not in page(at)
    assert "<b>Your form</b> · given" in page(at)

    at.button(key="ov-sec-0").click().run()
    assert at.session_state["profile_cur"] == 0


def test_a_confirmed_section_without_the_consent_asks_for_it_again() -> None:
    # A session carried over from before the consent existed: the section says
    # "Confirmed · Given" while the consent itself was never recorded.
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    at.session_state[store.CONSENT] = False
    at.session_state[store.SECTIONS] = {s["id"]: "ok" for s in store.data().sections}
    at.session_state[store.VALUES] = {s["id"]: dict(s["vals"]) for s in store.data().sections}
    at.session_state[store.VALUES][store.CONSENT_SECTION][store.CONSENT_LABEL] = "Given"
    at.run()

    assert not at.exception
    assert at.session_state[store.SECTIONS][store.CONSENT_SECTION] == "pend"
    assert at.session_state[store.VALUES][store.CONSENT_SECTION][store.CONSENT_LABEL] == "Not given"
    assert at.button(key="ok").label == "Give consent"
    assert not at.button(key="ok").disabled


def test_the_consent_check_follows_the_consent() -> None:
    at = profile(consent=False)
    assert "Missing" in page(at)

    at.button(key="ok").click().run()
    at.button(key=f"ov-sec-{consent_index()}").click().run()

    assert not at.exception
    assert "Missing" not in page(at)
    assert "Pass" in page(at)


def test_the_consent_section_holds_only_the_consent() -> None:
    (section,) = [s for s in store.data().sections if s["id"] == store.CONSENT_SECTION]
    assert [label for label, _ in section["vals"]] == [store.CONSENT_LABEL]
    assert "Accuracy" not in str(section)
