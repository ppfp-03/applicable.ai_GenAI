"""Curated eligibility parameters for the OI-50 synthetic catalogue.

Only requirements whose text maps to an existing rule parameter without a
choice between readings carry an entry in config/eligibility/job_parameters.json.
Everything else keeps no parameters, so its rule stays UNKNOWN.
"""

from __future__ import annotations

import collections
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from oi.contracts import CandidateProfile
from oi.intelligence.eligibility import assess_eligibility, load_job_parameters, load_rule_catalogue
from oi.intelligence.eligibility.catalogue import LANGUAGE_SCALES, language_level_key
from oi.intelligence.ranking_adapter import rank_with_eligibility
from oi.io.synthetic_catalogue import get_synthetic_catalogue

from . import builders as b

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "contracts" / "v0.2.0-draft" / "candidate_profile.json"

#: Requirements left unresolved on purpose, by reason (profile ID, requirement suffix).
AMBIGUOUS = {
    ("024", "req-002"), ("025", "req-002"), ("027", "req-003"), ("042", "req-002"),
    ("043", "req-002"), ("048", "req-003"), ("049", "req-002"),            # student status
    ("003", "req-003"), ("042", "req-003"),                                # "summer" windows
    ("038", "req-005"), ("047", "req-005"),                                # experience alternatives
    ("021", "req-005"), ("031", "req-002"), ("031", "req-003"), ("034", "req-004"),
    ("036", "req-004"), ("044", "req-006"), ("045", "req-005"), ("046", "req-003"),  # language wording
}
UNSUPPORTED = {
    ("027", "req-002"),                                                    # residence condition
    ("003", "req-002"), ("011", "req-002"), ("026", "req-002"), ("029", "req-002"), ("030", "req-002"), ("035", "req-002"),
    ("036", "req-002"), ("037", "req-002"), ("038", "req-002"), ("040", "req-002"), ("041", "req-002"),
    ("011", "req-003"), ("019", "req-002"), ("023", "req-003"),            # final stage, Bac+4/5
    ("005", "req-004"), ("011", "req-004"), ("023", "req-004"), ("026", "req-003"), ("027", "req-005"),
    ("033", "req-003"), ("035", "req-003"), ("036", "req-003"), ("039", "req-003"), ("045", "req-003"),
    ("048", "req-006"),                                                    # fields outside the vocabulary
    ("014", "req-003"), ("021", "req-004"), ("034", "req-003"), ("044", "req-005"),  # "related/similar/equivalent": no approved map
    ("014", "req-005"), ("033", "req-005"), ("046", "req-005"),            # experience ranges / internships
    ("018", "req-004"),                                                    # two languages in one requirement
}


def rid(profile: str, suffix: str) -> tuple[str, str]:
    return f"synthetic:SYN-JOB-{profile}", f"synthetic:SYN-JOB-{profile}:{suffix}"


@pytest.fixture(scope="module")
def jobs():
    return get_synthetic_catalogue().jobs


@pytest.fixture(scope="module")
def layer():
    return load_job_parameters()


@pytest.fixture(scope="module")
def hard(jobs):
    """Every hard requirement of the catalogue, by (job_id, requirement_id)."""
    return {(j.job_id, r.requirement_id): r for j in jobs for r in j.facts.requirements if r.constraint_id}


def assess_all(jobs, candidate, layer):
    catalogue = load_rule_catalogue()
    return [assess_eligibility(candidate, job, catalogue, job_parameters=layer) for job in jobs]


# --- The file ----------------------------------------------------------------


def test_the_parameter_file_loads_with_the_oi50_entries(layer):
    assert layer.layer_version == "0.1-temporary"
    assert len(layer.entries) == 84
    assert all(e.job_id.startswith("synthetic:SYN-JOB-") and e.origin == "curated" for e in layer.entries)


def test_every_entry_matches_a_real_hard_requirement(layer, hard, jobs):
    evidence = {j.job_id: {ref.evidence_id for ref in j.evidence} for j in jobs}
    for entry in layer.entries:
        requirement = hard[(entry.job_id, entry.requirement_id)]
        assert entry.requirement_id.startswith(entry.job_id + ":")
        assert entry.constraint_id == requirement.constraint_id
        assert entry.evidence_ids == requirement.evidence_ids
        assert set(entry.evidence_ids) <= evidence[entry.job_id]


def test_entries_are_unique_and_deterministically_ordered(layer):
    keys = [(e.job_id, e.requirement_id) for e in layer.entries]
    assert len(set(keys)) == len(keys)
    assert keys == sorted(keys)


def test_counts_by_rule(layer):
    assert collections.Counter(e.constraint_id for e in layer.entries) == {
        "HC_LANGUAGE": 47, "HC_STUDENT_STATUS": 16, "HC_DEGREE_LEVEL": 11,
        "HC_GRAD_WINDOW": 6, "HC_FIELD_OF_STUDY": 1, "HC_WORK_AUTH": 3,
    }


def test_the_engine_accepts_every_entry_without_warnings(jobs, layer):
    who = CandidateProfile.model_validate(json.loads(FIXTURE.read_text()))
    codes = {w.code.value for r in assess_all(jobs, who, layer) for w in r.warnings}
    assert not codes & {"invalid_job_parameter", "orphan_job_parameter"}


# --- What stays unresolved ----------------------------------------------------


def test_every_hard_requirement_is_classified_once(layer, hard):
    parameterized = {(e.job_id, e.requirement_id) for e in layer.entries}
    truncated = {key for key, r in hard.items() if "..." in r.text}
    ambiguous = {rid(*k) for k in AMBIGUOUS}
    unsupported = {rid(*k) for k in UNSUPPORTED}
    groups = [parameterized, truncated, ambiguous, unsupported]
    assert sum(len(g) for g in groups) == len(hard) == 154
    assert set().union(*groups) == set(hard)
    assert [len(g) for g in groups] == [84, 17, 19, 34]


def test_truncated_requirements_get_no_parameters(layer, hard):
    for key, requirement in hard.items():
        if "..." in requirement.text:
            assert layer.get(*key) is None, key


def test_ambiguous_and_unsupported_requirements_get_no_parameters(layer):
    for key in AMBIGUOUS | UNSUPPORTED:
        assert layer.get(*rid(*key)) is None, key


def test_preferred_and_not_stated_text_never_carries_hard_parameters(jobs, layer):
    for job in jobs:
        for req in job.facts.requirements:
            lowered = req.text.lower()
            if "prefer" in lowered or "not stated" in lowered:
                assert req.constraint_id is None
                assert layer.get(job.job_id, req.requirement_id) is None
    # SYN-JOB-048 work authorization and SYN-JOB-050 experience / field of study.
    assert not [e for e in layer.entries if e.job_id == "synthetic:SYN-JOB-048" and e.constraint_id == "HC_WORK_AUTH"]
    assert not [e for e in layer.entries if e.job_id == "synthetic:SYN-JOB-050"
                and e.constraint_id in ("HC_MIN_EXPERIENCE", "HC_FIELD_OF_STUDY")]


# --- Per rule -------------------------------------------------------------------


def test_languages_use_approved_scales_and_levels(layer, hard):
    catalogue = load_rule_catalogue().get("HC_LANGUAGE")
    for entry in (e for e in layer.entries if e.constraint_id == "HC_LANGUAGE"):
        p = entry.parameters
        assert p.min_level in LANGUAGE_SCALES[p.scale]
        assert p.required.code in catalogue.answer_key(language_level_key(p.language)).allowed_values
        text = hard[(entry.job_id, entry.requirement_id)].text
        if p.scale == "SELF":
            assert p.min_level == "fluent" and "fluen" in text.lower()
    assert layer.get(*rid("007", "req-004")).parameters.required.code == "CEFR:C1"


def test_unclear_language_wording_stays_unresolved(layer):
    for key in [("021", "req-005"), ("031", "req-002"), ("031", "req-003"), ("034", "req-004"),
                ("036", "req-004"), ("044", "req-006"), ("045", "req-005"), ("046", "req-003"),
                ("018", "req-004"), ("012", "req-004"), ("017", "req-004"), ("020", "req-004")]:
        assert layer.get(*rid(*key)) is None, key


def test_work_authorization_only_where_stated(layer):
    entries = {e.job_id[-3:]: e.parameters for e in layer.entries if e.constraint_id == "HC_WORK_AUTH"}
    assert {k: (p.country_code, p.employer_sponsorship) for k, p in entries.items()} == {
        "018": ("CN", "not_stated"), "046": ("DE", "not_offered"), "047": ("GB", "not_stated")}


def test_graduation_windows_only_when_exact(layer):
    windows = {e.job_id[-3:]: (e.parameters.start, e.parameters.end) for e in layer.entries
               if e.constraint_id == "HC_GRAD_WINDOW"}
    assert windows == {
        "012": (date(2027, 12, 1), date(2028, 7, 31)), "017": (date(2027, 12, 1), date(2028, 7, 31)),
        "020": (date(2026, 12, 1), date(2027, 7, 31)), "041": (date(2027, 1, 1), date(2027, 12, 31)),
        "044": (date(2027, 1, 1), date(2028, 12, 31)), "048": (date(2027, 8, 1), date(2028, 12, 31)),
    }


def test_degree_levels_only_when_representable(layer):
    degrees = {e.job_id[-3:]: (e.parameters.min_level, e.parameters.in_progress_policy)
               for e in layer.entries if e.constraint_id == "HC_DEGREE_LEVEL"}
    assert degrees["001"] == ("master", "counts")
    assert degrees["014"] == ("bachelor", "does_not_count")
    assert degrees["047"] == ("bachelor", None)
    for french in ("019", "023"):
        assert french not in degrees


def test_fields_use_exact_vocabulary_names_only(layer):
    fields = {e.job_id[-3:]: e.parameters for e in layer.entries if e.constraint_id == "HC_FIELD_OF_STUDY"}
    assert {k: (p.accepted, p.related_accepted) for k, p in fields.items()} == {"001": (["economics"], False)}


def test_no_experience_minimum_is_invented(layer):
    assert not [e for e in layer.entries if e.constraint_id == "HC_MIN_EXPERIENCE"]


def test_or_alternatives_are_never_made_stricter(layer):
    # "Enrolled OR recently graduated" keeps both statuses.
    assert layer.get(*rid("007", "req-002")).parameters.accepted == ["enrolled_student", "recent_graduate"]
    # "2027 OR 2028" is one contiguous window covering both years.
    window = layer.get(*rid("044", "req-003")).parameters
    assert (window.start, window.end) == (date(2027, 1, 1), date(2028, 12, 31))
    # A field list is neither narrowed nor broadened: a "related/similar/
    # equivalent" alternative has no approved equivalence map, and a field
    # outside the vocabulary cannot be dropped, so both stay unresolved.
    for key in [("014", "req-003"), ("021", "req-004"), ("034", "req-003"), ("044", "req-005"), ("048", "req-006")]:
        assert layer.get(*rid(*key)) is None, key


# --- Through the engine and ranking ----------------------------------------------


STUDENT = dict(
    answers={
        ("HC_STUDENT_STATUS", "current_status"): "enrolled_student",
        ("HC_GRAD_WINDOW", "expected_graduation_date"): date(2027, 6, 30),
        ("HC_DEGREE_LEVEL", "degree_level"): "master", ("HC_DEGREE_LEVEL", "degree_status"): "in_progress",
        ("HC_FIELD_OF_STUDY", "field_of_study"): "finance",
        ("HC_LANGUAGE", "level_en"): "CEFR:C1", ("HC_LANGUAGE", "level_fr"): "SELF:fluent",
    },
    work_auth=[("FR", True, False), ("GB", False, True), ("DE", True, False)],
)


@pytest.mark.parametrize("who", [
    b.candidate(),
    b.candidate(**STUDENT),
    b.candidate(answers={("HC_STUDENT_STATUS", "current_status"): "neither", ("HC_LANGUAGE", "level_en"): "CEFR:B2"}),
])
def test_conflicts_come_only_from_curated_parameters(jobs, layer, who):
    for result in assess_all(jobs, who, layer):
        for outcome in result.outcomes:
            if outcome.status.value == "conflict" and outcome.requirement_id:
                assert layer.get(result.job_id, outcome.requirement_id) is not None


def test_unparameterized_requirements_are_never_a_conflict(jobs, layer):
    # They stay UNKNOWN, except HC_WORK_AUTH, whose rule needs no job-side
    # value: a candidate authorized in the job's country is MET without one.
    parameterized = {(e.job_id, e.requirement_id) for e in layer.entries}
    for result in assess_all(jobs, b.candidate(**STUDENT), layer):
        for outcome in result.outcomes:
            if outcome.requirement_id and (result.job_id, outcome.requirement_id) not in parameterized:
                assert outcome.status.value != "conflict", outcome
                if outcome.rule_id != "HC_WORK_AUTH":
                    assert outcome.status.value in ("unknown", "not_applicable"), outcome


def test_the_student_candidate_is_decided_by_the_curated_values(jobs, layer):
    results = {r.job_id[-3:]: r for r in assess_all(jobs, b.candidate(**STUDENT), layer)}
    conflicts = {(k, o.rule_id) for k, r in results.items() for o in r.outcomes if o.status.value == "conflict"}
    assert conflicts == {("001", "HC_FIELD_OF_STUDY"), ("012", "HC_GRAD_WINDOW"), ("017", "HC_GRAD_WINDOW"),
                         ("048", "HC_GRAD_WINDOW"), ("014", "HC_DEGREE_LEVEL")}


def test_ranking_accepts_the_parameterized_results(jobs, layer):
    who = b.candidate(**STUDENT)
    results = assess_all(jobs, who, layer)
    ranked = rank_with_eligibility(
        who, jobs, results,
        weights={"profile_fit": 0.40, "preference_fit": 0.25, "deadline_urgency": 0.20, "freshness": 0.15},
        now=datetime(2026, 9, 27, 12, tzinfo=timezone.utc), deadline_horizon_days=30, freshness_horizon_days=30,
    )
    groups = ranked.pipeline.eligible, ranked.pipeline.uncertain
    entries = [e for g in groups for e in (*g.top, *g.rest, *g.unscored)]
    assert len(entries) + len(ranked.pipeline.excluded) == 50
    assert all(len(g.top) <= 5 for g in groups)
    assert {k: r.status for k, r in ranked.eligibility.items()} == {r.job_id: r.status for r in results}
