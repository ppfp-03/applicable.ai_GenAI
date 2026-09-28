"""The faithful synthetic catalogue adapter (core/synthetic) and legacy links.

core/synthetic still checks and ranks the faithful catalogue for audit and
supplies the readable rule wording the screens use. The screens themselves
show synthetic postings inside the one Matches ranking (tests/test_unified_matches.py);
an older `synthetic:` link opens the same posting's page.
"""

from __future__ import annotations

import json
import re
from html import escape
from datetime import datetime, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import eligibility, synthetic
from oi.intelligence.eligibility import assess_eligibility, load_job_parameters
from oi.intelligence.ranking_adapter import rank_with_eligibility

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app.py")
DEMO = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 9, 24, 10, 55, tzinfo=timezone.utc)
ANSWERS = {"uk_work": "yes"}
AUDIT_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com")


@pytest.fixture(scope="module")
def cat():
    return synthetic.run(DEMO["profile"], ANSWERS, NOW)


def every_id(cat) -> list[str]:
    p = cat.pipeline
    ids = [e.job_id for g in (p.eligible, p.uncertain) for e in (*g.top, *g.rest, *g.unscored)]
    return ids + [x.job_id for x in p.excluded]


# --- The adapter adds nothing ---------------------------------------------------


def test_statuses_are_the_canonical_engines(cat):
    candidate = eligibility.candidate(DEMO["profile"], ANSWERS)
    layer = load_job_parameters()
    for job in synthetic.jobs():
        direct = assess_eligibility(candidate, job, eligibility.catalogue(), job_parameters=layer)
        assert cat.result(job.job_id) == direct


def test_ranking_is_the_production_pipelines(cat):
    candidate = eligibility.candidate(DEMO["profile"], ANSWERS)
    layer = load_job_parameters()
    jobs = list(synthetic.jobs())
    results = [assess_eligibility(candidate, j, eligibility.catalogue(), job_parameters=layer) for j in jobs]
    direct = rank_with_eligibility(
        candidate, jobs, results, weights=synthetic.WEIGHTS, now=NOW,
        deadline_horizon_days=synthetic.DEADLINE_HORIZON_DAYS,
        freshness_horizon_days=synthetic.FRESHNESS_HORIZON_DAYS, limit=synthetic.TOP_N,
    )
    assert cat.pipeline == direct.pipeline


def test_all_fifty_are_reachable_exactly_once(cat):
    ids = every_id(cat)
    assert sorted(ids) == sorted(j.job_id for j in synthetic.jobs())
    assert len(ids) == len(set(ids)) == 50
    c = cat.counts()
    assert c["eligible"] + c["uncertain"] + c["excluded"] == 50
    assert c["scored"] + c["unscored"] + c["excluded"] == 50


def test_no_score_or_factor_is_invented(cat):
    p = cat.pipeline
    for group in (p.eligible, p.uncertain):
        assert len(group.top) <= synthetic.TOP_N
        for entry in (*group.top, *group.rest, *group.unscored):
            f = entry.breakdown.factors
            assert f["profile_fit"] is None and f["freshness"] is None and f["preference_fit"] is None
            job = entry.assessed.job
            assert (f["deadline_urgency"] is None) == (job.deadline_at is None)
            assert (entry.score is None) == (job.deadline_at is None)
        for entry in group.unscored:
            assert synthetic.shown(entry.score) is None


def test_the_demo_clock_is_read_as_utc():
    assert synthetic.aware(datetime(2026, 9, 24, 10, 55)).tzinfo == timezone.utc
    assert synthetic.aware(NOW) is NOW


# --- Matches ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["stage"] = "app"
    at.run()
    assert not at.exception
    return at


def page(at) -> str:
    return "".join(m.value for m in at.markdown)






def test_no_audit_url_reaches_the_screens(app):
    markup = page(app)
    for host in AUDIT_HOSTS:
        assert host not in markup


# --- Role page -------------------------------------------------------------------


def role_page(job_id: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["stage"] = "app"
    at.switch_page("views/role.py")
    at.query_params["id"] = job_id
    at.run()
    assert not at.exception
    return at






def test_curated_role_pages_are_unchanged():
    labels = [b.label for b in role_page("replai-pa").button]
    assert "Open job posting" in labels  # the curated demo page, as before


def test_an_unknown_synthetic_id_falls_back_to_the_demo_page():
    markup = page(role_page("synthetic:SYN-JOB-999"))
    assert "Synthetic catalogue" not in markup


# --- Isolation from the curated demo ----------------------------------------------


def _store_probe():
    import streamlit as st

    from core import store

    store.init()
    st.session_state["probe"] = {
        "views": [v.id for v in store.views()],
        "ranked": [v.id for v in store.ranked()],
        "apps": [a["role"] for a in store.applications()],
        "top": [v.id for v in store.top_matches()],
        "nav": store.nav_counts(),
    }


def test_the_curated_store_never_sees_synthetic_jobs():
    at = AppTest.from_function(_store_probe, default_timeout=60)
    at.run()
    probe = at.session_state["probe"]
    for key in ("views", "ranked", "apps", "top"):
        assert not [i for i in probe[key] if i.startswith("synthetic:")], key
    assert set(probe["views"]) <= {r["id"] for r in DEMO["roles"]}


# --- Limited-data scores -----------------------------------------------------------


def scored_entries(cat):
    p = cat.pipeline
    return [e for g in (p.eligible, p.uncertain) for e in (*g.top, *g.rest)]


def test_a_score_on_some_factors_only_is_labelled_limited_data(cat):
    scored = scored_entries(cat)
    assert scored, "the demo candidate has scored synthetic jobs"
    for entry in scored:
        used, missing = synthetic.basis(entry)
        assert used == ["deadline urgency"]  # the only factor this catalogue supports
        assert missing == 3 == len(entry.breakdown.missing)
        assert synthetic.limited(entry)
        assert synthetic.basis_text(entry) == "Based on deadline urgency only · 3 factors unavailable"


def test_a_zero_score_is_still_labelled_limited_data(cat):
    zeros = [e for e in scored_entries(cat) if synthetic.shown(e.score) == 0]
    assert zeros, "a far deadline gives a numeric 0"
    for entry in zeros:
        assert synthetic.limited(entry)


def test_the_basis_text_names_every_contributing_factor():
    from oi.intelligence.ranking import FactorScores, compute_priority_score

    class Fake:
        def __init__(self, **factors):
            self.breakdown = compute_priority_score(FactorScores(**factors), synthetic.WEIGHTS)
            self.score = self.breakdown.score

    two = Fake(deadline_urgency=0.5, preference_fit=1.0)
    assert synthetic.basis_text(two) == "Based on preference fit and deadline urgency · 2 factors unavailable"
    one_missing = Fake(profile_fit=0.2, preference_fit=0.4, deadline_urgency=0.6)
    assert synthetic.basis_text(one_missing).endswith("· 1 factor unavailable")
    full = Fake(profile_fit=0.2, preference_fit=0.4, deadline_urgency=0.6, freshness=0.1)
    assert not synthetic.limited(full)
    assert not synthetic.limited(Fake())  # no score at all: "Not scored yet", not limited








# --- No internal identifiers on screen ------------------------------------------------

RAW = re.compile(r"level_[a-z]{2}|current_status|expected_graduation_date|degree_level|degree_status|"
                 r"field_of_study|prior_experience_months|has_corporate_finance_experience|\bHC_[A-Z_]+|\bv\d+\.\d+")


def test_every_reason_shown_is_free_of_internal_identifiers(cat):
    raw_hits = 0
    for job in synthetic.jobs():
        for o in cat.result(job.job_id).outcomes:
            raw_hits += bool(RAW.search(o.reason))
            assert not RAW.search(synthetic.readable(o.reason, o.rule_id)), o.reason
    assert raw_hits  # the engine's own text does carry them: sanitizing is needed


def test_readable_maps_identifiers_to_names():
    assert synthetic.readable("Language: your answer is missing (level_fr).", "HC_LANGUAGE") == \
        "Language: your answer is missing (French level)."
    assert synthetic.readable("EN fluent (counted as C1) required; you have C1.", "HC_LANGUAGE") == \
        "English fluent (counted as C1) required; you have C1."
    assert synthetic.readable("Student status: your answer is missing (current_status).", "HC_STUDENT_STATUS") == \
        "Student status: your answer is missing (student status)."
    assert synthetic.readable("Rule HC_WORK_AUTH v0.1 · SG → unknown", "HC_WORK_AUTH") == \
        "Rule Work authorization · SG → unknown"
    assert synthetic.readable("The posting accepts business_administration.", "HC_FIELD_OF_STUDY") == \
        "The posting accepts business administration."


@pytest.mark.parametrize("job_id", ["synthetic:SYN-JOB-028", "synthetic:SYN-JOB-024", "synthetic:SYN-JOB-007"])
def test_rendered_role_pages_show_no_internal_identifiers(job_id):
    markup = page(role_page(job_id))
    visible = re.sub(r"<[^>]+>", " ", markup)  # text, not class names
    assert not RAW.search(visible), RAW.search(visible)
    assert "(French level)" in visible or job_id != "synthetic:SYN-JOB-028"


# --- Public candidate boundary --------------------------------------------------------


def test_core_synthetic_uses_only_the_public_candidate_boundary():
    import ast

    tree = ast.parse((ROOT / "core" / "synthetic.py").read_text(encoding="utf-8"))
    used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == "eligibility"}
    assert not {name for name in used if name.startswith("_")}
    assert {"candidate", "candidate_key"} <= used


def test_the_public_candidate_boundary_builds_the_same_candidate():
    for answers in (ANSWERS, {"uk_work": "no"}, {"uk_work": None, "languages": {"French": "B2"}}):
        assert eligibility.candidate_key(DEMO["profile"], answers) == eligibility._candidate_key(DEMO["profile"], answers)
        assert eligibility.candidate(DEMO["profile"], answers) == eligibility._candidate(
            eligibility._candidate_key(DEMO["profile"], answers))


def test_runs_are_cached_by_candidate_and_time():
    first = synthetic.run(DEMO["profile"], ANSWERS, NOW)
    assert synthetic.run(DEMO["profile"], dict(ANSWERS), NOW) is first
    other = synthetic.run(DEMO["profile"], {"uk_work": "no"}, NOW)
    assert other is not first
