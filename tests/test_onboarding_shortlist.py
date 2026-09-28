"""Onboarding step 4: once built, the shortlist opens on its #1 role and can be browsed."""

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from ui.html import esc

ONBOARDING = str(Path(__file__).resolve().parents[1] / "views" / "onboarding.py")
DECLARED = {"authorized": ["IT"], "sponsorship": []}


def built_shortlist() -> str:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "4"
    at.session_state["ob_tick"] = 5
    at.session_state[store.WORK_AUTH] = DECLARED
    at.run()
    assert not at.exception
    return next(m.value for m in at.markdown if 'id="cr-row"' in m.value)


def test_the_built_shortlist_centres_the_highest_score() -> None:
    page = built_shortlist()
    cards = re.findall(r'<div class="cc ([^"]*)" data-i="(\d)">.*?<b>(\d+)<small>/100', page, re.S)
    assert len(cards) == 5
    scores = [int(s) for _, _, s in cards]
    assert scores == sorted(scores, reverse=True)
    centre = [int(i) for cls, i, _ in cards if "c0" in cls.split()]
    assert centre == [0]
    assert 'data-cur="0"' in page


def test_the_built_shortlist_can_be_browsed() -> None:
    page = built_shortlist()
    assert "data-done" in page
    assert 'class="cr-nav prev off"' in page and 'class="cr-nav next"' in page
    assert len(re.findall(r'<div class="slot[^"]*" data-i="\d"', page)) == 5
    assert esc("Previous") in page
