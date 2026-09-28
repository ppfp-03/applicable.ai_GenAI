"""The eight fixed criteria, as the screens get them (core.store.view).

All eight come from the canonical engine (core/eligibility.py ->
oi.intelligence.eligibility -> core/eligibility_view.py). These pin the
outcomes the screens show for the demo profile: Deutsch Bank Shanghai is 6 of
8 and "to verify" (Mandarin HSK is outside canonical eligibility, so it is a
limitation, not a conflict), and UK roles follow the UK answer.
"""

from __future__ import annotations

from core import rules, store

D = store.data()


def criteria(role_id: str, **answers):
    return store.view(D.role(role_id), answers).criteria


def by_id(crit):
    return {c.id: c for c in crit}


def test_always_eight_criteria_in_fixed_order():
    crit = criteria("replai-pa", uk_work="yes")
    assert [c.id for c in crit] == list(rules.CRITERIA)


def test_deutsch_shanghai_is_six_of_eight_and_to_verify():
    v = store.view(D.role("deutsch-shanghai"), {"uk_work": "yes"})
    crit = by_id(v.criteria)
    assert crit["permission"].status == "check"  # no China work-authorisation declaration
    assert crit["field"].status == "check"  # "related field" is undecidable
    assert crit["language"].status == "met"  # no CEFR requirement: HC_LANGUAGE not applicable
    assert crit["language"].rule.endswith("→ not_applicable")
    assert v.met == 6
    assert v.standing == "verify"


def test_hsk_is_a_limitation_that_never_changes_the_standing():
    before = store.view(D.role("deutsch-shanghai"), {"uk_work": "yes"})
    after = store.view(D.role("deutsch-shanghai"), {"uk_work": "yes", "languages": {"Mandarin": "HSK 6"}})
    assert [n.name for n in before.limitations] == ["Mandarin level"]
    assert "HSK 6" in before.limitations[0].text and "HSK 4" in before.limitations[0].text
    assert before.standing == after.standing == "verify"
    assert before.criteria == after.criteria


def test_a_cefr_certificate_is_read_by_the_canonical_language_rule(monkeypatch):
    profile = {**D.profile, "languages": {**D.profile["languages"], "English": "B2"}}
    monkeypatch.setattr(D, "profile", profile)
    low = by_id(criteria("replai-pa", uk_work="yes"))["language"]
    assert (low.status, low.have, low.need) == ("not_met", "B2", "C1")
    cert = by_id(criteria("replai-pa", uk_work="yes", languages={"English": "C1"}))["language"]
    assert cert.status == "met"


def test_uk_answer_drives_uk_roles():
    assert by_id(criteria("replai-pa", uk_work="yes"))["permission"].status == "met"
    assert by_id(criteria("replai-pa", uk_work=None))["permission"].status == "check"
    assert by_id(criteria("replai-pa", uk_work="unsure"))["permission"].status == "check"
    # "No": a sponsoring employer is met (HC_WORK_AUTH), a non-sponsoring one is a conflict.
    assert by_id(criteria("bolton-strategy", uk_work="no"))["permission"].status == "met"
    assert by_id(criteria("replai-pa", uk_work="no"))["permission"].status == "not_met"


def test_swiss_role_asks_instead_of_reading_citizenship_as_a_permit():
    crit = by_id(criteria("roshe-basel"))
    assert crit["permission"].status == "check"
    assert "permit" not in crit["permission"].value.lower()


def test_level_gap_handles_known_scales_only():
    assert rules.level_gap("HSK 4", "HSK 6") == -2
    assert rules.level_gap("C1", "B2") == 1
    assert rules.level_gap("native", "C2") > 0
    assert rules.level_gap(None, "C1") is None
    assert rules.level_gap("HSK 4", "C1") is None
