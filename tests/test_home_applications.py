"""Home's Applications card: the stages filter a list, a row expands in place.

- The stage chips are a filter: the chosen one is lit, and only its
  applications are listed. It starts on "In progress" when there is any.
- Tapping an application expands it (one at a time) with its details and
  buttons; tapping it again collapses it.
- Changing stage collapses whatever was open.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import store

APP = str(Path(__file__).resolve().parents[1] / "app.py")
STAGES = ("saved", "progress", "applied", "interview")


def home() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    return at.run()


def roles_in(at: AppTest, stage: str) -> list[str]:
    return [a["role"] for a in at.session_state[store.APPS] if a["stage"] == stage]


def listed(at: AppTest) -> set[str]:
    """Applications shown in the Home card's list (one row button each)."""
    return {b.key[len("ov-ah-"):] for b in at.button if (b.key or "").startswith("ov-ah-")}


def test_starts_on_in_progress():
    at = home()
    assert not at.exception
    assert at.session_state["home_apps_filter"] == "progress"
    assert listed(at) == set(roles_in(at, "progress"))


def test_every_stage_is_a_chip_with_its_count():
    at = home()
    for stage in STAGES:
        chip = at.button(key=f"af-{stage}")
        assert f"**{len(roles_in(at, stage))}**" in chip.label


@pytest.mark.parametrize("stage", STAGES)
def test_a_chip_lists_only_that_stage(stage):
    at = home()
    at.button(key=f"af-{stage}").click().run()
    assert at.session_state["home_apps_filter"] == stage
    assert listed(at) == set(roles_in(at, stage))


def test_an_empty_stage_says_so():
    at = home()
    at.session_state[store.APPS] = [a for a in at.session_state[store.APPS] if a["stage"] != "applied"]
    at.button(key="af-applied").click().run()
    assert listed(at) == set()
    assert any("No applications in Applied yet." in m.value for m in at.markdown)


def test_a_row_expands_and_collapses():
    at = home()
    role = roles_in(at, "progress")[0]
    at.button(key=f"ov-ah-{role}").click().run()
    assert at.session_state["home_apps_open"] == role
    keys = {b.key for b in at.button}
    assert {f"apa1-{role}", f"apa2-{role}"} <= keys
    at.button(key=f"ov-ah-{role}").click().run()
    assert at.session_state["home_apps_open"] is None
    assert f"apa1-{role}" not in {b.key for b in at.button}


def test_only_one_row_is_open_at_a_time():
    at = home()
    first, second = roles_in(at, "progress")[:2]
    at.button(key=f"ov-ah-{first}").click().run()
    at.button(key=f"ov-ah-{second}").click().run()
    keys = {b.key for b in at.button}
    assert f"apa1-{second}" in keys and f"apa1-{first}" not in keys


def test_changing_stage_collapses_the_open_row():
    at = home()
    role = roles_in(at, "progress")[0]
    at.button(key=f"ov-ah-{role}").click().run()
    at.button(key="af-saved").click().run()
    assert at.session_state["home_apps_open"] is None


def test_the_wallet_is_gone():
    at = home()
    keys = {b.key or "" for b in at.button}
    assert not any(k.startswith(("wpick-", "wf-")) for k in keys)
