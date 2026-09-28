"""Ranking-engine primitives in ``oi.intelligence.ranking``.

These tests cover the production engine only. The demo ranking in
``core/ranking.py`` keeps its own tests in ``test_ranking.py``.

The weights below are the current development configuration approved by the
ranking owner; they are not a frozen shared ``RankingConfig``.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from oi.contracts import CandidatePreferences, JobLocation, JobRecord, SupportedText
from oi.intelligence import ranking
from oi.intelligence.ranking import (
    FactorScores,
    InvalidFactorValue,
    InvalidTimestamp,
    InvalidWeights,
    ScoredJob,
    assess_deadline_urgency,
    assess_freshness,
    assess_preference_fit,
    availability_exclusion,
    compute_priority_score,
    order_by_priority,
    profile_fit_from,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "v0.2.0-draft"

DEV_WEIGHTS = {
    "profile_fit": 0.40,
    "preference_fit": 0.25,
    "deadline_urgency": 0.20,
    "freshness": 0.15,
}

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
HORIZON = 30


def job(**update) -> JobRecord:
    data = json.loads((FIXTURE_ROOT / "job_record.json").read_text())
    return JobRecord.model_validate(data).model_copy(update=update)


def preferences(**update) -> CandidatePreferences:
    data = json.loads((FIXTURE_ROOT / "candidate_profile.json").read_text())
    return CandidatePreferences.model_validate({**data["preferences"], **update})


def scored(job_id: str, **factors) -> ScoredJob:
    return ScoredJob(job_id, compute_priority_score(FactorScores(**factors), DEV_WEIGHTS))


# --- Factor values and weights ---------------------------------------------


def test_all_four_factors_give_the_plain_weighted_sum():
    result = compute_priority_score(
        FactorScores(0.9, 0.8, 0.5, 0.6), DEV_WEIGHTS
    )
    assert result.score == pytest.approx(0.40 * 0.9 + 0.25 * 0.8 + 0.20 * 0.5 + 0.15 * 0.6)
    assert result.missing == ()
    assert dict(result.effective_weights) == pytest.approx(DEV_WEIGHTS)
    assert dict(result.configured_weights) == DEV_WEIGHTS


def test_one_missing_factor_renormalizes_the_others():
    result = compute_priority_score(
        FactorScores(profile_fit=0.9, preference_fit=0.8, freshness=0.6), DEV_WEIGHTS
    )
    assert result.missing == ("deadline_urgency",)
    assert dict(result.effective_weights) == pytest.approx(
        {"profile_fit": 0.50, "preference_fit": 0.3125, "freshness": 0.1875}
    )
    assert "deadline_urgency" not in result.effective_weights
    assert result.score == pytest.approx(0.50 * 0.9 + 0.3125 * 0.8 + 0.1875 * 0.6)


def test_several_missing_factors_renormalize_over_what_remains():
    result = compute_priority_score(
        FactorScores(profile_fit=0.7, freshness=0.2), DEV_WEIGHTS
    )
    assert result.missing == ("preference_fit", "deadline_urgency")
    assert dict(result.effective_weights) == pytest.approx(
        {"profile_fit": 0.40 / 0.55, "freshness": 0.15 / 0.55}
    )
    assert math.fsum(result.effective_weights.values()) == pytest.approx(1.0)
    assert result.score == pytest.approx((0.40 * 0.7 + 0.15 * 0.2) / 0.55)


def test_all_factors_missing_gives_no_score():
    result = compute_priority_score(FactorScores(), DEV_WEIGHTS)
    assert result.score is None
    assert result.missing == ranking.FACTOR_NAMES
    assert dict(result.effective_weights) == {}
    assert dict(result.factors) == dict.fromkeys(ranking.FACTOR_NAMES)


def test_missing_factor_is_not_treated_as_zero():
    missing = compute_priority_score(
        FactorScores(profile_fit=0.8, preference_fit=0.8, freshness=0.8), DEV_WEIGHTS
    )
    zero = compute_priority_score(
        FactorScores(0.8, 0.8, 0.0, 0.8), DEV_WEIGHTS
    )
    assert missing.factors["deadline_urgency"] is None
    assert missing.score == pytest.approx(0.8)
    assert zero.score == pytest.approx(0.64)
    assert missing.score != pytest.approx(zero.score)


@pytest.mark.parametrize(
    "bad", [-0.01, 1.01, float("nan"), float("inf"), True, "0.5", [0.5]]
)
def test_invalid_factor_value_is_rejected_not_clipped(bad):
    with pytest.raises(InvalidFactorValue):
        FactorScores(profile_fit=bad)


def test_boundary_factor_values_are_accepted():
    scores = FactorScores(0, 1, 0.0, 1.0)
    assert scores.as_dict() == {
        "profile_fit": 0.0,
        "preference_fit": 1.0,
        "deadline_urgency": 0.0,
        "freshness": 1.0,
    }


@pytest.mark.parametrize(
    "weights",
    [
        {**DEV_WEIGHTS, "freshness": 0.20},                       # sums to 1.05
        {k: v for k, v in DEV_WEIGHTS.items() if k != "freshness"},
        {**DEV_WEIGHTS, "prestige": 0.0},
        {**DEV_WEIGHTS, "freshness": -0.15, "profile_fit": 0.70},  # negative
        {**DEV_WEIGHTS, "freshness": float("nan")},
        {**DEV_WEIGHTS, "freshness": float("inf")},
        {**DEV_WEIGHTS, "freshness": float("-inf")},
        {**DEV_WEIGHTS, "freshness": "0.15"},
        {**DEV_WEIGHTS, "freshness": True, "profile_fit": -0.60},  # bool
        dict.fromkeys(DEV_WEIGHTS, 0.0),                           # all zero
    ],
)
def test_invalid_weight_configuration_is_rejected(weights):
    with pytest.raises(InvalidWeights):
        compute_priority_score(FactorScores(0.5, 0.5, 0.5, 0.5), weights)


def test_huge_integers_raise_the_module_exceptions():
    with pytest.raises(InvalidFactorValue) as factor_error:
        FactorScores(profile_fit=10**400)
    assert isinstance(factor_error.value.__cause__, OverflowError)
    with pytest.raises(InvalidWeights) as weight_error:
        ranking.validate_weights({**DEV_WEIGHTS, "freshness": 10**400})
    assert isinstance(weight_error.value.__cause__, OverflowError)


def test_weights_within_the_sum_tolerance_are_accepted():
    weights = {**DEV_WEIGHTS, "profile_fit": 0.40 + 5e-10}
    assert ranking.validate_weights(weights)["profile_fit"] == 0.40 + 5e-10


ZERO_FRESHNESS = {
    "profile_fit": 0.50,
    "preference_fit": 0.25,
    "deadline_urgency": 0.25,
    "freshness": 0.0,
}


def test_zero_weight_factor_is_a_valid_configuration():
    assert dict(ranking.validate_weights(ZERO_FRESHNESS)) == ZERO_FRESHNESS


def test_zero_weight_factor_with_a_score_does_not_move_the_score():
    low = compute_priority_score(FactorScores(0.8, 0.6, 0.4, 0.0), ZERO_FRESHNESS)
    high = compute_priority_score(FactorScores(0.8, 0.6, 0.4, 1.0), ZERO_FRESHNESS)
    assert low.missing == ()
    assert low.factors["freshness"] == 0.0
    assert low.effective_weights["freshness"] == 0.0
    assert low.score == pytest.approx(0.50 * 0.8 + 0.25 * 0.6 + 0.25 * 0.4)
    assert high.score == low.score


def test_zero_weight_factor_missing_leaves_other_weights_unchanged():
    present = compute_priority_score(FactorScores(0.8, 0.6, 0.4, 0.9), ZERO_FRESHNESS)
    missing = compute_priority_score(FactorScores(0.8, 0.6, 0.4, None), ZERO_FRESHNESS)
    assert missing.missing == ("freshness",)
    assert "freshness" not in missing.effective_weights
    assert dict(missing.effective_weights) == pytest.approx(
        {"profile_fit": 0.50, "preference_fit": 0.25, "deadline_urgency": 0.25}
    )
    assert missing.score == pytest.approx(present.score)


def test_only_zero_weight_factors_available_gives_no_score():
    result = compute_priority_score(FactorScores(freshness=0.9), ZERO_FRESHNESS)
    assert result.score is None
    assert result.factors["freshness"] == 0.9
    assert dict(result.effective_weights) == {}


def test_score_is_deterministic():
    first = compute_priority_score(FactorScores(0.3, 0.7, None, 0.9), DEV_WEIGHTS)
    second = compute_priority_score(FactorScores(0.3, 0.7, None, 0.9), DEV_WEIGHTS)
    assert first == second


# --- Ordering --------------------------------------------------------------


def test_equal_scores_are_ordered_by_job_id():
    jobs = [scored("job-c", profile_fit=0.5), scored("job-a", profile_fit=0.5),
            scored("job-b", profile_fit=0.5)]
    ordered = order_by_priority(jobs)
    assert [item.job_id for item in ordered.ranked] == ["job-a", "job-b", "job-c"]


def test_reordered_input_gives_the_same_order():
    jobs = [
        scored("job-d", profile_fit=0.4),
        scored("job-b", profile_fit=0.9, freshness=0.1),
        scored("job-a", profile_fit=0.6),
        scored("job-c", profile_fit=0.6),
        scored("job-e"),
    ]
    expected = order_by_priority(jobs)
    assert [item.job_id for item in expected.ranked] == ["job-b", "job-a", "job-c", "job-d"]
    assert [item.job_id for item in expected.unscored] == ["job-e"]
    for shift in range(1, len(jobs)):
        assert order_by_priority(jobs[shift:] + jobs[:shift]) == expected
    assert order_by_priority(reversed(jobs)) == expected


def test_unscored_jobs_are_kept_apart_and_never_given_a_score():
    ordered = order_by_priority([scored("job-z"), scored("job-a", freshness=0.0)])
    assert [item.job_id for item in ordered.ranked] == ["job-a"]
    assert [item.job_id for item in ordered.unscored] == ["job-z"]
    assert ordered.unscored[0].score is None


def test_duplicate_job_ids_are_rejected():
    with pytest.raises(ValueError):
        order_by_priority([scored("job-a", profile_fit=0.1), scored("job-a", profile_fit=0.2)])


def test_equal_scores_from_different_factor_sets_tie_on_job_id():
    complete = scored("job-b", profile_fit=0.1, preference_fit=0.1,
                      deadline_urgency=0.1, freshness=0.1)
    partial = scored("job-a", profile_fit=0.1, preference_fit=0.1, deadline_urgency=0.1)
    # Both are 0.1 mathematically; the raw floats differ and stay untouched.
    assert complete.score != partial.score
    assert complete.score == pytest.approx(partial.score)
    for jobs in ([complete, partial], [partial, complete]):
        assert [item.job_id for item in order_by_priority(jobs).ranked] == ["job-a", "job-b"]


# --- Deadline urgency ------------------------------------------------------


def test_missing_deadline_is_a_missing_factor():
    result = assess_deadline_urgency(None, NOW, horizon_days=HORIZON)
    assert result.status == "missing"
    assert result.urgency is None


def test_future_deadline_is_more_urgent_when_closer():
    near = assess_deadline_urgency(NOW + timedelta(days=3), NOW, horizon_days=HORIZON)
    far = assess_deadline_urgency(NOW + timedelta(days=24), NOW, horizon_days=HORIZON)
    beyond = assess_deadline_urgency(NOW + timedelta(days=90), NOW, horizon_days=HORIZON)
    assert near.status == far.status == beyond.status == "open"
    assert near.urgency == pytest.approx(0.9)
    assert far.urgency == pytest.approx(0.2)
    assert beyond.urgency == 0.0
    assert near.days_remaining == pytest.approx(3)


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(hours=-1), timedelta(days=-10)])
def test_past_deadline_is_expired_without_an_urgency_score(delta):
    result = assess_deadline_urgency(NOW + delta, NOW, horizon_days=HORIZON)
    assert result.status == "expired"
    assert result.urgency is None


def test_naive_timestamps_are_rejected():
    with pytest.raises(InvalidTimestamp):
        assess_deadline_urgency(NOW + timedelta(days=1), NOW.replace(tzinfo=None),
                                horizon_days=HORIZON)
    with pytest.raises(InvalidTimestamp):
        assess_deadline_urgency(datetime(2026, 10, 1), NOW, horizon_days=HORIZON)


def test_deadline_at_the_horizon_scores_zero_and_just_before_now_near_one():
    at_horizon = assess_deadline_urgency(NOW + timedelta(days=HORIZON), NOW,
                                         horizon_days=HORIZON)
    imminent = assess_deadline_urgency(NOW + timedelta(seconds=1), NOW,
                                       horizon_days=HORIZON)
    assert at_horizon.status == "open" and at_horizon.urgency == 0.0
    assert imminent.status == "open"
    assert imminent.urgency == pytest.approx(1.0, abs=1e-6)
    assert imminent.urgency < 1.0


def test_deadline_in_another_timezone_is_compared_as_the_same_instant():
    cest = timezone(timedelta(hours=2))
    deadline = datetime(2026, 9, 28, 14, 0, tzinfo=cest)  # 12:00 UTC, three days on
    result = assess_deadline_urgency(deadline, NOW, horizon_days=HORIZON)
    assert result.days_remaining == pytest.approx(3)
    assert result.urgency == pytest.approx(0.9)
    same_instant = assess_deadline_urgency(NOW.astimezone(cest), NOW, horizon_days=HORIZON)
    assert same_instant.status == "expired"


BAD_HORIZONS = [0, -5, float("nan"), True]


@pytest.mark.parametrize("horizon", BAD_HORIZONS)
def test_deadline_rejects_invalid_horizon(horizon):
    with pytest.raises(ValueError):
        assess_deadline_urgency(NOW + timedelta(days=1), NOW, horizon_days=horizon)


def test_deadline_rejects_a_huge_horizon_as_a_validation_error():
    with pytest.raises(ValueError) as error:
        assess_deadline_urgency(NOW + timedelta(days=1), NOW, horizon_days=10**400)
    assert isinstance(error.value.__cause__, OverflowError)


def test_availability_is_separate_from_eligibility():
    assert availability_exclusion(job(), NOW) is None
    assert availability_exclusion(job(active_state="closed"), NOW) == "closed"
    assert availability_exclusion(job(deadline_at=NOW - timedelta(days=1)), NOW) == "expired"
    assert availability_exclusion(job(deadline_at=None, active_state="unknown"), NOW) is None


# --- Freshness -------------------------------------------------------------


def freshness(**kw):
    args = {
        "source_published_at": None,
        "first_seen_at": None,
        "discovery_kind": "initial_snapshot",
        "now": NOW,
        "horizon_days": HORIZON,
    }
    return assess_freshness(**{**args, **kw})


def test_source_publication_time_gives_publication_freshness():
    result = freshness(source_published_at=NOW - timedelta(days=6))
    assert result.basis == "publication"
    assert result.freshness == pytest.approx(0.8)
    assert result.age_days == pytest.approx(6)


def test_discovery_freshness_is_labeled_apart_from_publication():
    seen = NOW - timedelta(days=6)
    discovery = freshness(first_seen_at=seen, discovery_kind="later_observation")
    simulated = freshness(first_seen_at=seen, discovery_kind="synthetic_scenario")
    publication = freshness(source_published_at=seen)
    assert discovery.basis == "discovery"
    assert simulated.basis == "simulated_discovery"
    assert publication.basis == "publication"
    assert discovery.freshness == publication.freshness


def test_publication_time_wins_over_discovery_time():
    result = freshness(
        source_published_at=NOW - timedelta(days=20),
        first_seen_at=NOW - timedelta(days=1),
        discovery_kind="later_observation",
    )
    assert result.basis == "publication"
    assert result.age_days == pytest.approx(20)


def test_initial_snapshot_first_seen_is_not_freshness():
    result = freshness(first_seen_at=NOW - timedelta(days=1), discovery_kind="initial_snapshot")
    assert result.basis == "missing"
    assert result.freshness is None


def test_missing_timestamps_give_a_missing_factor():
    result = freshness(discovery_kind="later_observation")
    assert result.basis == "missing"
    assert result.freshness is None


def test_updated_at_is_never_used_as_publication_time():
    record = job(
        source_published_at=None,
        source_updated_at=NOW - timedelta(days=1),
        discovery_kind="initial_snapshot",
    )
    result = assess_freshness(
        source_published_at=record.source_published_at,
        first_seen_at=record.first_seen_at,
        discovery_kind=record.discovery_kind,
        now=NOW,
        horizon_days=HORIZON,
    )
    assert result.basis == "missing"
    with pytest.raises(TypeError):
        assess_freshness(source_updated_at=NOW, first_seen_at=None, discovery_kind=None,
                         source_published_at=None, now=NOW, horizon_days=HORIZON)


@pytest.mark.parametrize(
    "kw",
    [
        {"source_published_at": NOW + timedelta(hours=1)},
        {"first_seen_at": NOW + timedelta(days=2), "discovery_kind": "later_observation"},
        # A future publication time is flagged, not replaced by discovery time.
        {"source_published_at": NOW + timedelta(days=1),
         "first_seen_at": NOW - timedelta(days=1), "discovery_kind": "later_observation"},
    ],
)
def test_future_freshness_timestamp_is_flagged_without_a_score(kw):
    result = freshness(**kw)
    assert result.basis == "invalid_future_timestamp"
    assert result.freshness is None


def test_freshness_is_one_at_age_zero_and_zero_at_the_horizon():
    assert freshness(source_published_at=NOW).freshness == 1.0
    at_horizon = freshness(source_published_at=NOW - timedelta(days=HORIZON))
    assert at_horizon.basis == "publication"
    assert at_horizon.freshness == 0.0


def test_freshness_rejects_naive_timestamps():
    with pytest.raises(InvalidTimestamp):
        freshness(source_published_at=datetime(2026, 9, 20))
    with pytest.raises(InvalidTimestamp):
        freshness(source_published_at=NOW - timedelta(days=1), now=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("horizon", BAD_HORIZONS)
def test_freshness_rejects_invalid_horizon(horizon):
    with pytest.raises(ValueError):
        freshness(source_published_at=NOW - timedelta(days=1), horizon_days=horizon)


def test_freshness_rejects_a_huge_horizon_as_a_validation_error():
    with pytest.raises(ValueError) as error:
        freshness(source_published_at=NOW - timedelta(days=1), horizon_days=10**400)
    assert isinstance(error.value.__cause__, OverflowError)


# --- Preference fit --------------------------------------------------------


def test_preferred_country_and_role_family_match():
    result = assess_preference_fit(preferences(), job())
    assert result.subfactors["location"] == 1.0
    assert result.subfactors["role_family"] == 1.0
    assert result.subfactors["industry"] is None
    assert result.unavailable["industry"] == "job_facts_have_no_industry_field"
    assert result.score == 1.0


def test_known_non_preferred_country_scores_zero_location_fit():
    record = job(locations=[JobLocation(country_code="FR", city="Paris", evidence_ids=[])])
    result = assess_preference_fit(preferences(), record)
    assert result.subfactors["location"] == 0.0
    assert result.score == pytest.approx(0.5)


def test_one_preferred_location_among_several_is_enough():
    record = job(locations=[
        JobLocation(country_code="FR", city="Paris", evidence_ids=[]),
        JobLocation(country_code=None, city="Somewhere", evidence_ids=[]),
        JobLocation(country_code="IT", city="Milan", evidence_ids=[]),
    ])
    assert assess_preference_fit(preferences(), record).subfactors["location"] == 1.0


def test_unknown_job_country_leaves_location_unavailable():
    record = job(locations=[
        JobLocation(country_code="FR", city="Paris", evidence_ids=[]),
        JobLocation(country_code=None, city="Somewhere", evidence_ids=[]),
    ])
    result = assess_preference_fit(preferences(), record)
    assert result.subfactors["location"] is None
    assert result.unavailable["location"] == "job_country_partly_unknown"


def test_null_job_facts_leave_role_and_industry_unavailable():
    result = assess_preference_fit(preferences(), job(facts=None))
    assert result.subfactors == {"location": 1.0, "role_family": None, "industry": None}
    assert result.unavailable == {
        "role_family": "job_facts_not_extracted",
        "industry": "job_facts_not_extracted",
    }
    assert result.score == 1.0


def with_role_family(value: str | None) -> JobRecord:
    record = job()
    role = None if value is None else SupportedText(value=value, evidence_ids=[])
    return record.model_copy(update={"facts": record.facts.model_copy(
        update={"role_family": role})})


def test_role_family_matches_after_trimming_and_case_folding():
    result = assess_preference_fit(preferences(), with_role_family("  Finance_Analyst "))
    assert result.subfactors["role_family"] == 1.0


def test_role_family_mismatch_scores_zero():
    result = assess_preference_fit(preferences(), with_role_family("marketing"))
    assert result.subfactors["role_family"] == 0.0
    assert "role_family" not in result.unavailable


@pytest.mark.parametrize("value", [None, "   "])
def test_missing_or_blank_job_role_family_is_unavailable(value):
    result = assess_preference_fit(preferences(), with_role_family(value))
    assert result.subfactors["role_family"] is None
    assert result.unavailable["role_family"] == "job_role_family_not_stated"


def test_blank_candidate_role_family_entries_are_ignored():
    blank_only = assess_preference_fit(
        preferences(preferred_role_families=["  "]), with_role_family("   "))
    assert blank_only.subfactors["role_family"] is None
    assert blank_only.unavailable["role_family"] == "candidate_has_no_role_family_preference"
    mixed = assess_preference_fit(
        preferences(preferred_role_families=["  ", "finance_analyst"]),
        with_role_family("finance_analyst"))
    assert mixed.subfactors["role_family"] == 1.0


def test_no_available_preference_subfactor_gives_no_score():
    prefs = preferences(preferred_country_codes=[], preferred_role_families=[],
                        preferred_industries=[], allowed_country_codes=None)
    result = assess_preference_fit(prefs, job())
    assert result.score is None
    assert set(result.unavailable) == set(ranking.PREFERENCE_SUBFACTORS)


# --- Profile fit boundary --------------------------------------------------


def test_profile_fit_boundary_validates_the_supplied_score():
    assert profile_fit_from(lambda c, j: 0.42, None, job()) == 0.42
    assert profile_fit_from(lambda c, j: None, None, job()) is None
    with pytest.raises(InvalidFactorValue):
        profile_fit_from(lambda c, j: 1.5, None, job())
