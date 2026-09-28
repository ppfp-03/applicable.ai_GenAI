"""The normalized synthetic demo catalogue (oi.io.synthetic_normalized).

The faithful OI-50 catalogue stays the source truth and is only read. The
normalized one is controlled demo data: complete and comparable by
construction, every value classed SOURCE, NORMALIZED or SYNTHETIC_FILL.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from oi.intelligence.eligibility import assess_eligibility, load_job_parameters, load_rule_catalogue
from oi.intelligence.eligibility.catalogue import DEGREE_LEVELS
from oi.intelligence.eligibility.models import RuleStatus, UnknownCause
from oi.intelligence.eligibility.rules.language import FLUENT_LEVELS
from oi.io import normalized_catalogue as nc
from oi.io import synthetic_normalized as sn
from oi.io.synthetic_catalogue import get_synthetic_catalogue

ROOT = Path(__file__).resolve().parents[1]
FAITHFUL_SNAPSHOT_SHA256 = "c1932122e5fb1ab25b6a5e094290ec54db0c8981338747970325ee78ff734919"
FAITHFUL_PARAMETERS_SHA256 = "d0dd1af492ff3e3277c1a1d083188a8d5ddc824d5131f37d6dcead781bcc3998"
RULE_CATALOGUE_SHA256 = "b76a20322fcdcf114ce521a24b620d1a0cb2f9a437858b7fde4ca5ff53febe1c"
IDS = [f"SYN-JOB-{i:03d}" for i in range(1, 51)]
ANCHOR = datetime(2026, 9, 24, 10, 55, tzinfo=timezone.utc)
ROLE_FAMILIES = [
    "Strategy & Consulting", "Finance & Investment", "Markets & Trading", "Operations & Supply Chain",
    "Marketing & Communications", "Sales & Business Development", "Product", "Data & Analytics",
    "Risk & Compliance", "Economics & Research",
]
FIELD_ADDITIONS = ["marketing", "communications", "data_science", "information_technology", "law_policy"]
SKILL_ADDITIONS = {"Quantitative reasoning", "Supply chain", "Digital marketing", "Compliance",
                   "Risk analysis", "Econometrics"}
#: Faithful rows whose audit source is a real posting (see test_synthetic_catalogue).
RELABELLED_REAL = ["SYN-JOB-001", "SYN-JOB-002", "SYN-JOB-003", "SYN-JOB-004",
                   "SYN-JOB-005", "SYN-JOB-006", "SYN-JOB-010", "SYN-JOB-012"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def cat() -> nc.NormalizedCatalogue:
    return nc.get_normalized_catalogue()


@pytest.fixture(scope="module")
def jobs(cat):
    return {job.source_job_id: job for job in cat.snapshot.jobs}


@pytest.fixture(scope="module")
def faithful():
    return {job.source_job_id: job for job in get_synthetic_catalogue().jobs}


@pytest.fixture(scope="module")
def values(cat):
    return {job_id[len("synthetic-normalized:"):]: cat.values(job_id) for job_id in cat.provenance["jobs"]}


def evidence_doc(job, evidence_id: str) -> str:
    return next(e.document_id for e in job.evidence if e.evidence_id == evidence_id)


# --- The faithful catalogue is untouched --------------------------------------


def test_the_faithful_snapshot_is_byte_identical():
    assert sha(sn.FAITHFUL_SNAPSHOT) == FAITHFUL_SNAPSHOT_SHA256


def test_the_faithful_84_parameters_are_unchanged():
    assert sha(sn.FAITHFUL_PARAMETERS) == FAITHFUL_PARAMETERS_SHA256
    entries = load_job_parameters().entries
    assert len(entries) == 84
    assert all(e.job_id.startswith("synthetic:SYN-JOB-") for e in entries)


def test_the_canonical_rule_catalogue_is_unchanged_and_not_extended():
    assert sha(ROOT / "config" / "eligibility" / "rule_catalogue.json") == RULE_CATALOGUE_SHA256
    fields = load_rule_catalogue().get("HC_FIELD_OF_STUDY").answer_key("field_of_study").allowed_values
    assert not set(FIELD_ADDITIONS) & set(fields)


def test_the_faithful_catalogue_stays_available_separately(cat, faithful):
    assert len(faithful) == 50
    assert not {j.job_id for j in cat.snapshot.jobs} & {j.job_id for j in faithful.values()}
    source = (ROOT / "src" / "oi" / "io" / "normalized_catalogue.py").read_text(encoding="utf-8")
    assert "synthetic_catalogue" not in source.split('"""', 2)[2]  # no alias of the faithful loader


def test_the_provenance_names_the_exact_faithful_snapshot(cat):
    assert cat.provenance["faithful_snapshot_sha256"] == FAITHFUL_SNAPSHOT_SHA256
    assert cat.provenance["faithful_snapshot_id"] == "synthetic-oi50"


# --- Identity ---------------------------------------------------------------------


def test_exactly_fifty_unique_normalized_ids_in_order(cat):
    ids = [job.job_id for job in cat.snapshot.jobs]
    assert ids == [f"synthetic-normalized:{i}" for i in IDS]
    assert cat.snapshot.snapshot_id == "synthetic-oi50-normalized"


def test_every_job_is_clearly_synthetic(cat):
    for job in cat.snapshot.jobs:
        assert job.source == "synthetic-normalized"
        assert job.url == f"https://example.invalid/synthetic-normalized/{job.source_job_id}"
        assert job.discovery_kind.value == "synthetic_scenario"
        (doc,) = job.source_documents
        assert doc.source_ref == f"normalization:oi50-v1#{job.source_job_id}"
        assert "Synthetic demo data" in doc.text and "not from the posting" in doc.text


def test_the_posting_text_is_the_faithful_text(jobs, faithful):
    for sid, job in jobs.items():
        assert job.description.text == faithful[sid].description.text
        assert job.company == faithful[sid].company and job.title == faithful[sid].title


# --- Eligibility inputs --------------------------------------------------------------


def test_every_hard_requirement_has_parameters(cat):
    for job in cat.snapshot.jobs:
        for req in job.facts.requirements:
            if req.classification.value == "hard_constraint":
                entry = cat.parameters.get(job.job_id, req.requirement_id)
                assert entry is not None, (job.job_id, req.requirement_id)
                assert entry.constraint_id == req.constraint_id
                known = {e.evidence_id for e in job.evidence}
                assert set(entry.evidence_ids) <= known


def test_every_job_states_work_authorization_and_student_status(cat):
    for job in cat.snapshot.jobs:
        hard = Counter(r.constraint_id for r in job.facts.requirements if r.constraint_id)
        assert hard["HC_WORK_AUTH"] == 1 and hard["HC_STUDENT_STATUS"] == 1, job.job_id
        (auth,) = [cat.parameters.get(job.job_id, r.requirement_id).parameters
                   for r in job.facts.requirements if r.constraint_id == "HC_WORK_AUTH"]
        assert auth.country_code == job.locations[0].country_code


def test_the_approved_quotas_are_exact(cat, values):
    params = cat.parameters.entries
    assert Counter(v["sponsorship"]["value"] for v in values.values()) == {
        "offered": 18, "not_offered": 18, "not_stated": 14}
    assert Counter("+".join(e.parameters.accepted) for e in params if e.constraint_id == "HC_STUDENT_STATUS") == {
        "enrolled_student": 30, "enrolled_student+recent_graduate": 15, "recent_graduate": 5}
    assert Counter(v["degree_level"]["value"] for v in values.values()) == {"bachelor": 30, "master": 17, "phd": 3}
    assert Counter(v["experience_months"]["value"] for v in values.values()) == {0: 28, 3: 12, 6: 7, 12: 3}


def run_engine(cat, candidate):
    return [assess_eligibility(candidate, job, cat.rule_catalogue, job_parameters=cat.parameters)
            for job in cat.snapshot.jobs]


def test_no_outcome_is_unknown_for_lack_of_job_data():
    from core import eligibility as bridge

    cat = nc.get_normalized_catalogue()
    profile = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["profile"]
    answers = {"uk_work": "no"}
    results = run_engine(cat, bridge.candidate(profile, answers))
    assert not [w for r in results for w in r.warnings]
    job_side = [(r.job_id, o) for r in results for o in r.outcomes
                if o.unknown_cause in {UnknownCause.JOB_PARAMETER_MISSING, UnknownCause.JOB_DATA_AMBIGUOUS}]
    # The one approved job-side UNKNOWN: sponsorship the posting does not state
    # (the not_stated quota), met by a candidate who needs sponsorship.
    for job_id, outcome in job_side:
        assert outcome.rule_id == "HC_WORK_AUTH"
        assert cat.parameters.get(job_id, outcome.requirement_id).parameters.employer_sponsorship == "not_stated"


def test_extended_fields_are_evaluable_only_in_the_normalized_layer(cat):
    fields = cat.rule_catalogue.get("HC_FIELD_OF_STUDY").answer_key("field_of_study").allowed_values
    assert set(FIELD_ADDITIONS) <= set(fields)
    used = {f for e in cat.parameters.entries if e.constraint_id == "HC_FIELD_OF_STUDY" for f in e.parameters.accepted}
    assert used <= set(fields)
    assert not [e for e in cat.parameters.entries
                if e.constraint_id == "HC_FIELD_OF_STUDY" and e.parameters.related_accepted]


# --- Approved mappings ------------------------------------------------------------------


RULES = json.loads(sn.RULES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("text, expected", [
    ("• English fluency.", [("en", "SELF:fluent")]),
    ("• English: good professional level.", [("en", "CEFR:B2")]),
    ("• English: professional.", [("en", "CEFR:B2")]),
    ("• English: strong written and spoken.", [("en", "CEFR:C1")]),
    ("• English: excellent written and spoken.", [("en", "CEFR:C1")]),
    ("• Italian: native/fluent.", [("it", "SELF:fluent")]),
    ("• Spanish: fluent/flawless spoken and written.", [("es", "SELF:fluent")]),
    ("• German: near-native.", [("de", "CEFR:C2")]),
    ("• Fluent business Mandarin AND English.", [("zh", "SELF:fluent"), ("en", "SELF:fluent")]),
])
def test_language_wording_map(text, expected):
    assert sn.languages(text, RULES)[0] == expected


def test_summer_is_june_to_september_and_spans_several_summers():
    assert sn.grad_window("• Expected university graduation: summer 2028.") == (date(2028, 6, 1), date(2028, 9, 30))
    assert sn.grad_window("• Summer 2027 OR Summer 2028.") == (date(2027, 6, 1), date(2028, 9, 30))


def test_experience_ranges_use_their_lower_bound_but_internships_are_not_months():
    assert sn.experience_lower_bound("• 0-3 years of experience, inclusive.", RULES) == 0
    assert sn.experience_lower_bound("• 2-4 years of experience.", RULES) == 24
    assert sn.experience_lower_bound("• 1-2 previous internships in consulting.", RULES) is None
    assert sn.experience_lower_bound("• 1-2 relevant years applies ONLY to the alternative.", RULES) is None


def test_related_wording_broadens_the_accepted_fields_deterministically():
    accepted, _, related, _ = sn.fields_of_study("• Finance OR Accounting OR Economics OR a similar subject.", RULES)
    assert related and accepted == ["finance", "accounting", "economics"]
    assert sn.broadened(accepted, RULES) == ["finance", "accounting", "economics", "statistics", "mathematics"]


def test_bac_plus_n_is_master_and_bachelor_or_master_is_bachelor(cat):
    for sid, level in (("SYN-JOB-019", "master"), ("SYN-JOB-023", "master"), ("SYN-JOB-011", "bachelor")):
        entry = next(e for e in cat.parameters.entries
                     if e.job_id == f"synthetic-normalized:{sid}" and e.constraint_id == "HC_DEGREE_LEVEL")
        assert entry.parameters.min_level == level


def test_stated_internship_experience_is_filled_never_read_as_none(cat, values):
    for sid in ("SYN-JOB-004", "SYN-JOB-033", "SYN-JOB-038", "SYN-JOB-047"):
        assert values[sid]["experience_months"]["class"] == "SYNTHETIC_FILL"
        assert values[sid]["experience_months"]["value"] > 0


def test_multiple_explicit_languages_are_split(jobs, cat):
    langs = sorted(e.parameters.language for e in cat.parameters.entries
                   if e.job_id == "synthetic-normalized:SYN-JOB-018" and e.constraint_id == "HC_LANGUAGE")
    assert langs == ["en", "zh"]


# --- Language comparability ------------------------------------------------------------

MANDARIN_ALTERNATIVES = ("SYN-JOB-012", "SYN-JOB-017", "SYN-JOB-020")


def language_candidate(levels: dict[str, str]):
    """The demo candidate with its language answers replaced by `levels`.

    The answers reuse one existing answer's evidence: only the level is under test.
    """
    from core import eligibility as bridge
    from oi.contracts import CandidateProfile

    profile = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["profile"]
    data = bridge.candidate(profile, {}).model_dump(mode="json")
    template = data["eligibility_answers"]["HC_LANGUAGE"][0]
    data["eligibility_answers"]["HC_LANGUAGE"] = [
        dict(template, answer_key=f"level_{code}", value=level) for code, level in levels.items()]
    return CandidateProfile.model_validate(data)


def language_outcomes(cat, candidate, sids=None):
    jobs = [j for j in cat.snapshot.jobs if sids is None or j.source_job_id in sids]
    results = [assess_eligibility(candidate, job, cat.rule_catalogue, job_parameters=cat.parameters)
               for job in jobs]
    assert not [w for r in results for w in r.warnings]
    return [(r.job_id, o) for r in results for o in r.outcomes if o.rule_id == "HC_LANGUAGE"]


def test_the_mandarin_alternatives_use_hsk_4_as_a_labelled_fill(cat, jobs, faithful):
    for sid in MANDARIN_ALTERNATIVES:
        job = jobs[sid]
        (req,) = [r for r in job.facts.requirements if r.constraint_id == "HC_LANGUAGE"
                  and cat.parameters.get(job.job_id, r.requirement_id).parameters.language == "zh"]
        params = cat.parameters.get(job.job_id, req.requirement_id).parameters
        assert (params.scale, params.min_level) == ("HSK", "4")
        prov = cat.provenance["jobs"][job.job_id]["requirements"][req.requirement_id]
        assert prov["class"] == "SYNTHETIC_FILL" and prov["rule"] == "alternatives_convention:zh=HSK:4"
        # The posting's own words are kept; HSK 4 is stated only in the normalization document.
        (source_req,) = [r for r in faithful[sid].facts.requirements if r.constraint_id == "HC_LANGUAGE"]
        assert req.text == source_req.text and "HSK" not in req.text
        assert "HSK" not in job.description.text
        assert "Language: Mandarin, HSK:4." in job.source_documents[0].text


@pytest.mark.parametrize("answer, status", [("HSK:4", RuleStatus.MET), ("HSK:6", RuleStatus.MET),
                                            ("HSK:3", RuleStatus.CONFLICT)])
def test_an_hsk_answer_is_compared_with_the_mandarin_requirement(cat, answer, status):
    outcomes = language_outcomes(cat, language_candidate({"zh": answer, "en": "SELF:fluent"}),
                                 MANDARIN_ALTERNATIVES)
    zh = [o for _, o in outcomes if "ZH" in o.reason]
    assert len(zh) == 3
    for outcome in zh:
        assert outcome.status is status
        assert "different scales" not in outcome.reason


def test_ordinary_answers_are_comparable_with_every_normalized_language_requirement(cat):
    # Candidates answer English and European languages on CEFR, Mandarin on HSK.
    ordinary = {"en": "CEFR:C1", "zh": "HSK:5", "it": "CEFR:B2", "de": "CEFR:B2",
                "fr": "CEFR:B2", "es": "CEFR:B2", "nl": "CEFR:B2"}
    outcomes = language_outcomes(cat, language_candidate(ordinary))
    # One outcome per requirement and job country (SYN-JOB-008 has offices in two countries).
    assert {o.requirement_id for _, o in outcomes} == {
        e.requirement_id for e in cat.parameters.entries if e.constraint_id == "HC_LANGUAGE"}
    assert not [(job_id, o.reason) for job_id, o in outcomes if o.status is RuleStatus.UNKNOWN]


def test_no_normalized_language_stays_on_an_uncomparable_fluent_scale(cat):
    for entry in cat.parameters.entries:
        p = entry.parameters
        if entry.constraint_id == "HC_LANGUAGE" and (p.scale, p.min_level) == ("SELF", "fluent"):
            assert p.language in FLUENT_LEVELS, entry.requirement_id


def test_fluent_moved_onto_cefr_is_a_fill_and_the_faithful_layer_keeps_fluent(cat):
    faithful_params = {(e.job_id, e.requirement_id): e.parameters for e in load_job_parameters().entries}
    moved = 0
    for job_id, job in cat.provenance["jobs"].items():
        for req_id, prov in job["requirements"].items():
            if prov["constraint_id"] == "HC_LANGUAGE" and "fluent_as_cefr_c1" in prov["rule"]:
                moved += 1
                assert prov["class"] == "SYNTHETIC_FILL"
                assert (prov["parameters"]["scale"], prov["parameters"]["min_level"]) == ("CEFR", "C1")
                sid = job_id.split(":", 1)[1]
                original = faithful_params.get((f"synthetic:{sid}", prov["faithful_requirement_id"]))
                if original is not None:
                    assert (original.scale, original.min_level) == ("SELF", "fluent")
    assert moved == 11


# --- Provenance of broad mappings ----------------------------------------------------------


def test_broad_or_default_mappings_are_never_source_or_normalized(cat, values):
    rules = RULES
    broad_fields = set(rules["broad_field_terms"])
    for sid, v in values.items():
        fields = v["fields_of_study"]
        if fields["rule"] == "role_family_default_fields" or "related_broadened" in fields["rule"] \
                or "broad_terms" in fields["rule"]:
            assert fields["class"] == "SYNTHETIC_FILL", sid
        family = v["role_family"]
        keyword = family["rule"].removeprefix("title_keyword:")
        broad_family = {k for r in rules["role_family_title_rules"] for k in r.get("broad", [])}
        if family["rule"] == "least_represented_family" or keyword in broad_family:
            assert family["class"] == "SYNTHETIC_FILL", sid
        broad_skill = {k for e in rules["skill_keywords"] for k in e.get("broad", [])}
        for skill in v["skills"]:
            if skill["rule"] == "role_family_skill_pool" or skill["rule"].removeprefix("skill_keyword:") in broad_skill:
                assert skill["class"] == "SYNTHETIC_FILL", (sid, skill)
    assert values["SYN-JOB-008"]["sponsorship"]["class"] == "SYNTHETIC_FILL"
    assert values["SYN-JOB-027"]["sponsorship"]["class"] == "NORMALIZED"
    assert values["SYN-JOB-015"]["role_family"] == {**values["SYN-JOB-015"]["role_family"],
                                                     "value": "Markets & Trading", "class": "SYNTHETIC_FILL"}
    assert broad_fields


# --- Ranking inputs -----------------------------------------------------------------------


def test_every_job_has_exactly_one_approved_role_family(jobs, values):
    for sid, job in jobs.items():
        assert job.facts.role_family.value in ROLE_FAMILIES
        assert values[sid]["role_family"]["value"] == job.facts.role_family.value


def test_every_job_has_four_to_six_vocabulary_skills(cat, jobs):
    vocabulary = {s["name"] for s in json.loads(sn.SKILLS_PATH.read_text(encoding="utf-8"))["skills"]}
    for job in jobs.values():
        skills = [s.value for s in job.facts.skills]
        assert 4 <= len(skills) <= 6 and len(set(skills)) == len(skills)
        assert set(skills) <= vocabulary


def test_every_job_has_complete_profile_fit_inputs(cat):
    fields = set(cat.rule_catalogue.get("HC_FIELD_OF_STUDY").answer_key("field_of_study").allowed_values)
    for job in cat.snapshot.jobs:
        inputs = cat.profile_inputs(job.job_id)
        assert inputs.role_family in ROLE_FAMILIES
        assert 4 <= len(inputs.skills) <= 6
        assert inputs.degree_level in DEGREE_LEVELS
        assert inputs.any_field or (inputs.fields_of_study and set(inputs.fields_of_study) <= fields)
        assert isinstance(inputs.experience_months, int) and inputs.experience_months >= 0


def test_every_job_has_a_future_deadline_anchored_to_the_demo_clock(jobs, faithful, values):
    for sid, job in jobs.items():
        assert job.deadline_at is not None and job.deadline_at > ANCHOR
        assert job.deadline_at - ANCHOR <= timedelta(days=240)
        if faithful[sid].deadline_at is not None:
            assert job.deadline_at == faithful[sid].deadline_at
            assert values[sid]["deadline_at"]["class"] == "SOURCE"
    filled = sorted((job.deadline_at.date() - ANCHOR.date()).days
                    for sid, job in jobs.items() if faithful[sid].deadline_at is None)
    buckets = Counter(next(n for n, (lo, hi) in enumerate([(1, 7), (8, 14), (15, 30), (31, 60), (61, 120)])
                           if lo <= d <= hi) for d in filled)
    assert buckets == {0: 6, 1: 8, 2: 12, 3: 12, 4: 8}


def test_freshness_is_simulated_and_never_in_the_future(cat):
    assert cat.snapshot.created_at == ANCHOR
    for job in cat.snapshot.jobs:
        assert job.source_published_at is None and job.source_updated_at is None
        assert ANCHOR - timedelta(days=30) <= job.first_seen_at <= ANCHOR
        assert job.last_seen_at == ANCHOR


# --- Provenance ------------------------------------------------------------------------------


def test_every_value_is_classed_with_a_rule(values):
    for sid, v in values.items():
        items = [v[k] for k in ("primary_country", "role_family", "sponsorship", "degree_level",
                                "fields_of_study", "experience_months", "deadline_at", "first_seen_at",
                                "discovery_kind")] + list(v["skills"])
        for item in items:
            assert item["class"] in nc.CLASSES and item["rule"], (sid, item)


def test_every_requirement_is_classed(cat, jobs):
    for sid, job in jobs.items():
        prov = cat.provenance["jobs"][job.job_id]["requirements"]
        assert set(prov) == {r.requirement_id for r in job.facts.requirements}
        assert all(p["class"] in nc.CLASSES and p["rule"] for p in prov.values())


def test_fills_cite_only_the_normalization_document(cat, jobs, values):
    for sid, job in jobs.items():
        doc = f"synthetic-normalized:{sid}:normalization"
        for key, item in values[sid].items():
            for entry in item if isinstance(item, list) else [item]:
                if entry["class"] == "SYNTHETIC_FILL" and "evidence_id" in entry:
                    assert evidence_doc(job, entry["evidence_id"]) == doc, (sid, key)
        prov = cat.provenance["jobs"][job.job_id]["requirements"]
        for req in job.facts.requirements:
            if prov[req.requirement_id]["class"] == "SYNTHETIC_FILL" and prov[req.requirement_id]["faithful_requirement_id"] is None:
                assert {evidence_doc(job, e) for e in req.evidence_ids} == {doc}


def test_source_values_equal_the_faithful_ones(cat, jobs, faithful):
    faithful_params = {(e.job_id, e.requirement_id): e.parameters for e in load_job_parameters().entries}
    for sid, job in jobs.items():
        prov = cat.provenance["jobs"][job.job_id]["requirements"]
        for req in job.facts.requirements:
            p = prov[req.requirement_id]
            if p["class"] == "SOURCE" and p["constraint_id"]:
                original = faithful_params[(f"synthetic:{sid}", p["faithful_requirement_id"])]
                assert cat.parameters.get(job.job_id, req.requirement_id).parameters == original
        assert [loc.country_code for loc in job.locations] == [loc.country_code for loc in faithful[sid].locations]


def test_no_audit_url_or_real_source_link_is_present():
    for path in (sn.SNAPSHOT_PATH, sn.PARAMETERS_PATH, sn.PROVENANCE_PATH, sn.RULES_PATH, sn.SKILLS_PATH):
        text = path.read_text(encoding="utf-8")
        urls = re.findall(r"https?://[^\s\"]+", text)
        assert all(u.startswith("https://example.invalid/synthetic-normalized/SYN-JOB-") for u in urls), path
        assert "greenhouse" not in text.lower() and "audit" not in text.lower(), path


# --- Determinism and independence ----------------------------------------------------------------


def test_generation_is_deterministic_and_the_committed_files_are_current():
    first, second = sn.render(), sn.render()
    assert first == second
    for path, text in first.items():
        assert path.read_text(encoding="utf-8") == text, path
    assert sn.main(["--check"]) == 0


def test_the_generator_reads_no_candidate():
    tree = ast.parse((ROOT / "src" / "oi" / "io" / "synthetic_normalized.py").read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not {m for m in imported if m and (m.startswith("core") or m.startswith("streamlit"))}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | {
        a.arg for n in ast.walk(tree) if isinstance(n, ast.arguments) for a in n.args}
    assert not [n for n in names if "candidate" in n.lower() or "preference" in n.lower()]
    strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not [s for s in strings if "demo.json" in s or "preferred_cities" in s]


def test_the_fill_order_depends_only_on_the_job():
    assert sn.order_key("sponsorship", "SYN-JOB-001") == hashlib.sha256(b"sponsorship:SYN-JOB-001").hexdigest()


# --- Evaluation boundary ---------------------------------------------------------------------------


def test_the_normalized_catalogue_is_never_evaluation_data(cat):
    assert nc.EVALUATION_USE == "excluded"
    assert cat.provenance["evaluation_use"] == "excluded"
    assert RULES["evaluation_use"] == "excluded"
    ids = {job.job_id for job in cat.snapshot.jobs}
    assert not ids & {f"synthetic:{sid}" for sid in RELABELLED_REAL}


# --- Shared skills vocabulary ------------------------------------------------------------------------


def test_one_shared_skills_vocabulary_keeps_every_existing_skill():
    vocab = json.loads(sn.SKILLS_PATH.read_text(encoding="utf-8"))["skills"]
    names = [s["name"] for s in vocab]
    assert len({n.lower() for n in names}) == len(names)
    stories = json.loads((ROOT / "data" / "stories.json").read_text(encoding="utf-8"))["stories"]
    demo = json.loads((ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["roles"]
    existing = {k for s in stories for k in s["sk"]} | {
        q["value"] for r in demo for q in r.get("description", {}).get("requirements", []) if q["kind"] == "skill"}
    assert existing <= set(names)
    assert {s["name"] for s in vocab if s["origin"] == "normalized_demo"} == SKILL_ADDITIONS
