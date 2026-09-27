"""Home's intro guide: the sheet, the walkthrough and the header's "?"."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import store
from ui import home_guide

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def open_home(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = state.pop("stage", "app")
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception
    return at


def page(at: AppTest) -> str:
    return "".join(m.value for m in at.markdown)


def keys(at: AppTest) -> set[str]:
    return {b.key for b in at.button if b.key}


def test_the_first_visit_opens_the_sheet_listing_every_part() -> None:
    at = open_home()
    assert {"hg-start", "hg-close"} <= keys(at)
    text = page(at)
    assert "What this page is for" in text
    for p in home_guide.PARTS:
        assert p.name in text and p.short in text


def test_closing_the_sheet_keeps_it_closed() -> None:
    at = open_home()
    at.button(key="hg-close").click().run()
    assert not at.exception
    assert "hg-start" not in keys(at)
    at.run()
    assert "hg-start" not in keys(at)


def test_show_me_around_walks_every_part_and_ends() -> None:
    at = open_home()
    at.button(key="hg-start").click().run()
    for i, p in enumerate(home_guide.PARTS):
        assert not at.exception
        text = page(at)
        assert f'data-sel=".st-key-tab-home .st-key-{p.key}"' in text
        assert p.what in text and p.how in text
        if i < len(home_guide.PARTS) - 1:
            at.button(key="hg-next").click().run()
    at.button(key="hg-done").click().run()
    assert not at.exception
    assert "aa-tour-mark" not in page(at)
    assert "hg-start" not in keys(at)


def test_skip_ends_the_walkthrough() -> None:
    at = open_home(**{home_guide.WALK: 1})
    at.button(key="hg-skip").click().run()
    assert "aa-tour-mark" not in page(at)


def test_the_question_mark_opens_the_sheet_again() -> None:
    at = open_home(**{home_guide.SEEN: True})
    assert "hg-start" not in keys(at)
    at.button(key="ib-help").click().run()
    assert not at.exception
    assert "hg-start" in keys(at)


def test_nothing_shows_during_the_first_run_tour() -> None:
    at = open_home(stage="tour")
    assert "hg-start" not in keys(at)
    assert "What this page is for" not in page(at)


def test_every_part_is_a_container_on_home() -> None:
    home = (Path(__file__).resolve().parents[1] / "views" / "home.py").read_text(encoding="utf-8")
    for p in home_guide.PARTS:
        assert f'key="{p.key}"' in home
