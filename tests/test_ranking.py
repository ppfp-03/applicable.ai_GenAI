"""Tests for priority scoring and verdicts.

Both are deterministic. A model may explain a score; it never produces one.
"""

from __future__ import annotations

import pytest

from core.ranking import rank, score, verdict_for
from oi.contracts import Evidence, Opportunity, Requirement, Source


def _req(status, kind="must", question_id=None):
    return Requirement(
        ask="Master's, graduating 2027–28",
        kind=kind,
        status=status,
        job_source=Source(kind="JOB", where="§Requirements, l.2"),
        question_id=question_id,
    )


def _opp(opp_id="x", factors=None, requirements=None, priority=0):
    return Opportunity(
        id=opp_id,
        title="Summer Analyst · M&A",
        company="Lazarde & Co.",
        city="Milan",
        contract="Internship",
        deadline_days=6,
        verdict="apply",
        priority=priority,
        why=Evidence(
            text="Your DCF model for a €40M target is the valuation work they ask for.",
            highlight=(5, 32),
            source=Source(kind="CV", where="p.1 · Experience"),
        ),
        requirements=requirements if requirements is not None else [],
        factors=factors or {},
    )


class TestScore:
    def test_sums_the_factors(self):
        opp = _opp(factors={"cv_fit": 34.0, "pref_fit": 27.0, "deadline": 16.4})
        assert score(opp) == 77

    def test_penalties_subtract(self):
        opp = _opp(factors={"cv_fit": 40.0, "penalty": -2.0})
        assert score(opp) == 38

    def test_result_is_clamped_to_the_published_range(self):
        # The UI presents priority as 0-100; a score outside that would make
        # the meter lie about its own scale.
        assert score(_opp(factors={"cv_fit": 300.0})) == 100
        assert score(_opp(factors={"penalty": -50.0})) == 0

    def test_no_factors_scores_zero(self):
        assert score(_opp()) == 0

    def test_is_deterministic(self):
        opp = _opp(factors={"cv_fit": 34.0, "freshness": 9.5})
        assert score(opp) == score(opp) == score(opp)


class TestVerdict:
    def test_all_must_requirements_met_is_apply(self):
        assert verdict_for([_req("met"), _req("met")]) == "apply"

    def test_a_conflict_is_skip(self):
        assert verdict_for([_req("met"), _req("conflict")]) == "skip"

    def test_something_to_confirm_is_clarify(self):
        assert verdict_for([_req("met"), _req("confirm")]) == "clarify"

    def test_a_conflict_outranks_a_confirm(self):
        # A blocking conflict is not softened by an open question elsewhere.
        assert verdict_for([_req("confirm"), _req("conflict")]) == "skip"

    def test_an_unmet_nice_to_have_does_not_block(self):
        reqs = [_req("met"), _req("confirm", kind="nice")]
        assert verdict_for(reqs) == "apply"

    def test_a_passed_deadline_is_closed_whatever_the_requirements(self):
        assert verdict_for([_req("met")], deadline_days=-1) == "closed"

    def test_no_requirements_cannot_be_apply(self):
        # Knowing nothing is not the same as everything being fine.
        assert verdict_for([]) == "clarify"


class TestRank:
    def test_orders_by_verdict_then_priority(self):
        opps = [
            _opp("low-apply", priority=70),
            _opp("high-clarify", priority=95),
            _opp("high-apply", priority=90),
        ]
        opps[1].verdict = "clarify"

        ordered = [o.id for o in rank(opps)]
        # Every apply comes before any clarify, even a higher-scoring one:
        # the list is a decision queue, not a leaderboard.
        assert ordered == ["high-apply", "low-apply", "high-clarify"]

    def test_skip_and_closed_sort_last(self):
        opps = [_opp("a", priority=10), _opp("b", priority=99), _opp("c", priority=50)]
        opps[1].verdict = "skip"
        opps[2].verdict = "closed"
        assert [o.id for o in rank(opps)][0] == "a"

    def test_is_stable_for_equal_keys(self):
        opps = [_opp("first", priority=80), _opp("second", priority=80)]
        assert [o.id for o in rank(opps)] == ["first", "second"]

    def test_does_not_mutate_its_input(self):
        opps = [_opp("a", priority=10), _opp("b", priority=90)]
        rank(opps)
        assert [o.id for o in opps] == ["a", "b"]
