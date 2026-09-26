"""Onboarding step 3b: every swipe updates "What we're learning about you"."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import explore
from ui.html import esc

ROOT = Path(__file__).resolve().parents[1]
ONBOARDING = str(ROOT / "views" / "onboarding.py")
STORIES = json.loads((ROOT / "data" / "stories.json").read_text("utf-8"))["stories"]


def test_every_story_carries_what_the_panel_needs() -> None:
    assert len(STORIES) == 12
    assert len({s["title"] for s in STORIES}) == 12
    for s in STORIES:
        assert len(s["riasec"]) == len(explore.RIASEC)
        assert len(s["lean"]) == 4
        assert s["direction"] and s["role"] and s["match"]
        assert "why" not in s  # derived from the candidate's own CV, never stored


def test_no_swipes_leave_the_panel_at_its_start() -> None:
    assert explore.sliders(STORIES, []) == [explore.SLIDER_START] * 4
    assert explore.interests(STORIES, []) == [explore.INTEREST_START] * 6
    assert explore.top_interests(explore.interests(STORIES, [])) == []
    assert explore.direction(STORIES, []) == ([], None)
    assert explore.history(STORIES, []) == []


def test_a_like_and_a_pass_move_the_sliders_opposite_ways() -> None:
    lean = STORIES[0]["lean"]
    liked, passed = explore.sliders(STORIES, ["r"]), explore.sliders(STORIES, ["l"])
    for i, k in enumerate(lean):
        assert liked[i] - explore.SLIDER_START == explore.SLIDER_STEP * k
        assert passed[i] - explore.SLIDER_START == -explore.SLIDER_STEP * k
    assert explore.sliders(STORIES, ["u"]) == [explore.SLIDER_START] * 4


def test_sliders_and_interests_stay_on_their_track() -> None:
    for verdict in explore.VERDICTS:
        for p in explore.sliders(STORIES, [verdict] * 12):
            assert explore.SLIDER_MIN <= p <= explore.SLIDER_MAX
        for v in explore.interests(STORIES, [verdict] * 12):
            assert explore.INTEREST_MIN <= v <= explore.INTEREST_MAX


def test_liking_a_story_raises_its_strongest_interest() -> None:
    story = STORIES[0]
    strongest = max(range(6), key=lambda i: story["riasec"][i])
    assert explore.top_interests(explore.interests(STORIES, ["r"]))[0] == strongest
    assert explore.interests(STORIES, ["l"])[strongest] < explore.INTEREST_START


def test_direction_follows_likes_and_drops_what_was_passed() -> None:
    dirs, role = explore.direction(STORIES, ["r"])
    assert dirs == [STORIES[0]["direction"]]
    assert role is STORIES[0]
    assert explore.direction(STORIES, ["l"]) == ([], None)
    assert explore.direction(STORIES, ["u"]) == ([], None)


def test_history_is_newest_first_and_skips_not_sure() -> None:
    hist = explore.history(STORIES, ["r", "u", "l"])
    assert hist == [("n", STORIES[2]["title"]), ("y", STORIES[0]["title"])]
    assert len(explore.history(STORIES, ["r"] * 12)) == 5


def test_why_names_only_skills_the_cv_has() -> None:
    story = {"sk": ["SQL", "Data analysis", "Clear communication"]}
    assert explore.cv_overlap(story, ["sql", "Python"]) == ["SQL"]
    assert explore.cv_overlap(story, ["Advanced data analysis"]) == ["Data analysis"]
    assert explore.cv_overlap(story, ["R"]) == []


def step3b(verdicts=None) -> tuple[AppTest, str]:
    at = AppTest.from_file(ONBOARDING, default_timeout=30)
    at.session_state["ob_step"] = "3b"
    if verdicts is not None:
        at.session_state["ob_swipes"] = verdicts
    at.run()
    assert not at.exception
    return at, "".join(m.value for m in at.markdown)


def radar(page: str) -> str:
    start = page.index('<svg width="370"')
    return page[start:page.index("</svg>", start)]


def swipe_buttons(at: AppTest) -> dict:
    return {b.key: b for b in at.button if b.key and b.key.startswith("oo-sw")}


def test_the_stack_starts_at_the_first_story_with_nothing_learned() -> None:
    _, page = step3b()
    assert "<b>Story 1 of 12</b>" in page
    assert "Live · from 0 swipes" in page
    assert "Nothing yet" in page
    assert "Not clear yet" in page
    assert esc(STORIES[0]["h"]) in page
    # The mockup's demo values are gone.
    for demo in ["Story 8 of 12", "Pricing analysis", "Growth Analyst</b> · 9 open roles", "Mediobanco"]:
        assert demo not in page


def test_a_swipe_updates_the_whole_panel() -> None:
    at, before = step3b()
    swipe_buttons(at)["oo-swr"].click().run()
    assert not at.exception
    after = "".join(m.value for m in at.markdown)
    assert at.session_state["ob_swipes"] == ["r"]
    assert "<b>Story 2 of 12</b>" in after
    assert "Live · from 1 swipe<" in after
    assert f"✓ {STORIES[0]['title']}" in after
    assert STORIES[0]["direction"] in after and STORIES[0]["role"] in after
    assert after.count('<div class="bp">') == 4
    assert f'<i style="left:{explore.sliders(STORIES, ["r"])[0]:.0f}%">' in after
    assert radar(after) != radar(before)
    assert esc(STORIES[1]["h"]) in after


def test_not_sure_moves_the_count_only() -> None:
    at, _ = step3b()
    swipe_buttons(at)["oo-swu"].click().run()
    page = "".join(m.value for m in at.markdown)
    assert at.session_state["ob_swipes"] == ["u"]
    assert "Nothing yet" in page and "Not clear yet" in page
    assert "Live · from 1 swipe<" in page


def test_after_the_last_story_the_stack_is_done_and_takes_no_more() -> None:
    at, page = step3b(["r", "l"] * 6)
    assert "<b>All 12 stories</b>" in page
    assert "sw-done" in page
    assert "You’d enjoy 6, passed on 6 and weren’t sure about 0." in page
    assert swipe_buttons(at) == {}
