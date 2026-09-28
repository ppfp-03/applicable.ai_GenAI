"""The guided tour after onboarding (ui/tour.py)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from ui import tour

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def open_tour(only=None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "tour"
    at.session_state[tour.STEP] = 0
    at.session_state[tour.ONLY] = only
    at.run()
    assert not at.exception
    return at


def page(at: AppTest) -> str:
    return "".join(m.value for m in at.markdown)


def test_the_whole_tour_starts_on_home() -> None:
    at = open_tour()
    tab, target, title, *_ = tour.STEPS[0]
    assert tab == "home" and title in page(at)
    assert {"tour-skip", "tour-next"} <= {b.key for b in at.button if b.key}


def test_after_starting_an_application_it_shows_applications_only() -> None:
    at = open_tour("applications")
    tab, target, title, body, tip = tour.APPLY_STEPS[0]
    text = page(at)
    assert f'data-sel="{target}"' in text and title in text
    assert "tr-dots" not in text  # one card, no step counter
    keys = {b.key for b in at.button if b.key}
    assert "tour-next" not in keys and "tour-skip" not in keys
    # Closing it lets the user carry on with the application.
    at.button(key="tour-end").click().run()
    assert not at.exception
    assert at.session_state[store.STAGE] == "app"
    assert tour.ONLY not in at.session_state
    assert "aa-tour-mark" not in page(at)


def test_a_new_account_with_no_applications_still_gets_the_tour() -> None:
    # Every tab runs before the tour is drawn, so one that fails on an empty
    # account (sign_up() starts with no applications) hides the tour.
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "tour"
    at.session_state[store.APPS] = []
    at.run()
    assert not at.exception
    assert tour.STEPS[0][2] in page(at)
    assert {"tour-skip", "tour-next"} <= {b.key for b in at.button if b.key}
    # The tour's Applications step lights up the empty page's main area.
    for _ in range(3):
        at.button(key="tour-next").click().run()
    assert not at.exception
    assert f'data-sel="{tour.STEPS[3][1]}"' in page(at)
    assert "No applications yet" in page(at)


def test_skipping_the_tour_does_not_open_homes_intro_sheet() -> None:
    at = open_tour()
    at.button(key="tour-skip").click().run()
    assert not at.exception
    assert at.session_state[store.STAGE] == "app"
    assert "hg-start" not in {b.key for b in at.button if b.key}
