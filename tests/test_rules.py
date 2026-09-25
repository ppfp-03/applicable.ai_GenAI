"""Tests for deterministic eligibility.

Work authorisation is never judged by a model. These tests pin the rules the
product relies on, including the Swiss permit table for EU/EFTA citizens from
design-system/10-ux-architecture.md.
"""

from __future__ import annotations

import pytest

from core.rules import RULES_VERSION, swiss_permit_for_eu_citizen, work_authorisation


class TestSwissPermitTable:
    """The three bands in the Swiss permit table, plus the unknown case."""

    def test_up_to_three_months_needs_no_permit(self):
        outcome = swiss_permit_for_eu_citizen(contract_months=3)
        assert outcome.status == "met"
        assert "No permit needed" in outcome.explanation

    def test_between_three_and_twelve_months_is_an_l_permit(self):
        outcome = swiss_permit_for_eu_citizen(contract_months=6)
        assert outcome.status == "met"
        assert "L permit" in outcome.explanation

    def test_twelve_months_or_more_is_a_b_permit(self):
        outcome = swiss_permit_for_eu_citizen(contract_months=18)
        assert outcome.status == "met"
        assert "B permit" in outcome.explanation
        assert "5 years" in outcome.explanation

    def test_the_boundary_at_twelve_months_is_a_b_permit(self):
        # 12 is the first month of the B band, not the last of the L band.
        assert "B permit" in swiss_permit_for_eu_citizen(12).explanation
        assert "L permit" in swiss_permit_for_eu_citizen(11).explanation

    def test_the_boundary_at_three_months_needs_no_permit(self):
        assert "No permit" in swiss_permit_for_eu_citizen(3).explanation
        assert "L permit" in swiss_permit_for_eu_citizen(4).explanation

    def test_unknown_duration_asks_rather_than_guesses(self):
        # The posting did not say. Picking a band here would be inventing a
        # fact about the user's legal status -- the one thing we never do.
        outcome = swiss_permit_for_eu_citizen(contract_months=None)
        assert outcome.status == "confirm"
        assert outcome.evidence is None

    def test_every_outcome_carries_a_rule_source(self):
        for months in (3, 6, 18):
            outcome = swiss_permit_for_eu_citizen(months)
            assert outcome.evidence is not None
            assert outcome.evidence.source.kind == "RULE"
            # The locator names the rule that fired, so it can be audited.
            assert "CH" in outcome.evidence.source.where

    def test_rules_are_versioned(self):
        # Rules change with the law; an outcome must be traceable to a version.
        assert RULES_VERSION


class TestWorkAuthorisation:
    """The entry point that dispatches by country and citizenship."""

    def test_italian_citizen_in_italy_is_met(self):
        outcome = work_authorisation(
            citizenship="IT", country="IT", contract_months=3
        )
        assert outcome.status == "met"

    def test_eu_citizen_in_switzerland_uses_the_permit_table(self):
        outcome = work_authorisation(
            citizenship="IT", country="CH", contract_months=18
        )
        assert outcome.status == "met"
        assert "B permit" in outcome.explanation

    def test_unknown_citizenship_asks(self):
        outcome = work_authorisation(
            citizenship=None, country="CH", contract_months=18
        )
        assert outcome.status == "confirm"

    def test_country_we_have_no_rule_for_asks_rather_than_assumes(self):
        # Silence is not permission. With no rule, we ask.
        outcome = work_authorisation(
            citizenship="IT", country="JP", contract_months=12
        )
        assert outcome.status == "confirm"

    @pytest.mark.parametrize("months", [0, -1])
    def test_nonsensical_duration_is_rejected(self, months):
        with pytest.raises(ValueError):
            swiss_permit_for_eu_citizen(contract_months=months)
