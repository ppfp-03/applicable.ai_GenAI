"""Ranking arithmetic and the orders the screens show.

The expected lists are the dashboard/matches top five after "Yes" and the
question screen's preview for each answer. Every criterion comes from the
canonical engine, so they differ from the approved mockups wherever the
mockups assumed a fact nobody declared: sponsoring Singapore roles are "to
verify" (no Singapore declaration), not eligible. Mandarin HSK is outside
canonical eligibility, so Deutsch Bank Shanghai (HSK 6) is "to verify", not
excluded.
"""

from __future__ import annotations

from core import ranking, store


def top(uk, n=5, **kw):
    return [(v.mono, v.shown) for v in store.ranked({"uk_work": uk}, **kw)[:n]]


def test_weights_sum_to_one():
    assert abs(sum(store.data().weights.values()) - 1) < 1e-9


def test_shown_rounds_half_up():
    assert ranking.shown(74.5) == 75
    assert ranking.shown(74.49) == 74


def test_replai_score_is_the_weighted_sum():
    v = store.view(store.data().role("replai-pa"), {"uk_work": "yes"})
    assert round(v.raw, 1) == 87.3  # 0.40·92 + 0.25·88 + 0.20·90 + 0.15·70
    assert v.shown == 87


def test_to_verify_roles_lose_the_penalty():
    v = store.view(store.data().role("replai-pa"), {"uk_work": None})
    assert v.standing == "verify"
    assert v.shown == 72  # 87 − 15 until verified


def test_top_five_after_yes():
    assert top("yes") == [("RP", 87), ("BC", 83), ("LZ", 81), ("MS", 77), ("DB", 65)]


def test_question_preview_for_no_and_not_sure():
    # "No" + sponsorship offered is MET under HC_WORK_AUTH; "not offered" is
    # a conflict (Replai, Lazarde are excluded).
    assert [m for m, _ in top("no")] == ["BC", "MS", "DB", "NE", "JP"]
    assert [m for m, _ in top("unsure")] == ["RP", "BC", "LZ", "DB", "MS"]


def test_onboarding_shortlist_before_the_answer():
    assert top(None, as_of=store.data().profile["onboarded"]) == [
        ("RP", 72), ("BC", 68), ("LZ", 66), ("DB", 65), ("MS", 62)
    ]


def test_movement_after_yes():
    # Every role in the top five is "to verify" before the answer; "Yes"
    # verifies the UK ones, which lifts Morgan above Deutsch Bank Shanghai.
    moves = store.movement({"uk_work": None}, {"uk_work": "yes"})
    assert moves == {
        "replai-pa": "—", "bolton-strategy": "—", "lazarde-ba": "—",
        "morgan-product": "↑ 1", "deutsch-shanghai": "↓ 1",
    }


def test_excluded_roles_are_never_ranked():
    ids = {v.id for v in store.ranked({"uk_work": "no"}, include_new=True)}
    assert not {"replai-pa", "lazarde-ba"} & ids  # sponsorship not offered
