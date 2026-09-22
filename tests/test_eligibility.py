"""The hard constraints, and the line between them and fit.

These tests exist for one reason: eligibility is the part of the product a
user cannot check for themselves, so it has to be the part we can prove.
"""

from __future__ import annotations

import pytest

from oi.contracts import Opportunity, Evidence, Source

from core import eligibility, ranking

PROFILE = {"citizenship": "IT", "graduation_year": 2027}
PREFS = {"countries": ["IT", "CH"]}


def _opp(country="IT", months=3, requirements=None, **kwargs):
    return Opportunity(
        id="x",
        title="Analyst",
        company="Lazarde & Co.",
        city="Milan",
        country=country,
        contract="Internship",
        contract_months=months,
        deadline_days=10,
        verdict="apply",
        why=Evidence(text="because", source=Source(kind="CV", where="p.1")),
        requirements=requirements or [],
        priority=0,
        factors={"profile_fit": 0.0, "preference_fit": 20.0},
        **kwargs,
    )


class TestWorkAuthorisation:
    def test_eu_citizen_in_the_eu_is_free_to_move(self):
        check = eligibility.work_authorisation(PROFILE, _opp(country="IT"))
        assert check.status == "met"
        assert check.source.kind == "RULE"

    def test_switzerland_runs_its_own_regime_even_for_eu_citizens(self):
        check = eligibility.work_authorisation(PROFILE, _opp(country="CH", months=18))
        assert check.status == "met"
        assert "B permit" in check.explanation

    def test_a_short_swiss_contract_takes_the_l_permit_band(self):
        check = eligibility.work_authorisation(PROFILE, _opp(country="CH", months=6))
        assert "L permit" in check.explanation

    def test_an_unknown_pair_asks_rather_than_assuming(self):
        check = eligibility.work_authorisation(PROFILE, _opp(country="US"))
        assert check.status == "confirm"


class TestGraduationWindow:
    def test_inside_the_window_passes(self):
        assert eligibility.graduation_window(PROFILE, [2027, 2028]).status == "met"

    def test_outside_the_window_conflicts(self):
        check = eligibility.graduation_window(PROFILE, [2025, 2026])
        assert check.status == "conflict"
        assert "2027" in check.explanation

    def test_a_posting_that_does_not_say_is_not_an_open_door(self):
        assert eligibility.graduation_window(PROFILE, None).status == "confirm"


class TestLocation:
    def test_a_selected_country_passes_and_is_attributed_to_the_user(self):
        check = eligibility.location(PREFS, _opp(country="IT"))
        assert check.status == "met"
        assert check.source.kind == "YOU"

    def test_an_unselected_country_conflicts(self):
        assert eligibility.location(PREFS, _opp(country="DE")).status == "conflict"


class TestEligibilityDecidesTheVerdict:
    def test_a_conflicting_rule_blocks_whatever_the_score(self):
        opp = _opp(country="DE")
        opp.eligibility = eligibility.evaluate(PROFILE, PREFS, opp, [2027, 2028])
        assert opp.eligibility_status == "conflict"
        assert ranking.verdict_for_opportunity(opp) == "skip"

    def test_an_unsettled_rule_asks_rather_than_waving_through(self):
        # A country the user chose, but one we have no work-authorisation
        # rule for: not having looked is not the same as having cleared it.
        opp = _opp(country="US")
        opp.eligibility = eligibility.evaluate(
            PROFILE, {"countries": ["IT", "CH", "US"]}, opp, [2027, 2028]
        )
        assert opp.eligibility_status == "confirm"
        assert ranking.verdict_for_opportunity(opp) == "clarify"

    def test_a_soft_gap_is_a_gap_not_a_gate(self):
        from oi.contracts import Requirement

        opp = _opp(
            requirements=[
                Requirement(
                    ask="PowerPoint",
                    kind="must",
                    status="confirm",
                    job_source=Source(kind="JOB", where="l.4"),
                )
            ]
        )
        opp.eligibility = eligibility.evaluate(PROFILE, PREFS, opp, [2027, 2028])
        # Every rule passes, so an unanswered question does not close the door.
        assert ranking.verdict_for_opportunity(opp) == "apply"

    def test_a_requirement_the_posting_rules_out_still_blocks(self):
        from oi.contracts import Requirement

        opp = _opp(
            requirements=[
                Requirement(
                    ask="German C1",
                    kind="must",
                    status="conflict",
                    job_source=Source(kind="JOB", where="l.3"),
                )
            ]
        )
        opp.eligibility = eligibility.evaluate(PROFILE, PREFS, opp, [2027, 2028])
        assert ranking.verdict_for_opportunity(opp) == "skip"


class TestProfileFitMoves:
    def test_fit_is_the_share_of_requirements_with_evidence(self):
        from oi.contracts import Requirement

        reqs = [
            Requirement(ask=a, kind="must", status=s,
                        job_source=Source(kind="JOB", where="l.1"))
            for a, s in [("a", "met"), ("b", "met"), ("c", "confirm"), ("d", "met")]
        ]
        assert ranking.profile_fit(reqs) == pytest.approx(18.8, abs=0.1)

    def test_no_requirements_scores_zero_rather_than_full_marks(self):
        assert ranking.profile_fit([]) == 0.0

    def test_reweighting_scales_each_factor_by_its_new_share(self):
        opp = _opp()
        opp.factors = {"profile_fit": 20.0, "preference_fit": 20.0}
        doubled = ranking.score_with(opp, {"profile_fit": 1.0, "preference_fit": 0.0})
        assert doubled == 40
