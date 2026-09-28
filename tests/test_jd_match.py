"""Updated ranking: a role's job description, line by line against the CV.

core/jd_match.py reads each requirement's outcome from the rules when the
rules check it, compares skills and preferred fields with the CV itself, and
gives every line the CV does not cover one piece of fixed advice.
"""

import json
from pathlib import Path

import pytest

from core import jd_match, rules
from core.jd_match import GAP, MET, VERIFY

DEMO = json.loads((Path(__file__).resolve().parents[1] / "data" / "demo.json").read_text("utf-8"))
PROFILE = DEMO["profile"]
ROLES = {r["id"]: r for r in DEMO["roles"]}
CV = ["Python", "SQL", "Financial modelling", "React", "Figma", "Business Analyst Intern at Mediobanco"]

#: Every role the onboarding's Updated ranking can show, under any UK answer
#: and the declarations tests/test_onboarding_ranking.py tries.
REACHABLE = ["replai-pa", "bolton-strategy", "lazarde-ba", "morgan-product",
             "nestella-strategy", "jpmorrow-strategy", "deutsch-shanghai", "roshe-product"]


def crit(cid, status="met", have="", need=""):
    return rules.Criterion(cid, rules.CRITERION_NAMES[cid], status, "", f"{cid} detail", "", have, need)


def all_met(**over):
    return [over.get(c) or crit(c) for c in rules.CRITERIA]


def role(*requirements, **extra):
    return {"id": "r", "gaps": [], "description": {"summary": "s", "responsibilities": [], "requirements": list(requirements)}, **extra}


def req(kind, value=None):
    r = {"kind": kind, "text": f"{kind} line"}
    if value is not None:
        r["value"] = value
    return r


def only(lines):
    assert len(lines) == 1
    return lines[0]


def test_a_skill_the_cv_names_is_covered_without_advice() -> None:
    line = only(jd_match.lines(role(req("skill", "sql")), all_met(), PROFILE, CV))
    assert (line.status, line.advice) == (MET, "")


def test_a_skill_the_cv_does_not_name_is_a_gap_with_advice() -> None:
    line = only(jd_match.lines(role(req("skill", "A/B testing")), all_met(), PROFILE, CV))
    assert line.status == GAP
    assert "A/B testing" in line.advice and "CV" in line.advice


def test_skills_are_to_verify_before_a_cv_is_read() -> None:
    assert only(jd_match.lines(role(req("skill", "SQL")), all_met(), PROFILE, None)).status == VERIFY


def test_rule_criteria_keep_the_rules_outcome() -> None:
    criteria = all_met(language=crit("language", "not_met", "HSK 4", "HSK 6"), permission=crit("permission", "check"))
    lang, perm, deg = jd_match.lines(role(req("language"), req("permission"), req("degree")), criteria, PROFILE, CV)
    assert lang.status == GAP and "HSK 4" in lang.advice and "HSK 6" in lang.advice
    assert perm.status == VERIFY and perm.advice == jd_match.ADVICE["permission"]
    assert (deg.status, deg.advice) == (MET, "")


def test_a_preferred_field_is_compared_with_every_degree() -> None:
    cs, econ = jd_match.lines(role(req("preferred_field", "Computer Science"), req("preferred_field", "Economics")),
                              all_met(), PROFILE, CV)
    assert cs.status == GAP and "Computer Science" in cs.advice
    assert econ.status == MET  # the BSc Economics counts


def test_a_preferred_duration_is_always_to_verify() -> None:
    assert only(jd_match.lines(role(req("duration", 12)), all_met(), PROFILE, CV)).status == VERIFY


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        jd_match.lines(role(req("salary")), all_met(), PROFILE, CV)


def test_without_a_description_the_rules_and_fixture_gaps_are_shown() -> None:
    r = {"id": "r", "gaps": ["No payments experience"]}
    lines = jd_match.lines(r, all_met(field=crit("field", "check")), PROFILE, CV)
    assert [ln.kind for ln in lines] == [c for c in rules.CRITERIA if c != "location"] + ["other"]
    assert lines[-1].status == GAP and lines[-1].text == "No payments experience"
    assert next(ln for ln in lines if ln.kind == "field").status == VERIFY


@pytest.mark.parametrize("rid", REACHABLE)
def test_every_reachable_role_has_a_description_the_matcher_reads(rid) -> None:
    r = ROLES[rid]
    desc = r["description"]
    assert desc["summary"] and desc["responsibilities"] and desc["requirements"]
    lines = jd_match.lines(r, all_met(), PROFILE, CV)
    assert len(lines) == len(desc["requirements"])


@pytest.mark.parametrize("rid", REACHABLE)
def test_the_description_names_the_gap_the_role_card_shows(rid) -> None:
    # The row in Updated ranking shows the fixture's first gap: the opened
    # role must not contradict it, with the persona's CV.
    r = ROLES[rid]
    gaps = [ln for ln in jd_match.lines(r, all_met(), PROFILE, CV) if ln.status != MET]
    assert bool(gaps) == bool(r["gaps"])



def test_a_language_no_rule_checks_is_to_verify_not_covered() -> None:
    # Deutsch Bank asks for HSK 6; the rules do not check that level, so the
    # rules' "met" must not read as covered.
    r = ROLES["deutsch-shanghai"]
    lang = next(ln for ln in jd_match.lines(r, all_met(), PROFILE, CV, ["Mandarin"]) if ln.kind == "language")
    assert (lang.status, lang.advice) == (VERIFY, jd_match.ADVICE["language_unchecked"])
    checked = next(ln for ln in jd_match.lines(r, all_met(), PROFILE, CV) if ln.kind == "language")
    assert checked.status == MET
