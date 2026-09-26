"""Onboarding step 3b: every swipe updates "What we're learning about you"."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import explore, store
from ui.html import esc

ROOT = Path(__file__).resolve().parents[1]
ONBOARDING = str(ROOT / "views" / "onboarding.py")
STORIES = json.loads((ROOT / "data" / "stories.json").read_text("utf-8"))["stories"]
#: Step 3 opens only after step 2's mandatory work authorization declaration.
DECLARED = {"authorized": ["IT"], "sponsorship": []}


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
    at.session_state[store.WORK_AUTH] = DECLARED
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


# --- Explore comes first and is not optional; Fine-tune confirms (D-045) ----

#: Likes "Conversion drop" (Product analytics, Fintech) and "Launch review"
#: (Product management, Fintech); passes or is unsure about the rest.
SWIPES = ["r", "l", "l", "u", "u", "l", "l", "u", "l", "l", "r", "u"]


def page_of(at: AppTest) -> str:
    return "".join(m.value for m in at.markdown)


def test_every_story_names_an_industry_or_none() -> None:
    industries = {s["industry"] for s in STORIES}
    assert None in industries and "Fintech" in industries


def test_industries_follow_likes_and_drop_what_was_passed() -> None:
    assert explore.industries(STORIES, SWIPES) == ["Fintech"]
    assert explore.industries(STORIES, ["r", "l"]) == []  # Fintech liked once, passed once
    assert explore.industries(STORIES, ["u", "u", "r"]) == []  # a story without an industry


def test_explore_is_the_first_preferences_step_and_cannot_be_skipped() -> None:
    at, page = step3b()
    assert "Skip for now" not in [b.label for b in at.button]
    assert at.button(key="next").disabled
    assert "oo-to3a" not in [b.key for b in at.button]  # Fine-tune waits for every story
    assert "1 · Explore" in page and "2 · Fine-tune" in page
    assert "Describe" not in page
    # No jumping past Explore from the step bar either.
    assert {b.key for b in at.button if b.key and b.key.startswith("oo-st")} == {"oo-st1", "oo-st2", "oo-st3"}


def test_after_every_story_continue_opens_fine_tune_with_the_suggestions() -> None:
    at, _ = step3b(SWIPES)
    assert not at.button(key="next").disabled
    at.button(key="next").click().run()

    assert not at.exception
    assert at.session_state["ob_step"] == "3a"
    rows = [(r["field"], r["values"], r["level"]) for r in at.session_state["ob_prefs"]]
    assert rows == [
        ("role_family", ["Product analytics"], "important"),
        ("role_family", ["Product management"], "important"),
        ("industry", ["Fintech"], "important"),
        ("city", ["London", "Singapore", "Shanghai"], "important"),
        ("mode", ["Hybrid"], "nice"),
    ]
    page = page_of(at)
    for gone in ["Your ideal internship", "Describe it in your own words", "In 3 years I want to be"]:
        assert gone not in page
    assert "Product analytics roles" in page and "Suggested by your swipes" in page


def fine_tune(verdicts=SWIPES) -> AppTest:
    at, _ = step3b(verdicts)
    at.button(key="next").click().run()
    assert not at.exception
    return at


def test_nothing_counts_until_find_my_roles() -> None:
    at = fine_tune()
    assert "confirmed_preferences" not in at.session_state

    at.button(key="next").click().run()

    assert not at.exception
    assert at.session_state["ob_step"] == "4"
    assert at.session_state["confirmed_preferences"] == at.session_state["ob_prefs"]


def test_a_level_change_shows_in_the_live_preview() -> None:
    at = fine_tune()
    at.button(key="oo-imp43").click().run()  # Hybrid work: Don't mind

    assert at.session_state["ob_prefs"][4]["level"] == "none"
    assert "Hybrid work<b>" not in page_of(at)  # no weight, no share in the bar


def test_fine_tune_cannot_be_confirmed_without_a_weighted_preference() -> None:
    at = fine_tune()
    for r in range(len(at.session_state["ob_prefs"])):
        at.button(key=f"oo-imp{r}3").click().run()

    assert at.button(key="next").disabled
    assert "Mark at least one preference to continue" in page_of(at)


def test_without_likes_fine_tune_offers_only_the_declared_rows() -> None:
    at = fine_tune(["l"] * 12)
    assert [r["field"] for r in at.session_state["ob_prefs"]] == ["city", "mode"]
    assert "Like a few stories in Explore to get suggestions." in page_of(at)
