"""The role page's buttons do what they say.

- The foot of the panel leads back: to the application when there is one for
  the role, else to the matches. "Report a mistake" (a toast) is gone.
- "Open job posting" opens a notice that the posting is a synthetic demo one,
  instead of a toast pretending to open it.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import eligibility, store

APP = str(Path(__file__).resolve().parents[1] / "app.py")
NOTICE = "This is a synthetic demo posting"


def role_page(role_id: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state[store.STAGE] = "app"
    at.session_state["role_id"] = role_id
    at.run()
    at.switch_page("views/role.py")
    return at.run()


def text(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_no_report_a_mistake_button_is_left():
    at = role_page("jpmorrow-strategy")
    assert not at.exception
    assert "Report a mistake" not in {b.label for b in at.button}


def test_back_leads_to_the_application_when_there_is_one():
    at = role_page("jpmorrow-strategy")  # J.P. Morrow is in the user's applications
    assert at.button(key="back-f").label == "‹ Applications"


def test_back_leads_to_matches_without_an_application():
    at = role_page("deutsch-shanghai")  # no application for it
    assert at.button(key="back-f").label == "‹ Matches"


def test_open_job_posting_says_the_posting_is_a_demo_one():
    at = role_page("jpmorrow-strategy")
    assert NOTICE not in text(at)
    at.button(key="posting").click().run()  # the panel's "Open job posting"
    assert not at.exception
    assert NOTICE in text(at)


# ───────────── Permission to work outside the UK: one question ─────────────
#
# AppTest reruns the whole page for a click inside a dialog, where the dialog
# is no longer open, so the answers themselves are set as the dialog sets them:
# store.set_work_answer writes the one work authorization declaration
# (store.WORK_AUTH; D-050); the browser run covers the clicks.

#: What each answer declares for the country, as the store keeps it.
DECLARES = {
    "yes": lambda c: {"authorized": [c], "no_sponsorship": [c]},
    "no": lambda c: {"not_authorized": [c], "sponsorship": [c]},
    "unsure": lambda c: {},
}


#: The demo persona's UK answer ("yes"), carried into the declaration the
#: first answer starts (store.declaration).
PERSONA = {"authorized": ["GB"], "no_sponsorship": ["GB"]}


def answered(role_id: str, choice: str, country: str = "SG") -> AppTest:
    at = role_page(role_id)
    decl = DECLARES[choice](country)
    at.session_state[store.WORK_AUTH] = {k: PERSONA.get(k, []) + decl.get(k, [])
                                         for k in store.WORK_AUTH_LISTS}
    return at.run()


def live_answers(at: AppTest) -> dict:
    """The answers as store.answers() gives them: the declaration included,
    the UK answer read from it."""
    decl = at.session_state[store.WORK_AUTH]
    uk = eligibility.work_answer(eligibility.declared(decl, "GB"))
    return {**at.session_state[store.ANSWERS], store.WORK_AUTH: decl, "uk_work": uk}


def permission(at: AppTest, role_id: str = "jpmorrow-strategy"):
    return store.view(store.data().role(role_id), live_answers(at)).criterion("permission")


def test_the_panel_asks_the_question_for_the_roles_country():
    at = role_page("jpmorrow-strategy")  # Singapore
    assert permission(at).status == "check"
    assert at.button(key="ask-wa").label == "Answer 1 question"
    at.button(key="ask-wa").click().run()
    assert not at.exception
    assert "Can you work in <b>Singapore</b> without visa sponsorship?" in text(at)
    assert {"wq-yes", "wq-no", "wq-unsure"} <= {b.key for b in at.button}


def test_yes_settles_it_and_the_role_becomes_eligible():
    at = answered("jpmorrow-strategy", "yes")
    assert not at.exception
    assert permission(at).status == "met"
    assert store.view(store.data().role("jpmorrow-strategy"), live_answers(at)).standing == "eligible"


def test_needing_sponsorship_follows_the_employer():
    assert permission(answered("jpmorrow-strategy", "no")).status == "met"  # J.P. Morrow sponsors


def test_not_sure_keeps_it_to_verify_and_asks_again():
    at = answered("jpmorrow-strategy", "unsure")
    assert permission(at).status == "check"
    assert at.button(key="ask-wa").label == "Answer 1 question"


def test_needing_sponsorship_where_it_is_not_offered_is_a_conflict_you_can_revisit():
    # Deutsch Bank Shanghai requires a permit already held (sponsorship not offered).
    at = answered("deutsch-shanghai", "no", country="CN")
    assert permission(at, "deutsch-shanghai").status == "not_met"
    assert at.button(key="ask-wa").label == "Change your answer"


def test_one_answer_settles_every_role_in_that_country_only():
    at = answered("jpmorrow-strategy", "yes")
    ans = live_answers(at)
    views = {r.id: store.view(r, ans) for r in store.data().roles}
    assert views["nestella-strategy"].criterion("permission").status == "met"  # also Singapore
    assert views["roshe-basel"].criterion("permission").status == "check"      # Switzerland: not answered
    assert views["replai-pa"].criterion("permission").status == "met"          # UK: its own answer


def test_an_eligible_role_you_already_applied_to_is_not_started_again():
    at = answered("jpmorrow-strategy", "yes")  # J.P. Morrow is at Interview
    keys = {b.key for b in at.button}
    assert "apply" not in keys and "view-app" in keys
    at.button(key="view-app").click().run()
    stage = next(a["stage"] for a in at.session_state[store.APPS] if a["role"] == "jpmorrow-strategy")
    assert stage == "interview"


def test_the_notice_opens_for_every_role():
    at = role_page("deutsch-shanghai")
    at.button(key="posting").click().run()
    assert NOTICE in text(at)


# ───────────── One Requirements list, and the role panel ─────────────


def test_the_header_has_no_buttons_every_action_is_in_the_panel():
    at = role_page("jpmorrow-strategy")
    keys = {b.key for b in at.button}
    assert "Check again" not in {b.label for b in at.button}
    assert "back" not in keys  # the way back is only in the panel
    assert {"view-app", "posting", "back-f"} <= keys


def test_the_open_requirement_comes_first_with_its_action():
    at = role_page("jpmorrow-strategy")  # permission to work in Singapore is open
    page = text(at)
    assert "They ask · Permission to work" in page and "Right to work in Singapore" in page
    assert page.index("Right to work in Singapore") < page.index("Based in Singapore")
    assert at.button(key="ask-wa").label == "Answer 1 question"


def test_a_met_requirement_opens_on_a_tap_and_closes_again():
    at = role_page("jpmorrow-strategy")
    assert "How it was decided" not in text(at).split("Based in Singapore")[1]
    at.button(key="ov-rqh-location").click().run()
    assert not at.exception
    after = text(at).split("Based in Singapore")[1]
    # Opened: the rule's reason in words; its ID and version stay internal.
    assert "How it was decided" in after and "HC_LOCATION" not in after and "v0." not in after
    at.button(key="ov-rqh-location").click().run()
    assert "How it was decided" not in text(at).split("Based in Singapore")[1]


def test_every_role_page_renders():
    for r in store.data().roles:
        at = role_page(r.id)
        assert not at.exception, r.id
        assert "Requirements" in text(at)
