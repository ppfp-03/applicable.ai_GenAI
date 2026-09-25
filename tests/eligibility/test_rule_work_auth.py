"""HC_WORK_AUTH: explicit requirement only, declarations only, never citizenship."""

from __future__ import annotations

import pytest

from oi.intelligence.eligibility import RuleStatus, UnknownCause

from . import builders as b
from .rule_helpers import outcomes_for, single

CID = "HC_WORK_AUTH"
UK = [("GB", "London")]


def declared(authorized, sponsorship, country="GB", **kwargs):
    return b.candidate(work_auth=[(country, authorized, sponsorship)], **kwargs)


def sponsorship(policy: str, country: str | None = None) -> dict:
    params = {"kind": "work_auth", "employer_sponsorship": policy}
    if country:
        params["country_code"] = country
    return params


def path(country: str, leaf: str) -> str:
    return f"declarations.work_authorizations.{country}.{leaf}"


def test_not_required_by_the_job_is_not_applicable() -> None:
    # D7: no implicit right-to-work check, even for an undeclared country.
    (outcome,) = outcomes_for(CID, b.candidate(), b.job(locations=UK))
    assert outcome.status is RuleStatus.NOT_APPLICABLE
    assert outcome.requirement_id is None


@pytest.mark.parametrize("sponsor", [True, False, None])
def test_authorized_is_met_whatever_the_rest(sponsor) -> None:
    outcome = single(CID, declared(True, sponsor), locations=UK)
    assert outcome.status is RuleStatus.MET
    assert outcome.candidate_evidence_ids == [b.work_auth_evidence_id("GB")]
    assert "ev-job-location-0" in outcome.job_evidence_ids


@pytest.mark.parametrize("authorized", [False, None])
def test_sponsorship_needed_and_offered_is_met(authorized) -> None:
    # D8: sponsorship compatible with employer policy is MET.
    outcome = single(CID, declared(authorized, True), sponsorship("offered"), locations=UK)
    assert outcome.status is RuleStatus.MET


@pytest.mark.parametrize("authorized", [False, None])
def test_sponsorship_needed_and_not_offered_is_conflict(authorized) -> None:
    outcome = single(
        CID, declared(authorized, True), sponsorship("not_offered"), locations=UK
    )
    assert outcome.status is RuleStatus.CONFLICT


@pytest.mark.parametrize("params", [None, sponsorship("not_stated")])
def test_sponsorship_needed_and_policy_unknown_is_unknown(params) -> None:
    outcome = single(CID, declared(False, True), params, locations=UK)
    assert outcome.unknown_cause is UnknownCause.JOB_PARAMETER_MISSING
    assert outcome.missing_field_paths == []


def test_no_declaration_asks_for_both_facts() -> None:
    outcome = single(CID, b.candidate(), sponsorship("not_offered"), locations=UK)
    assert outcome.status is RuleStatus.UNKNOWN
    assert outcome.missing_field_paths == [
        path("GB", "authorized_to_work"),
        path("GB", "requires_sponsorship"),
    ]


def test_citizenship_is_never_work_authorization() -> None:
    # A GB citizenship is declared, but no GB work declaration: still unknown.
    candidate = b.candidate(citizenships=["GB"])
    outcome = single(CID, candidate, sponsorship("not_offered"), locations=UK)
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING


def test_declaration_for_another_country_does_not_count() -> None:
    outcome = single(CID, declared(True, False, country="NL"), locations=UK)
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING


@pytest.mark.parametrize(
    ("authorized", "sponsor", "missing"),
    [
        (False, None, ["requires_sponsorship"]),
        (None, None, ["authorized_to_work", "requires_sponsorship"]),
        (False, False, ["authorized_to_work"]),
        (None, False, ["authorized_to_work"]),
    ],
)
def test_incomplete_or_inconsistent_declarations_ask(authorized, sponsor, missing) -> None:
    outcome = single(
        CID, declared(authorized, sponsor), sponsorship("not_offered"), locations=UK
    )
    assert outcome.unknown_cause is UnknownCause.CANDIDATE_MISSING
    assert outcome.missing_field_paths == sorted(path("GB", leaf) for leaf in missing)
    assert outcome.candidate_evidence_ids == [b.work_auth_evidence_id("GB")]


def test_parameter_country_overrides_job_location() -> None:
    candidate = b.candidate(work_auth=[("GB", False, True), ("IE", True, False)])
    outcome = single(
        CID, candidate, sponsorship("not_offered", country="IE"), locations=UK
    )
    assert outcome.status is RuleStatus.MET


@pytest.mark.parametrize(
    "locations", [[("GB", "London"), ("NL", "Amsterdam")], [], [(None, "Remote")]]
)
def test_no_single_job_country_is_ambiguous(locations) -> None:
    outcome = single(CID, declared(True, False), locations=locations)
    assert outcome.unknown_cause is UnknownCause.JOB_DATA_AMBIGUOUS


def test_unspecified_modality_softens_a_sponsorship_conflict() -> None:
    outcome = single(
        CID,
        declared(False, True),
        sponsorship("not_offered"),
        modality="unspecified",
        locations=UK,
    )
    assert outcome.unknown_cause is UnknownCause.NON_MANDATORY_MISMATCH
