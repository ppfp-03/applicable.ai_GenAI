"""The one ranked Matches population (core/matches.py) and the screens that show it.

Curated roles and synthetic demo postings are checked by the canonical engine
and scored in one production-pipeline call with the D-051 formula; a posting
appears once; a role to verify sorts 15 points lower without its score
changing. Onboarding keeps its own scripted ranking.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import eligibility, normalized, ranking, store
from core import matches as mc
from oi.intelligence.ranking import assess_deadline_urgency

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app.py")
DEMO_PATH = ROOT / "data" / "demo.json"
DEMO = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
NOW = datetime(2026, 9, 24, 10, 55, tzinfo=timezone.utc)
EU = ["IT", "ES", "FR", "DE", "NL", "LU", "DK", "IE"]
OTHER = ["GB", "CH", "CN", "HK", "SG"]
#: A stated declaration (test input): authorized in the EU, sponsorship elsewhere.
ANSWERS = {"work_auth": {"authorized": EU, "not_authorized": OTHER, "sponsorship": OTHER, "no_sponsorship": EU}}
CONFIRMED = [{"field": "role_family", "values": ["Consulting"], "level": "important"},
             {"field": "role_family", "values": ["Product analytics"], "level": "important"}]
ORIGINALS = {"replai-pa", "bolton-strategy", "lazarde-ba", "morgan-product", "nestella-strategy",
             "jpmorrow-strategy", "unicreda-pa", "roshe-product", "mediobanco-growth", "roshe-basel",
             "deutsch-frankfurt", "deutsch-shanghai"}
USER_FACING_BANNED = re.compile(r"OI-50|normali[sz]ed|faithful|catalogue|Limited-data", re.IGNORECASE)


def build(roles=None, answers=ANSWERS, confirmed=CONFIRMED, cv=None) -> mc.Matches:
    return mc.build(DEMO["roles"] if roles is None else roles, DEMO["profile"], answers, confirmed, cv, NOW)


@pytest.fixture(scope="module")
def m() -> mc.Matches:
    return build()


# --- One population -----------------------------------------------------------------------


def test_the_population_is_62_unique_postings(m):
    assert len(m.population) == 62
    assert len({o.posting for o in m.population}) == 62
    assert {o.role_id for o in m.population if o.kind == "curated"} == ORIGINALS
    assert sum(o.kind == "synthetic" for o in m.population) == 50


def test_a_curated_copy_never_appears_beside_its_posting(m):
    copies = [r for r in DEMO["roles"] if r["id"].startswith("oi50-")]
    assert len(copies) == len(m.represented_by) == 42
    role_ids = {o.role_id for o in m.population}
    for role in copies:
        assert role["id"] not in role_ids
        assert m.represented_by[role["id"]] == f"synthetic-normalized:{role['source_job_id']}"
        assert m.get(role["id"]).role_id == m.represented_by[role["id"]]


def test_all_50_synthetic_postings_enter_before_eligibility(m):
    checked = set(m.ranked.eligibility)
    assert {f"synthetic-normalized:SYN-JOB-{i:03d}" for i in range(1, 51)} <= checked
    assert len(checked) == 62
    for o in m.excluded:
        assert o.status == "ineligible"  # excluded by a rule, never by origin


def test_one_pipeline_call_ranks_every_origin_together(monkeypatch):
    calls = []
    real = mc.rank_with_eligibility

    def spy(candidate, jobs, results, **kwargs):
        jobs = list(jobs)
        calls.append((jobs, kwargs))
        return real(candidate, jobs, results, **kwargs)

    monkeypatch.setattr(mc, "rank_with_eligibility", spy)
    build()
    (jobs, kwargs), = calls
    assert len(jobs) == 62
    assert dict(kwargs["weights"]) == {"profile_fit": 0.40, "preference_fit": 0.25,
                                       "deadline_urgency": 0.20, "freshness": 0.15}
    assert kwargs["deadline_horizon_days"] == 240 and kwargs["freshness_horizon_days"] == 30


# --- Comparable scoring -----------------------------------------------------------------------


def test_every_ranked_job_has_the_same_four_factors_and_weights(m):
    assert m.ordered
    for o in m.ordered:
        assert set(o.entry.breakdown.factors) == set(mc.FACTORS)
        assert o.entry.breakdown.missing == ()
        assert dict(o.entry.breakdown.effective_weights) == dict(normalized.WEIGHTS)


def test_the_raw_priority_is_the_weighted_sum(m):
    for o in m.ordered:
        expected = 100 * math.fsum(normalized.WEIGHTS[k] * o.entry.breakdown.factors[k] for k in mc.FACTORS)
        assert o.raw == pytest.approx(expected, abs=1e-9)


def test_the_curated_importance_weighted_preference_is_never_used(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("the curated preference formula must not rank Matches")

    monkeypatch.setattr(ranking, "preference_fit", forbidden)
    result = build()
    for o in result.ordered:
        assert o.entry.preference.subfactors["industry"] is None
        assert o.factor("preference_fit") in (0.0, 50.0, 100.0)


def test_no_formula_depends_on_origin():
    source = (ROOT / "core" / "matches.py").read_text(encoding="utf-8")
    assert source.count("rank_with_eligibility(") == 1
    assert "core.ranking" not in source and "from core import ranking" not in source


# --- Ordering -------------------------------------------------------------------------------------


def test_verification_moves_the_order_never_the_score(m):
    for o in m.ordered:
        raw = 100 * o.entry.breakdown.score
        assert o.raw == raw
        if o.status == "eligible":
            assert o.ordering == raw and o.adjustment == 0
        else:
            assert o.status == "uncertain" and o.ordering == raw - 15 and o.adjustment == -15
        assert o.shown == int(raw + 0.5)


def test_excluded_jobs_are_not_ordered(m):
    assert not {o.job_id for o in m.excluded} & {o.job_id for o in m.ordered}
    assert len(m.ordered) + len(m.excluded) == 62


def test_the_order_is_deterministic_with_ties_by_id(m):
    again = build()
    assert [o.job_id for o in again.ordered] == [o.job_id for o in m.ordered]
    keys = [(-o.ordering, -o.raw, o.job_id) for o in m.ordered]
    assert keys == sorted(keys)


def test_an_eligible_job_can_overtake_a_higher_scored_job_to_verify(m):
    pairs = [(v, e) for v in m.ordered if v.status == "uncertain" for e in m.ordered
             if e.status == "eligible" and e.raw < v.raw and m.ordered.index(e) < m.ordered.index(v)]
    assert pairs


def test_the_top_five_is_one_selection_from_the_whole_order(m):
    assert list(m.ordered[:5]) == sorted(m.ordered, key=lambda o: (-o.ordering, -o.raw, o.job_id))[:5]
    assert any(o.kind == "curated" for o in m.ordered[:5])  # curated roles reach it when they score


def test_synthetic_postings_reach_the_top_five_when_they_score():
    # Preferences a synthetic posting meets (Paris, marketing) and no curated role does.
    paris = build(confirmed=[{"field": "role_family", "values": ["Marketing"], "level": "important"}])
    profile = {**DEMO["profile"], "preferred_cities": ["Paris"]}
    result = mc.build(DEMO["roles"], profile, ANSWERS, [{"field": "role_family", "values": ["Marketing"],
                                                          "level": "important"}], None, NOW)
    assert any(o.kind == "synthetic" for o in result.ordered[:5])
    assert paris.ordered


# --- Curated ranking inputs --------------------------------------------------------------------------


def test_every_curated_original_gets_the_four_factors():
    everyone = {"work_auth": {"authorized": EU + OTHER, "no_sponsorship": EU + OTHER}}
    result = build(answers=everyone)
    curated = [o for o in result.population if o.kind == "curated"]
    assert len(curated) == 12
    for o in curated:
        assert o.profile.score is not None and not o.profile.missing
    for o in (o for o in result.ordered if o.kind == "curated"):
        assert o.entry.breakdown.missing == ()


def test_curated_top_ups_are_deterministic_and_leave_the_demo_file_alone():
    before = hashlib.sha256(DEMO_PATH.read_bytes()).hexdigest()
    roles = copy.deepcopy(DEMO["roles"])
    first = [mc.ranking_skills(r) for r in roles if r["id"] in ORIGINALS]
    build(roles=roles)
    assert [mc.ranking_skills(r) for r in roles if r["id"] in ORIGINALS] == first
    assert roles == DEMO["roles"]
    assert hashlib.sha256(DEMO_PATH.read_bytes()).hexdigest() == before
    for role in (r for r in roles if r["id"] in ORIGINALS):
        stated, added = mc.ranking_skills(role)
        assert 4 <= len(stated) + len(added) <= 6 or (len(stated) >= 4 and not added)
        assert not set(stated) & set(added)


def test_curated_education_and_experience_are_read_through_the_bridge():
    role = next(r for r in DEMO["roles"] if r["id"] == "replai-pa")
    job = mc.curated_profile(role, DEMO["profile"])
    req = role["requirements"]
    assert job.degree_level == req["degree_level"]
    assert set(job.fields_of_study) == {eligibility.FIELDS[f] for f in req["fields"]}
    assert job.experience_months == req["experience_min"]  # one internship = one month (the bridge)


def test_closes_feeds_urgency_and_found_feeds_simulated_freshness(m):
    for o in (o for o in m.ordered if o.kind == "curated"):
        role = next(r for r in DEMO["roles"] if r["id"] == o.role_id)
        deadline = datetime.fromisoformat(f"{role['closes']}T23:59:00+00:00")
        assert o.job.deadline_at == deadline
        assert o.entry.deadline == assess_deadline_urgency(deadline, NOW, horizon_days=240)
        assert o.entry.freshness.basis == "simulated_discovery"
        assert o.entry.freshness.reference_at == datetime.fromisoformat(f"{role['found']}T00:00:00+00:00")
        assert o.job.source_published_at is None


def test_posted_days_ago_is_never_read(m):
    roles = copy.deepcopy(DEMO["roles"])
    for r in roles:
        r["posted_days_ago"] = 999
    other = build(roles=roles)
    assert [(o.job_id, o.raw) for o in other.ordered] == [(o.job_id, o.raw) for o in m.ordered]


def test_a_cv_replaces_the_persona_skills_in_matches():
    from oi.contracts import CandidateProfile

    cv = CandidateProfile.model_validate(json.loads(
        (ROOT / "tests" / "fixtures" / "contracts" / "v0.2.0-draft" / "candidate_profile.json").read_text()))
    with_cv = build(cv=cv)
    bolton = with_cv.get("bolton-strategy")
    assert "SQL" not in bolton.profile.matched_skills or "SQL" in {s.value for s in cv.skills}


# --- Screens ------------------------------------------------------------------------------------------


def run_app(page=None, role_id=None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["stage"] = "app"
    at.session_state["home_guide_seen"] = True
    if page:
        at.switch_page(page)
    if role_id:
        at.query_params["id"] = role_id
    at.run()
    assert not at.exception
    return at


def markup(at) -> str:
    return "".join(x.value for x in at.markdown)


def visible(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


@pytest.fixture(scope="module")
def app():
    return run_app()


def matches_panel(html: str) -> str:
    start = html.index("Your top 5 opportunities")
    return html[start:]


def test_matches_shows_one_ranked_list_with_no_catalogue_section(app):
    html = markup(app)
    panel = matches_panel(html)
    assert "Your top 5 opportunities" in html
    assert not USER_FACING_BANNED.search(visible(panel))
    top = re.findall(r'<div class="k-row tile[^"]*">.*?<div class="k-jt">(.*?)</div>', panel)[:5]
    expected = [o.title for o in store.matches().ordered[:5]]
    from html import escape

    assert top == [escape(t) for t in expected]
    labels = [e.label for e in app.expander]
    assert any(label.startswith("More ranked roles (") for label in labels)
    assert not any("Excluded (" in label or "Not scored yet" in label for label in labels)


def test_synthetic_rows_carry_a_small_demo_label_and_a_normal_score(app):
    panel = matches_panel(markup(app))
    rows = re.findall(r'<div class="k-row tile.*?</b></div></div>', panel)
    assert len(rows) == len(store.matches().ordered)
    synthetic_titles = {o.title for o in store.matches().ordered if o.kind == "synthetic"}
    from html import escape

    for row in rows:
        title = re.search(r'<div class="k-jt">(.*?)</div>', row).group(1)
        if title in {escape(t) for t in synthetic_titles}:
            assert "Demo posting" in row or "Closes in" in row or "Applied" in row
        assert re.search(r"<b>\d+</b>", row)


def test_a_synthetic_role_page_shows_a_normal_priority_score():
    o = next(o for o in store.matches().ordered if o.kind == "synthetic")
    html = markup(run_app("views/role.py", o.role_id))
    assert f'<div class="sc">{o.shown}<small> /100 priority</small>' in html
    for name in ("Profile fit", "Preference fit", "Deadline urgency", "Freshness"):
        assert name in html
    assert '<span class="syn">SYNTHETIC</span>' in html
    assert not USER_FACING_BANNED.search(visible(html))


def test_a_legacy_synthetic_link_opens_the_same_posting():
    o = next(o for o in store.matches().ordered if o.kind == "synthetic")
    legacy = o.role_id.replace("synthetic-normalized:", "synthetic:")
    at = run_app("views/role.py", legacy)
    assert f'<div class="sc">{o.shown}<small> /100 priority</small>' in markup(at)
    labels = [b.label for b in at.button]
    assert "Open job posting" not in labels and "Start application" not in labels


def test_a_curated_role_page_shows_its_unified_score_without_typical_skills():
    o = next(o for o in store.matches().ordered if o.kind == "curated" and o.topped_up_skills)
    at = run_app("views/role.py", o.role_id)
    html = markup(at)
    assert f'<div class="sc">{o.shown}<small> /100 priority</small>' in html
    assert "Open job posting" in [b.label for b in at.button]
    text = visible(html)
    for skill in o.topped_up_skills:
        assert skill not in text, skill  # ranking inputs, never posting facts
    assert "typical for the role" in text


def test_the_same_curated_score_everywhere_outside_onboarding():
    app_role = next(a["role"] for a in store.applications() if store.priority(a["role"]) is not None)
    n = store.priority(app_role)
    apps = markup(run_app("views/applications.py"))
    assert f"Score {n}" in apps or f"{n}<span" in apps
    role = markup(run_app("views/role.py", app_role))
    assert f'<div class="sc">{n}<small> /100 priority</small>' in role
    home = markup(run_app())
    for v in store.top_matches():
        if store.priority(v.id) is not None:
            assert f'<div class="sc">{store.priority(v.id)}<small>' in home


#: A preference that brings synthetic postings into the top five.
FINANCE = [{"field": "role_family", "values": ["Finance"], "level": "important"}]


def matches_at(sel: int) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["stage"] = "app"
    at.session_state["home_guide_seen"] = True
    at.session_state[store.PREFERENCES] = FINANCE
    at.session_state["matches_sel"] = sel
    at.switch_page("views/matches.py")
    at.run()
    assert not at.exception
    return at


@pytest.mark.parametrize("sel", range(5))
def test_every_top_match_shows_the_explore_panel_and_both_actions(sel):
    at = matches_at(sel)
    html = markup(at)
    # The selected role's side panel: its header, then the criteria right under the score.
    panel = html[html.index(f'<div class="kk">#{sel + 1} · '):][:3000]
    assert '<div class="lab">8 fixed criteria' in panel
    assert re.search(r"\d of 8 met", panel)
    labels = [b.label for b in at.button]
    assert "Open role" in labels and "Start application" in labels


def test_starting_a_synthetic_posting_saves_its_curated_role():
    # Under FINANCE the top match is a synthetic posting whose curated copy is an oi50 role.
    at = matches_at(0)
    before = {a["role"] for a in at.session_state[store.APPS]}
    next(b for b in at.button if b.label == "Start application").click().run()
    added = {a["role"] for a in at.session_state[store.APPS]} - before
    assert len(added) == 1 and next(iter(added)).startswith("oi50-")


# --- Isolation -------------------------------------------------------------------------------------------


def test_onboarding_keeps_its_scripted_ranking():
    for v in store.views():
        expected = ranking.priority(ranking.raw_score(v.factors, store.data().weights), v.standing, store.data().penalty)
        assert v.score == expected
    assert not [v.id for v in store.ranked() if v.id.startswith("synthetic")]


def test_home_and_applications_get_no_synthetic_postings():
    assert not [v.id for v in store.top_matches() if v.id.startswith("synthetic")]
    assert not [a["role"] for a in store.applications() if a["role"].startswith("synthetic")]


def test_no_private_helper_crosses_into_the_matches_boundary():
    tree = ast.parse((ROOT / "core" / "matches.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not [a.name for a in node.names if a.name.startswith("_")]
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in (
                "eligibility", "normalized"):
            assert not node.attr.startswith("_"), node.attr


# --- No internal identifiers on role pages ------------------------------------------------------------

RAW = re.compile(r"\bHC_[A-Z_]+|\bv\d+\.\d+|\blevel_[a-z]{2}\b|current_status|expected_graduation_date|"
                 r"degree_level|degree_status|field_of_study|prior_experience_months|"
                 r"has_corporate_finance_experience")


def visible_text(html: str) -> str:
    html = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def role_text(role_id: str, answers: dict | None = None) -> str:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["stage"] = "app"
    at.session_state["home_guide_seen"] = True
    for key, value in (answers or {}).items():
        at.session_state[key] = value
    at.switch_page("views/role.py")
    at.query_params["id"] = role_id
    at.run()
    assert not at.exception
    return visible_text(markup(at))


@pytest.mark.parametrize("role_id", sorted(ORIGINALS) + ["oi50-006", "oi50-024"])
def test_curated_role_pages_show_no_rule_ids_versions_or_answer_keys(role_id):
    text = role_text(role_id)
    assert "How it was decided" in text or "Requirements" in text
    assert not RAW.search(text), RAW.search(text)


def test_a_curated_work_authorization_row_explains_in_words():
    # With no declaration, the right to work is open: its explanation is shown, readable.
    text = role_text("roshe-product")
    assert "Right to work in China" in text and "How it was decided" in text
    assert "HC_WORK_AUTH" not in text and "v0.1" not in text


@pytest.mark.parametrize("job", ["SYN-JOB-003", "SYN-JOB-018", "SYN-JOB-028", "SYN-JOB-041", "SYN-JOB-047"])
def test_synthetic_role_pages_show_no_rule_ids_versions_or_answer_keys(job):
    text = role_text(f"synthetic-normalized:{job}")
    assert "Checked by fixed rules" in text
    assert not RAW.search(text), RAW.search(text)


@pytest.mark.parametrize("answers", [{}, {"uk_work": "no"}, {"uk_work": "yes"}, ANSWERS])
def test_every_curated_reason_reads_without_identifiers(answers):
    # Met rows show their reason only when opened; every reason is checked here.
    from core import eligibility_view, synthetic

    for role in DEMO["roles"]:
        result = eligibility.assess(role, DEMO["profile"], answers)
        for c in eligibility_view.criteria(result, role, DEMO["profile"], answers):
            shown = synthetic.readable(c.detail, "HC_LANGUAGE" if c.id == "language" else "")
            assert not RAW.search(shown), (role["id"], c.id, shown)
            assert c.rule  # the audit trace is kept, just not shown


def test_the_role_page_never_renders_the_audit_trace():
    tree = ast.parse((ROOT / "views" / "role.py").read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "rule"]
