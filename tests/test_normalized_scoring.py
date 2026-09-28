"""Scoring the normalized synthetic demo jobs (core.normalized, oi.intelligence.profile_fit).

Approved for the normalized demo only: priority 40/25/20/15 through the
production pipeline, profile fit 50/25/25, a 240-day deadline horizon,
preferred cities and confirmed role families as the only preferences.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core import explore
from core import normalized as nz
from oi.intelligence import profile_fit as pf
from oi.intelligence.ranking import assess_deadline_urgency, assess_freshness, assess_preference_fit
from oi.io import synthetic_normalized as sn
from oi.io.normalized_catalogue import get_normalized_catalogue

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 24, 10, 55, tzinfo=timezone.utc)
PROFILE = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["profile"]
EU = ["IT", "ES", "FR", "DE", "NL", "LU", "DK", "IE"]
OTHER = ["GB", "CH", "CN", "HK", "SG"]
#: A stated declaration (test input): authorized in the EU, sponsorship elsewhere.
ANSWERS = {"work_auth": {"authorized": EU, "not_authorized": OTHER, "sponsorship": OTHER, "no_sponsorship": EU}}
CONFIRMED = [
    {"field": "role_family", "values": ["Consulting"], "level": "important"},
    {"field": "role_family", "values": ["Product analytics"], "level": "nice"},
    {"field": "industry", "values": ["Fintech"], "level": "must"},
    {"field": "mode", "values": ["Hybrid"], "level": "nice"},
]
#: The persona's skills as data/demo.json defines them (profile_sections "skills").
SKILLS = ["Python", "SQL", "Financial modelling", "React", "Figma"]
#: An extracted CV (contract fixture) whose skills differ from the persona's.
CV = json.loads((ROOT / "tests" / "fixtures" / "contracts" / "v0.2.0-draft" / "candidate_profile.json").read_text())
#: Every role-family label Fine-tune can offer (the Explore story directions)
#: or a demo role carries.
LEGACY_FAMILIES = {
    "Consulting": "Strategy & Consulting", "Strategy": "Strategy & Consulting",
    "Product management": "Product", "Product analytics": "Data & Analytics",
    "Growth": "Sales & Business Development", "Finance": "Finance & Investment",
    "Marketing": "Marketing & Communications", "Operations": "Operations & Supply Chain",
    "Sales": "Sales & Business Development", "Audit": "Risk & Compliance", "User research": "Product",
}


@pytest.fixture(scope="module")
def cat():
    return get_normalized_catalogue()


@pytest.fixture(scope="module")
def candidate():
    return nz.demo_candidate(PROFILE, ANSWERS, CONFIRMED)


@pytest.fixture(scope="module")
def run(candidate):
    # The normal demo persona, no CV uploaded: its data/demo.json skills.
    return nz.rank(candidate, NOW, nz.demo_persona_skills(None).texts)


def job(**kw) -> pf.JobProfile:
    base = dict(skills=("SQL", "Python", "Excel", "Valuation"), degree_level="master",
                fields_of_study=("finance", "economics"), any_field=False, experience_months=6)
    return pf.JobProfile(**{**base, **kw})


def facts(**kw) -> pf.CandidateFacts:
    base = dict(skills=frozenset({"SQL", "Python"}), degree_level="master", field_of_study="finance",
                experience_months=3)
    return pf.CandidateFacts(**{**base, **kw})


# --- Profile fit -----------------------------------------------------------------------


def test_profile_fit_is_exactly_50_25_25():
    assert pf.WEIGHTS == {"skills": 0.50, "education_field": 0.25, "experience": 0.25}
    fit = pf.profile_fit(facts(), job())
    assert (fit.skills, fit.education_field, fit.experience) == (50.0, 100.0, 50.0)
    assert fit.score == 0.50 * 50 + 0.25 * 100 + 0.25 * 50


def test_skills_score_is_exact_vocabulary_coverage():
    assert pf.skills_score(facts(skills=frozenset({"SQL"})), job()) == 25.0
    assert pf.skills_score(facts(skills=frozenset({"SQL", "Python", "Excel", "Valuation"})), job()) == 100.0
    assert pf.skills_score(facts(skills=frozenset({"Figma"})), job()) == 0.0


def test_candidate_skill_records_are_read_only_through_the_vocabulary():
    vocab = pf.load_skills_vocabulary()
    named = pf.vocabulary_skills(["Financial modelling in Excel", "Python (pandas)", "Bloomberg basics"], vocab)
    assert named == {"Financial modelling", "Excel", "Python"}
    assert named <= set(vocab)


@pytest.mark.parametrize("candidate_facts, expected", [
    (dict(degree_level="master", field_of_study="finance"), 100.0),
    (dict(degree_level="phd", field_of_study="economics"), 100.0),
    (dict(degree_level="bachelor", field_of_study="finance"), 50.0),
    (dict(degree_level="master", field_of_study="marketing"), 50.0),
    (dict(degree_level="bachelor", field_of_study="marketing"), 0.0),
])
def test_education_field_is_100_50_or_0(candidate_facts, expected):
    assert pf.education_score(facts(**candidate_facts), job()) == expected


def test_any_field_accepts_every_field():
    assert pf.education_score(facts(field_of_study="law"), job(any_field=True, fields_of_study=())) == 100.0


@pytest.mark.parametrize("months, required, expected", [(3, 6, 50.0), (6, 6, 100.0), (24, 6, 100.0), (0, 12, 0.0),
                                                        (None, 0, 100.0), (5, 0, 100.0)])
def test_experience_formula_and_no_requirement_is_100(months, required, expected):
    assert pf.experience_score(facts(experience_months=months), job(experience_months=required)) == expected


def test_missing_candidate_facts_leave_the_part_and_the_fit_unavailable():
    assert pf.profile_fit(facts(skills=None), job()).score is None
    assert pf.profile_fit(facts(degree_level=None), job()).missing == ("education_field",)
    assert pf.profile_fit(facts(field_of_study=None), job()).education_field is None
    assert pf.profile_fit(facts(experience_months=None), job(experience_months=3)).missing == ("experience",)


def test_candidate_facts_come_only_from_the_canonical_candidate(candidate):
    vocab = pf.load_skills_vocabulary()
    read = pf.candidate_facts(candidate, vocab)
    # The demo bridge records no skills: none are invented.
    assert candidate.skills == [] and read.skills is None
    assert (read.degree_level, read.field_of_study, read.experience_months) == (
        PROFILE["degree"]["level"], "finance", PROFILE["experience_months"])
    empty = nz.demo_candidate({"preferred_cities": []}, {}, None)
    assert pf.candidate_facts(empty, vocab) == pf.CandidateFacts(None, None, None, None)


def test_every_normalized_job_gets_a_profile_fit_for_the_complete_candidate(run, cat):
    assert set(run.profile_fits) == {j.job_id for j in cat.snapshot.jobs}
    for fit in run.profile_fits.values():
        assert fit.score is not None and 0 <= fit.score <= 100 and not fit.missing


def test_the_explore_overlap_uses_the_same_skill_rule():
    story = {"sk": ["SQL", "Excel", "Data analysis"]}
    assert explore.cv_overlap(story, ["Financial modelling in Excel", "sql"]) == ["SQL", "Excel"]


# --- Preferences --------------------------------------------------------------------------


def test_preferred_cities_become_country_preferences():
    mapped = nz.map_preferences(["London", "Singapore", "Shanghai", "Atlantis"], None)
    assert mapped.preferences.preferred_country_codes == ["GB", "SG", "CN"]
    assert mapped.unmapped_cities == ("Atlantis",)


@pytest.mark.parametrize("label, family", [
    ("Consulting", "Strategy & Consulting"), ("Strategy", "Strategy & Consulting"),
    ("Product management", "Product"), ("Product analytics", "Data & Analytics"),
    ("Growth", "Sales & Business Development"), ("Markets & Trading", "Markets & Trading"),
    ("Finance", "Finance & Investment"), ("Marketing", "Marketing & Communications"),
    ("Operations", "Operations & Supply Chain"), ("Sales", "Sales & Business Development"),
    ("Audit", "Risk & Compliance"), ("User research", "Product"),
    ("Astrology", None), ("finance", None),
])
def test_the_approved_role_family_mapping(label, family):
    assert nz.role_family(label) == family


def test_no_industry_and_no_unconfirmed_preference_is_used():
    rows = [*CONFIRMED, {"field": "role_family", "values": ["Growth"], "level": "none"},
            {"field": "role_family", "values": ["Astrology"], "level": "important"}]
    mapped = nz.map_preferences([], rows)
    assert mapped.preferences.preferred_role_families == ["Strategy & Consulting", "Data & Analytics"]
    assert mapped.preferences.preferred_industries == []
    assert mapped.preferences.preferred_country_codes == []
    assert mapped.unmapped_role_families == ("Astrology",)
    assert nz.map_preferences([], None).preferences.preferred_role_families == []


def test_every_normalized_job_gets_a_preference_fit_for_the_complete_candidate(candidate, cat):
    assert candidate.preferences.preferred_country_codes == ["GB", "SG", "CN"]
    assert candidate.preferences.preferred_role_families == ["Strategy & Consulting", "Data & Analytics"]
    for j in cat.snapshot.jobs:
        fit = assess_preference_fit(candidate.preferences, j)
        assert fit.score is not None, j.job_id
        assert fit.subfactors["industry"] is None


def test_every_legacy_role_family_label_maps_deterministically():
    assert dict(nz.ROLE_FAMILY_MAP) == LEGACY_FAMILIES
    families = set(json.loads(sn.RULES_PATH.read_text(encoding="utf-8"))["role_families"])
    assert set(LEGACY_FAMILIES.values()) <= families
    for family in families:
        assert nz.role_family(family) == family


def test_no_fine_tune_or_demo_role_family_is_lost():
    stories = json.loads((ROOT / "data" / "stories.json").read_text(encoding="utf-8"))["stories"]
    roles = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["roles"]
    labels = {s["direction"] for s in stories} | {r["role_family"] for r in roles}
    rows = [{"field": "role_family", "values": [label], "level": "important"} for label in sorted(labels)]
    mapped = nz.map_preferences([], rows)
    assert mapped.unmapped_role_families == ()
    assert set(mapped.preferences.preferred_role_families) == {LEGACY_FAMILIES[label] for label in labels}


# --- Demo persona skills ----------------------------------------------------------------------------


def test_without_a_cv_the_persona_uses_its_demo_json_skills():
    records = nz.demo_persona_skills(None)
    assert records == nz.SkillRecords(tuple(SKILLS), "demo_persona")


def test_extracted_cv_skills_replace_the_persona_skills():
    from oi.contracts import CandidateProfile

    cv = CandidateProfile.model_validate(CV)
    records = nz.demo_persona_skills(cv)
    assert records.source == "cv"
    assert records.texts == tuple(s.value for s in cv.skills)
    assert not set(records.texts) & set(SKILLS)


def test_a_cv_without_skills_leaves_the_persona_skills():
    from oi.contracts import CandidateProfile

    cv = CandidateProfile.model_validate({**CV, "skills": []})
    assert nz.demo_persona_skills(cv).source == "demo_persona"


def test_demo_skills_do_not_leak_into_a_cv_backed_candidate(candidate):
    from oi.contracts import CandidateProfile

    records = nz.demo_persona_skills(CandidateProfile.model_validate(CV))
    r = nz.rank(candidate, NOW, records.texts)
    assert r.facts.skills == {"Financial modelling", "Excel", "Python", "Data analysis"}
    assert not r.facts.skills & {"SQL", "Figma"}
    demo = nz.rank(candidate, NOW, nz.demo_persona_skills(None).texts)
    assert demo.facts.skills == {"Python", "SQL", "Financial modelling", "Figma"}


def test_the_fallback_is_not_a_default_of_the_scorer(candidate):
    # rank() never reaches for the persona's skills by itself.
    assert nz.rank(candidate, NOW).facts.skills is None


# --- Deadline and freshness ---------------------------------------------------------------------


def test_every_normalized_job_gets_deadline_urgency_on_240_days(cat):
    assert nz.DEADLINE_HORIZON_DAYS == 240
    for j in cat.snapshot.jobs:
        assert assess_deadline_urgency(j.deadline_at, NOW, horizon_days=240).urgency is not None


def test_every_normalized_job_gets_simulated_freshness(cat):
    for j in cat.snapshot.jobs:
        assert j.source_published_at is None
        result = assess_freshness(source_published_at=None, first_seen_at=j.first_seen_at,
                                  discovery_kind=j.discovery_kind, now=NOW, horizon_days=nz.FRESHNESS_HORIZON_DAYS)
        assert result.freshness is not None


# --- Ranking ---------------------------------------------------------------------------------------


def test_the_adapter_uses_the_production_pipeline_with_the_approved_weights(monkeypatch, candidate):
    calls = []
    real = nz.rank_with_eligibility

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(nz, "rank_with_eligibility", spy)
    nz.rank(candidate, NOW, nz.demo_persona_skills(None).texts)
    (kwargs,) = calls
    assert dict(kwargs["weights"]) == {"profile_fit": 0.40, "preference_fit": 0.25,
                                       "deadline_urgency": 0.20, "freshness": 0.15}
    assert kwargs["deadline_horizon_days"] == 240
    assert "profile_fit_scorer" not in kwargs and len(kwargs["profile_fit"]) == 50


def test_every_rankable_job_has_all_four_factors_and_no_renormalization(run):
    entries = run.entries()
    assert entries
    for e in entries:
        assert e.breakdown.missing == ()
        assert dict(e.breakdown.effective_weights) == dict(nz.WEIGHTS)


def test_the_raw_priority_is_the_weighted_sum_with_no_verification_penalty(run):
    for e in run.entries():
        f = e.breakdown.factors
        expected = math.fsum(nz.WEIGHTS[k] * f[k] for k in nz.WEIGHTS)
        assert e.breakdown.score == pytest.approx(expected, abs=1e-12)
        assert e.breakdown.factors["profile_fit"] == pytest.approx(run.profile_fits[e.job_id].score / 100)


def test_eligibility_status_decides_the_groups(run):
    p = run.ranked.pipeline
    for status, group in (("eligible", p.eligible), ("uncertain", p.uncertain)):
        for e in (*group.top, *group.rest, *group.unscored):
            assert run.result(e.job_id).status.value == status
    for x in p.excluded:
        assert run.result(x.job_id).status.value == "ineligible" and x.reason == "ineligible"
    assert len(run.entries()) + len(p.excluded) == 50


def test_ranking_is_deterministic(candidate):
    first, second = nz.rank(candidate, NOW, nz.demo_persona_skills(None).texts), nz.rank(candidate, NOW, nz.demo_persona_skills(None).texts)
    order = lambda r: [(e.job_id, e.breakdown.score) for e in r.entries()]  # noqa: E731
    assert order(first) == order(second)


def test_no_score_is_authored_in_the_data():
    for path in (sn.SNAPSHOT_PATH, sn.PARAMETERS_PATH, sn.PROVENANCE_PATH, sn.RULES_PATH):
        text = path.read_text(encoding="utf-8").lower()
        assert "priority" not in text and "profile_fit" not in text and '"score"' not in text, path


def test_scores_follow_the_candidate_not_the_job_data(candidate):
    other = nz.with_preferences(candidate, nz.map_preferences(["Paris"], None).preferences)
    before = {e.job_id: e.breakdown.score for e in nz.rank(candidate, NOW, nz.demo_persona_skills(None).texts).entries()}
    after = {e.job_id: e.breakdown.score for e in nz.rank(other, NOW, nz.demo_persona_skills(None).texts).entries()}
    assert before != after


# --- Incomplete candidate --------------------------------------------------------------------------


def test_missing_candidate_data_stays_missing_and_is_never_zero():
    bare = nz.demo_candidate(PROFILE, ANSWERS, None)
    bare = nz.with_preferences(bare, nz.map_preferences([], None).preferences)
    r = nz.rank(bare, NOW)  # no skill records, no preferences
    entries = r.entries()
    assert entries
    for e in entries:
        assert e.breakdown.factors["profile_fit"] is None
        assert e.breakdown.factors["preference_fit"] is None
        assert set(e.breakdown.missing) == {"profile_fit", "preference_fit"}
        assert e.breakdown.factors["deadline_urgency"] is not None and e.breakdown.factors["freshness"] is not None
    assert all(f.missing == ("skills",) for f in r.profile_fits.values())


# --- Isolation ---------------------------------------------------------------------------------------


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_faithful_files_and_normalized_artifacts_are_unchanged():
    assert sha(sn.FAITHFUL_SNAPSHOT) == "c1932122e5fb1ab25b6a5e094290ec54db0c8981338747970325ee78ff734919"
    assert sha(sn.FAITHFUL_PARAMETERS) == "d0dd1af492ff3e3277c1a1d083188a8d5ddc824d5131f37d6dcead781bcc3998"
    assert sn.main(["--check"]) == 0


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {
        f"{n.module}.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module for a in n.names}


def test_screens_reach_the_scoring_only_through_the_matches_boundary():
    # Screens read the one Matches ranking (core.matches, via the store), never
    # the normalized scoring directly; onboarding reads neither.
    files = [ROOT / "app.py", *(ROOT / "views").glob("*.py"), *(ROOT / "ui").glob("*.py")]
    for path in files:
        assert "core.normalized" not in imports(path), path
    onboarding = imports(ROOT / "views" / "onboarding.py")
    assert not {m for m in onboarding if m.startswith(("core.matches", "core.normalized"))}


def test_no_private_helper_crosses_a_module_boundary():
    for path in (ROOT / "core" / "normalized.py", ROOT / "src" / "oi" / "intelligence" / "profile_fit.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not [a.name for a in node.names if a.name.startswith("_")], path
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.attr.startswith("_"):
                assert node.value.id == "self", (path, node.attr)
