"""Internal eligibility -> ranking adapter (Ranking Phase 3).

The adapter passes eligibility through untouched and delegates everything
else to ``run_ranking_pipeline``. Weights and horizons are development
values, not frozen configuration.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from oi.contracts import CandidateProfile, JobRecord, JobSnapshot
from oi.intelligence.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    EligibilityWarning,
    RuleOutcome,
    RuleStatus,
    UnknownCause,
    WarningCode,
    assess_eligibility,
    load_rule_catalogue,
)
from oi.intelligence.ranking import AssessedJob, run_ranking_pipeline
from oi.intelligence.ranking_adapter import (
    AdapterDiagnostic,
    EligibilityMappingError,
    rank_with_eligibility,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "contracts" / "v0.2.0-draft"
SNAPSHOT = ROOT / "data" / "snapshots" / "greenhouse_batch01.json"

DEV_WEIGHTS = {
    "profile_fit": 0.40,
    "preference_fit": 0.25,
    "deadline_urgency": 0.20,
    "freshness": 0.15,
}
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
HORIZONS = {"deadline_horizon_days": 30, "freshness_horizon_days": 30}

MISSING_PATH = "declarations.work_authorizations.NL.authorized_to_work"


def candidate(**preference_update) -> CandidateProfile:
    data = json.loads((FIXTURE_ROOT / "candidate_profile.json").read_text())
    profile = CandidateProfile.model_validate(data)
    if not preference_update:
        return profile
    preferences = profile.preferences.model_copy(update=preference_update)
    return profile.model_copy(update={"preferences": preferences})


def job(job_id: str, **update) -> JobRecord:
    data = json.loads((FIXTURE_ROOT / "job_record.json").read_text())
    return JobRecord.model_validate(data).model_copy(update={"job_id": job_id, **update})


def outcome(status: RuleStatus) -> RuleOutcome:
    unknown = status is RuleStatus.UNKNOWN
    return RuleOutcome(
        rule_id="HC_WORK_AUTH",
        status=status,
        candidate_evidence_ids=[],
        job_evidence_ids=["ev-job-requirement-001"],
        reason="Synthetic outcome for adapter tests.",
        unknown_cause=UnknownCause.CANDIDATE_MISSING if unknown else None,
        missing_field_paths=[MISSING_PATH] if unknown else [],
        rule_version="0.1",
    )


STATUS_OF_OUTCOME = {
    "eligible": RuleStatus.MET,
    "uncertain": RuleStatus.UNKNOWN,
    "ineligible": RuleStatus.CONFLICT,
}


def result(job_id: str, status: str = "eligible", *, candidate_id=None,
           warnings=()) -> EligibilityResult:
    rule = outcome(STATUS_OF_OUTCOME[status])
    return EligibilityResult(
        candidate_id=candidate_id or candidate().candidate_id,
        job_id=job_id,
        catalogue_version="0.1-internal",
        parameter_layer_version="0.1-temporary",
        status=EligibilityStatus(status),
        outcomes=[rule],
        missing_field_paths=list(rule.missing_field_paths),
        warnings=list(warnings),
    )


def adapt(jobs, results, who=None, **kw):
    args = {"weights": DEV_WEIGHTS, "now": NOW, **HORIZONS}
    return rank_with_eligibility(who or candidate(), jobs, results, **{**args, **kw})


def ids(entries):
    return [entry.job_id for entry in entries]


# --- Status passthrough ----------------------------------------------------


@pytest.mark.parametrize("status", ["eligible", "uncertain", "ineligible"])
def test_status_is_passed_through_unchanged(status):
    ranked = adapt([job("job-a")], [result("job-a", status)])
    grouped = {
        "eligible": ids(ranked.pipeline.eligible.top),
        "uncertain": ids(ranked.pipeline.uncertain.top),
        "ineligible": [item.job_id for item in ranked.pipeline.excluded
                       if item.reason == "ineligible"],
    }
    assert grouped == {name: (["job-a"] if name == status else []) for name in grouped}


def test_full_eligibility_result_is_preserved_by_job_id():
    warning = EligibilityWarning(code=WarningCode.UNSUPPORTED_CONSTRAINT,
                                 message="Constraint not catalogued.",
                                 constraint_id="work_authorization_nl",
                                 requirement_id="req-001")
    originals = [result("job-a", "uncertain", warnings=[warning]), result("job-b")]
    ranked = adapt([job("job-a"), job("job-b")], originals)
    assert list(ranked.eligibility) == ["job-a", "job-b"]
    kept = ranked.eligibility["job-a"]
    assert kept is originals[0]
    assert kept.outcomes == originals[0].outcomes
    assert kept.outcomes[0].status is RuleStatus.UNKNOWN
    assert kept.missing_field_paths == [MISSING_PATH]
    assert kept.warnings == [warning]
    assert (kept.catalogue_version, kept.parameter_layer_version) == (
        "0.1-internal", "0.1-temporary")


def test_real_engine_results_flow_through_unchanged():
    who, record = candidate(), job("synthetic:job-001")
    original = assess_eligibility(who, record, load_rule_catalogue())
    ranked = adapt([record], [original], who)
    assert ranked.eligibility["synthetic:job-001"] == original
    assert original.warnings  # the fixture's uncatalogued constraint
    assert ids(ranked.pipeline.eligible.top) == ["synthetic:job-001"]


def test_eligibility_note_is_not_filled_in():
    ranked = adapt([job("job-a")], [result("job-a", "uncertain")])
    assert ranked.pipeline.uncertain.top[0].assessed.eligibility_note is None


# --- Pairing validation ----------------------------------------------------


def test_result_for_another_candidate_is_rejected():
    with pytest.raises(EligibilityMappingError, match="another candidate"):
        adapt([job("job-a")], [result("job-a", candidate_id="someone-else")])


def test_result_with_a_mismatched_job_id_is_rejected():
    with pytest.raises(EligibilityMappingError, match="without result.*job-a.*unknown job.*job-z"):
        adapt([job("job-a")], [result("job-z")])


def test_duplicate_eligibility_result_is_rejected():
    with pytest.raises(EligibilityMappingError, match="duplicate eligibility result"):
        adapt([job("job-a")], [result("job-a"), result("job-a", "uncertain")])


def test_duplicate_job_is_rejected():
    with pytest.raises(EligibilityMappingError, match="duplicate job"):
        adapt([job("job-a"), job("job-a")], [result("job-a")])


def test_missing_eligibility_result_is_rejected():
    with pytest.raises(EligibilityMappingError, match="without result \\['job-b'\\]"):
        adapt([job("job-a"), job("job-b")], [result("job-a")])


def test_result_for_an_unknown_job_is_rejected():
    with pytest.raises(EligibilityMappingError, match="unknown job \\['job-x'\\]"):
        adapt([job("job-a")], [result("job-a"), result("job-x")])


# --- eligible_without_job_facts ---------------------------------------------


def test_eligible_job_without_facts_is_flagged():
    ranked = adapt([job("job-a", facts=None), job("job-b")],
                   [result("job-a"), result("job-b")])
    assert ranked.diagnostics == (AdapterDiagnostic("eligible_without_job_facts", "job-a"),)


def test_flag_changes_neither_group_nor_score():
    flagged = adapt([job("job-a", facts=None)], [result("job-a")])
    direct = run_ranking_pipeline(
        candidate(), [AssessedJob(job("job-a", facts=None), "eligible")],
        weights=DEV_WEIGHTS, now=NOW, **HORIZONS)
    assert flagged.diagnostics
    assert ids(flagged.pipeline.eligible.top) == ["job-a"]
    assert flagged.pipeline == direct
    assert flagged.eligibility["job-a"].status is EligibilityStatus.ELIGIBLE


@pytest.mark.parametrize("status", ["uncertain", "ineligible"])
def test_non_eligible_jobs_without_facts_keep_status_and_are_not_flagged(status):
    ranked = adapt([job("job-a", facts=None)], [result("job-a", status)])
    assert ranked.diagnostics == ()
    assert ranked.eligibility["job-a"].status.value == status
    if status == "uncertain":
        assert ids(ranked.pipeline.uncertain.top) == ["job-a"]
    else:
        assert [item.reason for item in ranked.pipeline.excluded] == ["ineligible"]


# --- Availability, profile fit, determinism --------------------------------


def test_availability_exclusion_still_applies_and_keeps_eligibility():
    ranked = adapt(
        [job("job-closed", active_state="closed"),
         job("job-expired", deadline_at=NOW - timedelta(days=1)),
         job("job-open")],
        [result("job-closed"), result("job-expired", "uncertain"), result("job-open")],
    )
    assert [(item.job_id, item.reason) for item in ranked.pipeline.excluded] == [
        ("job-closed", "closed"), ("job-expired", "expired")]
    assert ranked.eligibility["job-closed"].status is EligibilityStatus.ELIGIBLE
    assert ranked.eligibility["job-expired"].status is EligibilityStatus.UNCERTAIN
    assert set(ranked.eligibility) == {"job-closed", "job-expired", "job-open"}


def test_supplied_profile_fit_is_passed_through():
    ranked = adapt([job("job-a"), job("job-b")], [result("job-a"), result("job-b")],
                   profile_fit={"job-a": 0.83})
    by_id = {entry.job_id: entry for entry in ranked.pipeline.eligible.top}
    assert by_id["job-a"].breakdown.factors["profile_fit"] == 0.83
    assert by_id["job-b"].breakdown.factors["profile_fit"] is None


def test_profile_fit_for_an_unknown_job_is_rejected():
    with pytest.raises(EligibilityMappingError, match="profile_fit for unknown job"):
        adapt([job("job-a")], [result("job-a")], profile_fit={"job-z": 0.5})


def test_profile_fit_values_and_scorer_together_are_rejected():
    with pytest.raises(ValueError, match="not both"):
        adapt([job("job-a")], [result("job-a")], profile_fit={"job-a": 0.5},
              profile_fit_scorer=lambda c, j: 0.5)


def test_injected_scorer_is_forwarded():
    ranked = adapt([job("job-a")], [result("job-a")], profile_fit_scorer=lambda c, j: 0.61)
    assert ranked.pipeline.eligible.top[0].breakdown.factors["profile_fit"] == 0.61


def test_input_order_does_not_change_the_result():
    jobs = [job("job-c", facts=None), job("job-a"), job("job-b"), job("job-d")]
    results = [result("job-a"), result("job-b", "uncertain"), result("job-c"),
               result("job-d", "ineligible")]
    fits = {"job-a": 0.2, "job-b": 0.9, "job-c": 0.7}
    expected = adapt(jobs, results, profile_fit=fits)
    assert ids(expected.pipeline.eligible.top) == ["job-c", "job-a"]
    again = adapt(list(reversed(jobs)), results[::-1], profile_fit=fits)
    assert again.pipeline == expected.pipeline
    assert again.diagnostics == expected.diagnostics
    assert list(again.eligibility) == list(expected.eligibility)


def test_adapter_output_equals_calling_the_pipeline_directly():
    jobs = [job("job-a"), job("job-b", facts=None), job("job-c")]
    results = [result("job-a"), result("job-b", "uncertain"), result("job-c", "ineligible")]
    ranked = adapt(jobs, results, profile_fit={"job-a": 0.4}, limit=1)
    direct = run_ranking_pipeline(
        candidate(),
        [AssessedJob(jobs[0], "eligible", profile_fit=0.4),
         AssessedJob(jobs[1], "uncertain"),
         AssessedJob(jobs[2], "ineligible")],
        weights=DEV_WEIGHTS, now=NOW, limit=1, **HORIZONS)
    assert ranked.pipeline == direct


# --- Real snapshot, structural only -----------------------------------------


def test_real_snapshot_flows_through_without_fabricated_factors():
    """Structural check on today's snapshot; says nothing about ranking quality."""

    snapshot = JobSnapshot.model_validate_json(SNAPSHOT.read_text())
    who = candidate(allowed_country_codes=None)
    catalogue = load_rule_catalogue()
    results = [assess_eligibility(who, record, catalogue) for record in snapshot.jobs]

    ranked = adapt(snapshot.jobs, results, who)

    job_ids = sorted(record.job_id for record in snapshot.jobs)
    assert list(ranked.eligibility) == job_ids
    assert [r.job_id for r in ranked.eligibility.values()] == job_ids
    flagged = [d.job_id for d in ranked.diagnostics
               if d.code == "eligible_without_job_facts"]
    assert flagged == sorted(
        record.job_id for record, r in zip(snapshot.jobs, results)
        if r.status is EligibilityStatus.ELIGIBLE and record.facts is None)

    groups = ranked.pipeline.eligible, ranked.pipeline.uncertain
    entries = [e for group in groups for e in (*group.top, *group.rest, *group.unscored)]
    assert len(entries) + len(ranked.pipeline.excluded) == len(snapshot.jobs)
    for entry in entries:
        factors = entry.breakdown.factors
        assert factors["profile_fit"] is None
        if entry.assessed.job.facts is None:
            assert entry.preference.subfactors["role_family"] is None
            assert entry.preference.subfactors["industry"] is None
        if entry.assessed.job.deadline_at is None:
            assert factors["deadline_urgency"] is None
        assert entry.freshness.basis in ("publication", "missing", "invalid_future_timestamp")
