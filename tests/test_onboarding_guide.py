"""Onboarding guidance: the intro sheet, the footer's line and the practice card."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import store
from ui import guide

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")
DECLARED = {"authorized": ["IT"], "sponsorship": []}


def open_step(step: str, **state) -> AppTest:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = step
    at.session_state[store.WORK_AUTH] = DECLARED
    at.session_state[store.CONSENT] = True  # given by uploading the CV in step 1
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception
    return at


def page(at: AppTest) -> str:
    return "".join(m.value for m in at.markdown)


def keys(at: AppTest) -> set[str]:
    return {b.key for b in at.button if b.key}


def test_the_first_visit_opens_the_sheet_and_got_it_closes_it() -> None:
    at = open_step("2")
    assert "guide-ok" in keys(at)
    assert "Why it matters" in page(at) and guide.GUIDE["2"].why in page(at)

    at.button(key="guide-ok").click().run()
    assert not at.exception
    assert "guide-ok" not in keys(at)
    assert "2" in at.session_state[guide.SEEN]


def test_question_mark_opens_the_sheet_again() -> None:
    at = open_step("2", **{guide.SEEN: {"2"}})
    assert "guide-ok" not in keys(at)
    at.button(key="guide-open").click().run()
    assert "guide-ok" in keys(at)


def test_step_one_sheet_is_the_journey_map() -> None:
    at = open_step("1")
    text = page(at)
    assert "gd-map" in text
    for name, _, _ in guide.JOURNEY:
        assert name in text
    assert at.button(key="guide-ok").label == "Let’s start"


def test_the_footer_says_why_once_the_sheet_is_closed() -> None:
    at = open_step("3a", **{guide.SEEN: {"3a"}}, ob_swipes=["r"] * 12)
    assert "Only what you confirm here shapes your ranking" in page(at)


def test_a_gate_still_speaks_before_the_guidance_line() -> None:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "2"
    at.run()
    assert "Add your work authorization in Edit profile to continue." in page(at)
    assert guide.GUIDE["2"].line not in page(at)


def test_every_flow_step_has_a_guide_and_a_journey_phase() -> None:
    steps = ["1", "2", "3b", "3a", "4", "5", "6", "7"]
    assert set(guide.GUIDE) == set(steps)
    assert sorted(s for _, phase, _ in guide.JOURNEY for s in phase) == sorted(steps)


# --- Explore practice card ------------------------------------------------

def swipe(at: AppTest, d: str) -> None:
    at.button(key=f"oo-sw{d}").click().run()
    assert not at.exception


def test_explore_opens_on_the_practice_card() -> None:
    at = open_step("3b", **{guide.SEEN: {"3b"}})
    text = page(at)
    assert "sw-card tut" in text
    assert "<b>Practice card</b> · then 12 stories" in text


@pytest.mark.parametrize("d", ["r", "l", "u"])
def test_the_practice_swipe_records_nothing(d: str) -> None:
    at = open_step("3b", **{guide.SEEN: {"3b"}})
    swipe(at, d)
    assert at.session_state["ob_swipes"] == []
    assert at.session_state["ob_taught"] is True
    text = page(at)
    assert "sw-card tut" not in text
    assert "<b>Story 1 of 12</b>" in text


def test_after_practice_every_swipe_counts() -> None:
    at = open_step("3b", **{guide.SEEN: {"3b"}})
    swipe(at, "r")
    swipe(at, "r")
    assert at.session_state["ob_swipes"] == ["r"]
    assert "<b>Story 2 of 12</b>" in page(at)


def test_the_shortlist_waits_while_its_sheet_is_open() -> None:
    at = open_step("5", ob_tick=0)
    assert "guide-ok" in keys(at)
    assert at.session_state["ob_tick"] == 1  # drawn once, no timer behind the sheet
