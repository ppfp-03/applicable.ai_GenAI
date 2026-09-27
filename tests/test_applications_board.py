"""Applications board: selecting cards and moving them between stages.

- An application passed on arrival (go("applications", id=...)) is selected
  once; a later click on another card must win instead of being undone on
  every rerun.
- Dropping a card on another lane presses that card's hidden move button
  (ui/js/applications.js); the button moves it through the store and selects it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import store
from ui import tabs

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def app(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def stage_of(at: AppTest, role_id: str) -> str:
    return next(a["stage"] for a in at.session_state[store.APPS] if a["role"] == role_id)


def test_arrival_selects_the_passed_application():
    at = app(**{tabs._PARAMS: {"applications": {"id": "replai-pa"}}, tabs._NONCE: 1})
    assert not at.exception
    assert at.session_state["apps_sel"] == "replai-pa"


def test_a_click_is_not_undone_by_the_arrival_id():
    at = app(**{tabs._PARAMS: {"applications": {"id": "replai-pa"}}, tabs._NONCE: 1})
    at.button(key="ov-app-lazarde-ba").click().run()
    assert at.session_state["apps_sel"] == "lazarde-ba"
    at.run()  # any later rerun keeps the user's choice
    assert at.session_state["apps_sel"] == "lazarde-ba"
    at.button(key="ov-app-bolton-strategy").click().run()
    assert at.session_state["apps_sel"] == "bolton-strategy"


def test_a_new_arrival_selects_again():
    at = app(**{tabs._PARAMS: {"applications": {"id": "replai-pa"}}, tabs._NONCE: 1})
    at.button(key="ov-app-lazarde-ba").click().run()
    at.session_state[tabs._NONCE] = 2  # go("applications", id="replai-pa") again
    at.run()
    assert at.session_state["apps_sel"] == "replai-pa"


def test_every_card_can_move_to_every_other_lane():
    at = app()
    keys = {b.key for b in at.button}
    for a in at.session_state[store.APPS]:
        for k in ("saved", "progress", "applied", "interview"):
            assert (f"mv-{a['role']}--{k}" in keys) == (k != a["stage"]), (a["role"], k)


@pytest.mark.parametrize("role_id, to", [
    ("bolton-strategy", "progress"),   # saved -> in progress
    ("replai-pa", "interview"),        # in progress -> interview
    ("jpmorrow-strategy", "saved"),    # and back
])
def test_dropping_on_a_lane_moves_and_selects_the_card(role_id, to):
    at = app()
    assert stage_of(at, role_id) != to
    at.button(key=f"mv-{role_id}--{to}").click().run()
    assert not at.exception
    assert stage_of(at, role_id) == to
    assert at.session_state["apps_sel"] == role_id
    assert f"mv-{role_id}--{to}" not in {b.key for b in at.button}  # already there


def test_the_board_script_is_on_the_page():
    at = app()
    assert any("__aaApps" in (getattr(h, "body", "") or "") for h in at.get("html"))


def test_the_board_script_survives_streamlits_sanitiser():
    # st.html runs through DOMPurify, which removes a whole script whose text
    # has "<" followed by a letter or "/" (it looks like a tag). The script
    # would then silently never run.
    import re
    js = (Path(__file__).resolve().parents[1] / "ui" / "js" / "applications.js").read_text(encoding="utf-8")
    assert not re.search(r"<[/\w]", js)


def test_the_panel_has_one_real_action_open_role():
    # The panel used to show the application's first action (e.g. "Open prep"),
    # which only raised a toast. Only "Open role" is left, as the primary button.
    at = app()
    keys = {b.key for b in at.button}
    assert "act" not in keys
    open_role = at.button(key="ap-open")
    assert open_role.label == "Open role" and open_role.proto.type == "primary"


def test_no_button_promises_an_interview_prep_that_does_not_exist():
    raw = (Path(__file__).resolve().parents[1] / "data" / "demo.json").read_text(encoding="utf-8")
    assert "Open prep" not in raw
    at = app()
    assert "Open prep" not in {b.label for b in at.button}
