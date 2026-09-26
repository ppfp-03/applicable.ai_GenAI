"""The eight fixed criteria, decided by core/rules.py.

These pin the outcomes the screens show for the demo profile: Deutsch Bank
Shanghai is 5 of 8 with one conflict, UK roles follow the UK answer, and a
high semantic match never overrides a rule.
"""

from __future__ import annotations

from core import rules, store

D = store.data()


def criteria(role_id: str, **answers):
    return rules.evaluate(D.profile, answers, D.role(role_id).raw)


def by_id(crit):
    return {c.id: c for c in crit}


def test_always_eight_criteria_in_fixed_order():
    crit = criteria("replai-pa", uk_work="yes")
    assert [c.id for c in crit] == list(rules.CRITERIA)


def test_deutsch_shanghai_is_five_of_eight_with_one_conflict():
    crit = by_id(criteria("deutsch-shanghai", uk_work="yes"))
    assert crit["language"].status == "not_met"
    assert (crit["language"].have, crit["language"].need) == ("HSK 4", "HSK 6")
    assert crit["permission"].status == "check"  # X1 visa, letter not stated
    assert crit["field"].status == "check"  # "related field" is undecidable
    assert sum(c.status == "met" for c in crit.values()) == 5
    assert rules.verdict(list(crit.values())) == "excluded"


def test_a_certificate_clears_the_language_conflict():
    crit = by_id(criteria("deutsch-shanghai", uk_work="yes", languages={"Mandarin": "HSK 6"}))
    assert crit["language"].status == "met"
    assert rules.verdict(list(crit.values())) == "verify"


def test_the_university_letter_settles_the_china_permit():
    crit = by_id(criteria("deutsch-shanghai", cn_letter=True))
    assert crit["permission"].status == "met"


def test_uk_answer_drives_uk_roles():
    assert by_id(criteria("replai-pa", uk_work="yes"))["permission"].status == "met"
    assert by_id(criteria("replai-pa", uk_work=None))["permission"].status == "check"
    assert by_id(criteria("replai-pa", uk_work="unsure"))["permission"].status == "check"
    # "No": a sponsoring employer stays open, a non-sponsoring one is a conflict.
    assert by_id(criteria("bolton-strategy", uk_work="no"))["permission"].status == "check"
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
