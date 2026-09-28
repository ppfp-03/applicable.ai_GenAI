"""Internal ranking pipeline in ``oi.intelligence.ranking`` (Phase 2).

The pipeline takes eligibility as already decided by the caller and wires the
Phase 1 primitives together. It is not the shared ``rank_opportunities``
contract; the weights and horizons are development values, not frozen config.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence import ranking
from oi.intelligence.ranking import (
    AssessedJob,
    FactorScores,
    InvalidFactorValue,
    compute_priority_score,
    run_ranking_pipeline,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "v0.2.0-draft"

DEV_WEIGHTS = {
    "profile_fit": 0.40,
    "preference_fit": 0.25,
    "deadline_urgency": 0.20,
    "freshness": 0.15,
}

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
DEADLINE_HORIZON = 30
FRESHNESS_HORIZON = 30


def candidate() -> CandidateProfile:
    data = json.loads((FIXTURE_ROOT / "candidate_profile.json").read_text())
    return CandidateProfile.model_validate(data)


def job(job_id: str, **update) -> JobRecord:
    data = json.loads((FIXTURE_ROOT / "job_record.json").read_text())
    return JobRecord.model_validate(data).model_copy(update={"job_id": job_id, **update})


def assessed(job_id: str, eligibility: str = "eligible", profile_fit=0.5, **update):
    return AssessedJob(job(job_id, **update), eligibility, profile_fit=profile_fit)


def run(jobs, **kw):
    args = {
        "weights": DEV_WEIGHTS,
        "now": NOW,
        "deadline_horizon_days": DEADLINE_HORIZON,
        "freshness_horizon_days": FRESHNESS_HORIZON,
    }
    return run_ranking_pipeline(candidate(), jobs, **{**args, **kw})


def ids(entries):
    return [entry.job_id for entry in entries]


# --- Grouping and exclusion ------------------------------------------------


def test_eligible_and_uncertain_jobs_form_separate_groups():
    result = run([assessed("job-a"), assessed("job-b", "uncertain"), assessed("job-c")])
    assert ids(result.eligible.top) == ["job-a", "job-c"]
    assert ids(result.uncertain.top) == ["job-b"]
    assert result.excluded == ()


def test_ineligible_job_is_excluded_and_never_scored():
    result = run([assessed("job-a"), assessed("job-x", "ineligible", profile_fit=1.0)])
    assert ids(result.eligible.top) == ["job-a"]
    assert ids(result.uncertain.top) == []
    [exclusion] = result.excluded
    assert (exclusion.job_id, exclusion.reason, exclusion.availability) == (
        "job-x", "ineligible", None)


def test_closed_posting_is_excluded_for_availability_not_eligibility():
    result = run([assessed("job-closed", active_state="closed")])
    [exclusion] = result.excluded
    assert exclusion.reason == "closed"
    assert exclusion.availability == "closed"
    assert exclusion.assessed.eligibility == "eligible"


def test_expired_posting_is_excluded_for_availability():
    result = run([assessed("job-old", "uncertain", deadline_at=NOW - timedelta(hours=1))])
    [exclusion] = result.excluded
    assert exclusion.reason == "expired"
    assert exclusion.assessed.eligibility == "uncertain"
    assert result.uncertain.top == ()


def test_unavailable_posting_with_top_scores_is_still_excluded():
    result = run([
        assessed("job-closed", profile_fit=1.0, active_state="closed"),
        assessed("job-expired", profile_fit=1.0, deadline_at=NOW),
        assessed("job-low", profile_fit=0.0),
    ])
    assert ids(result.eligible.top) == ["job-low"]
    assert [(item.job_id, item.reason) for item in result.excluded] == [
        ("job-closed", "closed"), ("job-expired", "expired")]


def test_availability_is_reported_before_ineligibility():
    result = run([assessed("job-x", "ineligible", active_state="closed")])
    [exclusion] = result.excluded
    assert exclusion.reason == "closed"
    assert exclusion.assessed.eligibility == "ineligible"


# --- Same scoring for both groups --------------------------------------------


def test_eligible_and_uncertain_use_identical_scoring_without_penalty():
    result = run([assessed("job-e", "eligible", 0.7), assessed("job-u", "uncertain", 0.7)])
    [eligible], [uncertain] = result.eligible.top, result.uncertain.top
    assert eligible.breakdown.factors == uncertain.breakdown.factors
    assert eligible.breakdown.effective_weights == uncertain.breakdown.effective_weights
    assert eligible.score == uncertain.score


def test_pipeline_score_equals_the_phase_one_primitives():
    [entry] = run([assessed("job-a", profile_fit=0.6)]).eligible.top
    expected = compute_priority_score(
        FactorScores(
            profile_fit=0.6,
            preference_fit=entry.preference.score,
            deadline_urgency=entry.deadline.urgency,
            freshness=entry.freshness.freshness,
        ),
        DEV_WEIGHTS,
    )
    assert entry.breakdown == expected
    assert entry.deadline.status == "open"
    assert entry.freshness.basis == "publication"


# --- Limit, ordering and determinism ---------------------------------------


def test_limit_caps_each_group_and_keeps_the_rest():
    jobs = [assessed(f"job-{i}", profile_fit=i / 10) for i in range(7)]
    jobs += [assessed(f"unc-{i}", "uncertain", profile_fit=i / 10) for i in range(4)]
    result = run(jobs, limit=3)
    assert ids(result.eligible.top) == ["job-6", "job-5", "job-4"]
    assert ids(result.eligible.rest) == ["job-3", "job-2", "job-1", "job-0"]
    assert ids(result.uncertain.top) == ["unc-3", "unc-2", "unc-1"]
    assert ids(result.uncertain.rest) == ["unc-0"]


def test_default_limit_is_the_local_pipeline_default():
    result = run([assessed(f"job-{i}") for i in range(8)])
    assert result.limit == ranking.PIPELINE_DEFAULT_LIMIT == 5
    assert len(result.eligible.top) == 5
    assert len(result.eligible.rest) == 3


def test_fewer_jobs_than_the_limit_stay_fewer_and_are_not_padded():
    result = run([
        assessed("job-a"),
        assessed("job-b", "uncertain"),
        assessed("job-x", "ineligible"),
        assessed("job-y", active_state="closed"),
    ])
    assert ids(result.eligible.top) == ["job-a"]
    assert ids(result.uncertain.top) == ["job-b"]
    assert result.eligible.rest == result.uncertain.rest == ()
    assert ids(result.excluded) == ["job-x", "job-y"]


def test_equal_scores_in_a_group_order_by_job_id():
    result = run([assessed("job-c"), assessed("job-a"), assessed("job-b")])
    assert ids(result.eligible.top) == ["job-a", "job-b", "job-c"]


def test_input_order_does_not_change_the_result():
    jobs = [
        assessed("job-d", profile_fit=0.2),
        assessed("job-b", profile_fit=0.9),
        assessed("job-a", "uncertain", profile_fit=0.4),
        assessed("job-c", profile_fit=0.9),
        assessed("job-x", "ineligible"),
        assessed("job-y", active_state="closed"),
        assessed("job-e", "uncertain", profile_fit=0.8),
    ]
    expected = run(jobs)
    assert ids(expected.eligible.top) == ["job-b", "job-c", "job-d"]
    assert ids(expected.uncertain.top) == ["job-e", "job-a"]
    for shift in range(1, len(jobs)):
        assert run(jobs[shift:] + jobs[:shift]) == expected
    assert run(list(reversed(jobs))) == expected


def test_duplicate_job_ids_are_rejected_across_groups():
    with pytest.raises(ValueError, match="duplicate job_id"):
        run([assessed("job-a"), assessed("job-a", "uncertain")])


@pytest.mark.parametrize("limit", [0, -1, True, 2.5])
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError):
        run([assessed("job-a")], limit=limit)


# --- Missing factors -------------------------------------------------------


def bare_job(job_id: str, eligibility: str = "eligible", **update) -> AssessedJob:
    """A job that supports no factor: no facts, location, dates or fit."""

    fields = {
        "facts": None,
        "locations": [],
        "deadline_at": None,
        "source_published_at": None,
        "discovery_kind": "initial_snapshot",
        **update,
    }
    return assessed(job_id, eligibility, profile_fit=None, **fields)


def test_missing_factors_renormalize_through_phase_one():
    [entry] = run([assessed("job-a", profile_fit=0.8, deadline_at=None)]).eligible.top
    assert entry.deadline.status == "missing"
    assert entry.breakdown.missing == ("deadline_urgency",)
    assert dict(entry.breakdown.effective_weights) == pytest.approx(
        {"profile_fit": 0.50, "preference_fit": 0.3125, "freshness": 0.1875})


def test_job_with_no_factors_is_unscored_but_kept_visible():
    result = run([bare_job("job-z"), assessed("job-a"), bare_job("job-u")])
    assert ids(result.eligible.top) == ["job-a"]
    assert ids(result.eligible.unscored) == ["job-u", "job-z"]
    for entry in result.eligible.unscored:
        assert entry.score is None
        assert entry.breakdown.missing == ranking.FACTOR_NAMES


def test_uncertain_unscored_job_stays_in_its_own_group():
    result = run([bare_job("job-u", "uncertain")])
    assert ids(result.uncertain.unscored) == ["job-u"]
    assert result.eligible == ranking.PipelineGroup((), (), ())


def test_missing_job_facts_do_not_invent_role_family_or_industry_fit():
    [entry] = run([assessed("job-a", facts=None)]).eligible.top
    assert entry.preference.subfactors == {
        "location": 1.0, "role_family": None, "industry": None}
    assert entry.preference.unavailable == {
        "role_family": "job_facts_not_extracted",
        "industry": "job_facts_not_extracted",
    }
    assert entry.breakdown.factors["preference_fit"] == 1.0


# --- Profile fit -----------------------------------------------------------


def test_supplied_profile_fit_is_used_as_is():
    [entry] = run([assessed("job-a", profile_fit=0.37)]).eligible.top
    assert entry.breakdown.factors["profile_fit"] == 0.37


def test_missing_profile_fit_stays_missing_without_a_scorer():
    [entry] = run([assessed("job-a", profile_fit=None)]).eligible.top
    assert entry.breakdown.factors["profile_fit"] is None
    assert "profile_fit" in entry.breakdown.missing


def test_injected_scorer_is_called_only_for_ranked_candidates():
    calls = []

    def scorer(candidate, record):
        calls.append(record.job_id)
        return 0.9

    result = run(
        [
            assessed("job-a", profile_fit=None),
            assessed("job-u", "uncertain", profile_fit=None),
            assessed("job-x", "ineligible", profile_fit=None),
            assessed("job-y", profile_fit=None, active_state="closed"),
        ],
        profile_fit_scorer=scorer,
    )
    assert sorted(calls) == ["job-a", "job-u"]
    assert result.eligible.top[0].breakdown.factors["profile_fit"] == 0.9


def test_supplied_fit_and_scorer_together_are_rejected():
    with pytest.raises(ValueError, match="one or the other"):
        run([assessed("job-a", profile_fit=0.5)], profile_fit_scorer=lambda c, j: 0.5)


def test_invalid_supplied_profile_fit_is_rejected():
    with pytest.raises(InvalidFactorValue):
        assessed("job-a", profile_fit=1.2)


def test_unknown_eligibility_value_is_rejected():
    with pytest.raises(ValueError):
        assessed("job-a", "maybe")
