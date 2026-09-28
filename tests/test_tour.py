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
