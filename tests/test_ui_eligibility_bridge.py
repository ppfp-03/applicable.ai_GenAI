"""The UI -> canonical Eligibility Engine bridge.

UI/demo state -> structural adapter (core/eligibility.py) -> CandidateProfile
+ JobRecord (+ JobParameterSet) -> assess_eligibility -> presentation adapter
(core/eligibility_view.py) -> RoleView.

Pins the approved demo mapping: classification vs modality, only supported
hard constraints gate, informational requirements (Mandarin HSK) never
conflict, a degree in progress counts only if it completes before the role's
synthetic start, experience in months, Business -> business_administration,
citizenship is never work authorisation, and sponsorship is explicit.
"""

from __future__ import annotations

import ast
import copy
from datetime import date
from pathlib import Path

import pytest

from core import eligibility, eligibility_view, store
from oi.contracts import RequirementClassification, RequirementModality
from oi.intelligence.eligibility import RuleStatus, assess_eligibility

D = store.data()
ROOT = Path(__file__).resolve().parents[1]
ANSWERS = [{"uk_work": uk} for uk in ("yes", "no", "unsure", None)]


def role(role_id: str) -> dict:
    return D.role(role_id).raw


def outcome(result, rule_id: str):
    return next(o for o in result.outcomes if o.rule_id == rule_id)


def reqs(role_id: str) -> dict:
    return {r.requirement_id: r for r in eligibility.job(role(role_id)).facts.requirements}


# ───────────────────────── Demo configuration ─────────────────────────


def test_every_role_has_the_synthetic_start_and_explicit_sponsorship():
    assert len(D.roles) == 12
    for r in D.roles:
        assert r.raw["start"] == "2027-09"
        assert r.raw["sponsorship"] in eligibility.SPONSORSHIP


def test_giulia_keeps_the_msc_in_progress_and_a_separate_completed_bachelor():
    p = D.profile
    assert p["name"] == "Giulia Rossi"
    assert (p["degree"]["level"], p["degree"]["status"], p["degree"]["graduation"]) == (
        "master", "in_progress", "2027-07")
    [bsc] = p["previous_degrees"]
    assert (bsc["level"], bsc["status"], bsc["field"]) == ("bachelor", "completed", "Economics")


# ───────────────────────── Structural adapter: job ─────────────────────────


def test_supported_requirements_are_mandatory_hard_constraints():
    r = reqs("nestella-strategy")
    expected = {
        "req-work-auth": eligibility.WORK_AUTH,
        "req-student": eligibility.STUDENT,
        "req-grad-window": eligibility.GRAD_WINDOW,
        "req-degree": eligibility.DEGREE,
        "req-field": eligibility.FIELD,
        "req-language-en": eligibility.LANGUAGE,
        "req-experience": eligibility.EXPERIENCE,
    }
    for rid, cid in expected.items():
        assert r[rid].classification is RequirementClassification.HARD_CONSTRAINT
        assert r[rid].modality is RequirementModality.MANDATORY
        assert r[rid].constraint_id == cid


@pytest.mark.parametrize("role_id", ["nestella-strategy", "roshe-product", "deutsch-shanghai"])
def test_mandarin_hsk_is_informational_with_no_constraint(role_id):
    hsk = reqs(role_id)["req-language-mandarin"]
    # Stated as required (modality), but no supported rule checks it (classification).
    assert hsk.modality is RequirementModality.MANDATORY
    assert hsk.classification is RequirementClassification.INFORMATIONAL
    assert hsk.constraint_id is None
    params = eligibility.parameters(role(role_id), D.profile)
    assert all(e.requirement_id != "req-language-mandarin" for e in params.entries)


def test_business_maps_to_business_administration():
    [entry] = [e for e in eligibility.parameters(role("bolton-strategy"), D.profile).entries
               if e.constraint_id == eligibility.FIELD]
    assert entry.parameters.accepted == ["finance", "economics", "business_administration"]


def test_graduation_window_covers_whole_months():
    [entry] = [e for e in eligibility.parameters(role("replai-pa"), D.profile).entries
               if e.constraint_id == eligibility.GRAD_WINDOW]
    assert (entry.parameters.start, entry.parameters.end) == (date(2026, 12, 1), date(2027, 12, 31))


def test_internships_become_min_months():
    [entry] = [e for e in eligibility.parameters(role("replai-pa"), D.profile).entries
               if e.constraint_id == eligibility.EXPERIENCE]
    assert entry.parameters.min_months == role("replai-pa")["requirements"]["experience_min"] == 1


@pytest.mark.parametrize("value, expected", [
    ("offered", "offered"), ("not_offered", "not_offered"), ("not_stated", "not_stated"), (None, "not_stated"),
])
def test_sponsorship_is_explicit(value, expected):
    r = {**role("replai-pa"), "sponsorship": value}
    [entry] = [e for e in eligibility.parameters(r, D.profile).entries
               if e.constraint_id == eligibility.WORK_AUTH]
    assert entry.parameters.employer_sponsorship == expected


@pytest.mark.parametrize("value", [False, True, "no", "yes"])
def test_a_non_explicit_sponsorship_value_is_rejected(value):
    with pytest.raises(ValueError):
        eligibility.parameters({**role("replai-pa"), "sponsorship": value}, D.profile)


# ───────────────────────── Structural adapter: candidate ─────────────────────────


def test_candidate_carries_the_structured_facts():
    c = eligibility.candidate(D.profile, {"uk_work": "yes"})
    got = {(cid, a.answer_key): a.value for cid, answers in c.eligibility_answers.items() for a in answers}
    assert got == {
        (eligibility.DEGREE, "degree_level"): "master",
        (eligibility.DEGREE, "degree_status"): "in_progress",
        (eligibility.GRAD_WINDOW, "expected_graduation_date"): date(2027, 7, 1),
        (eligibility.FIELD, "field_of_study"): "finance",
        (eligibility.STUDENT, "current_status"): "enrolled_student",
        (eligibility.EXPERIENCE, "prior_experience_months"): 10,
        (eligibility.LANGUAGE, "level_en"): "C1",
        (eligibility.LANGUAGE, "level_it"): "native",
    }
    assert [e.value for e in c.education] == ["MSc Finance", "BSc Economics"]


def test_bachelor_is_recorded_not_inferred_from_the_master():
    profile = copy.deepcopy(D.profile)
    profile["previous_degrees"] = []
    c = eligibility.candidate(profile, {})
    assert [e.value for e in c.education] == ["MSc Finance"]


def test_citizenship_is_never_a_work_authorisation():
    c = eligibility.candidate(D.profile, {})
    assert D.profile["citizenship"] == "IT"
    assert c.declarations.work_authorizations == []
    assert c.declarations.additional_citizenships == []
    result = eligibility.assess(role("mediobanco-growth"), D.profile, {})
    assert outcome(result, eligibility.WORK_AUTH).status is RuleStatus.UNKNOWN


def test_hsk_never_reaches_the_candidate_answers():
    c = eligibility.candidate(D.profile, {"languages": {"Mandarin": "HSK 6"}})
    keys = {a.answer_key for a in c.eligibility_answers.get(eligibility.LANGUAGE, [])}
    assert keys == {"level_en", "level_it"}


# ───────────────────────── Degree in progress vs role start ─────────────────────────


@pytest.mark.parametrize("graduation, start, policy", [
    ("2027-07", "2027-09", "counts"),
    ("2027-07", "2027-07", "does_not_count"),
    ("2027-07", "2027-06", "does_not_count"),
    ("2027-07", None, "undecided"),
    (None, "2027-09", "undecided"),
])
def test_in_progress_policy(graduation, start, policy):
    assert eligibility.in_progress_policy(graduation, start) == policy


def test_in_progress_msc_counts_before_the_synthetic_start():
    for r in D.roles:
        result = eligibility.assess(r.raw, D.profile, {"uk_work": "yes"})
        assert outcome(result, eligibility.DEGREE).status is RuleStatus.MET, r.id


def test_a_start_before_completion_is_a_degree_conflict():
    r = {**role("replai-pa"), "start": "2027-06"}
    result = eligibility.assess(r, D.profile, {"uk_work": "yes"})
    assert outcome(result, eligibility.DEGREE).status is RuleStatus.CONFLICT
    assert eligibility_view.standing(result) == "excluded"


def test_no_start_leaves_the_degree_undecided():
    r = {k: v for k, v in role("replai-pa").items() if k != "start"}
    result = eligibility.assess(r, D.profile, {"uk_work": "yes"})
    got = outcome(result, eligibility.DEGREE)
    assert got.status is RuleStatus.UNKNOWN and got.unknown_cause.value == "policy_undecided"


# ───────────────────────── Canonical distinctions ─────────────────────────


def test_a_preferred_requirement_cannot_conflict():
    r = role("morgan-product")
    job = eligibility.job(r)
    req = [x.model_copy(update={"modality": RequirementModality.PREFERRED})
           if x.constraint_id == eligibility.EXPERIENCE else x for x in job.facts.requirements]
    job = job.model_copy(update={"facts": job.facts.model_copy(update={"requirements": req})})
    profile = {**D.profile, "experience_months": 0}
    result = assess_eligibility(eligibility.candidate(profile, {"uk_work": "yes"}), job,
                                eligibility.catalogue(),
                                job_parameters=eligibility.parameters(r, profile))
    assert outcome(result, eligibility.EXPERIENCE).status is RuleStatus.NOT_APPLICABLE


def test_the_mapping_is_complete_for_every_role():
    # No unsupported constraint, unusable parameter or orphan entry anywhere.
    for r in D.roles:
        for ans in ANSWERS:
            assert eligibility.assess(r.raw, D.profile, ans).warnings == [], r.id


# ───────────────────────── Presentation adapter ─────────────────────────


@pytest.mark.parametrize("ans", ANSWERS)
def test_tiles_and_standing_render_the_engine_unchanged(ans):
    for r in D.roles:
        result = eligibility.assess(r.raw, D.profile, ans)
        v = store.view(r, ans)
        assert v.standing == eligibility_view.STANDING[result.status]
        for c in v.criteria:
            outs = [o for o in result.outcomes if eligibility_view.CRITERION_OF[o.rule_id] == c.id]
            worst = min(outs, key=lambda o: eligibility_view._SEVERITY[o.status])
            assert c.status == eligibility_view.TILE_STATUS[worst.status]
            assert c.detail == worst.reason
        statuses = {c.status for c in v.criteria}
        assert v.standing == ("excluded" if "not_met" in statuses
                              else "verify" if "check" in statuses else "eligible")


def test_limitations_never_affect_the_standing():
    for r in D.roles:
        v = store.view(r, {"uk_work": "yes"})
        has_hsk = any("HSK" in lvl for lvl in r.raw["requirements"].get("languages", {}).values())
        assert bool(v.limitations) == has_hsk, r.id
        assert all(c.status != "not_met" for c in v.criteria if c.id == "language")


# ───────────────────────── Architecture ─────────────────────────


def test_ui_reaches_eligibility_only_through_the_store():
    files = [ROOT / "app.py", *(ROOT / "views").glob("*.py"), *(ROOT / "ui").glob("*.py")]
    banned = {"core.eligibility", "core.eligibility_view", "core.rules", "oi.intelligence.eligibility"}
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in banned, path
                if node.module == "core":
                    assert not {a.name for a in node.names} & {"eligibility", "eligibility_view", "rules"}, path
            if isinstance(node, ast.Import):
                assert not {a.name for a in node.names} & banned, path


def test_the_canonical_engine_is_not_modified_by_the_bridge():
    # The adapters import the engine; the engine never imports the demo.
    for path in (ROOT / "src" / "oi" / "intelligence" / "eligibility").rglob("*.py"):
        assert "core." not in path.read_text(encoding="utf-8").replace("core.py", ""), path
