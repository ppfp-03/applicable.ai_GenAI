"""Engine behaviour that is the same for every rule.

Rules are replaced by recording fakes here, so these tests pin dispatch,
modality gating, warnings and aggregation independently of rule semantics.
"""

from __future__ import annotations

from datetime import date
from typing import Callable

import pytest

from oi.intelligence.eligibility import (
    EligibilityStatus,
    RuleStatus,
    UnknownCause,
    WarningCode,
    assess_eligibility,
    load_rule_catalogue,
)
from oi.intelligence.eligibility.engine import check_registry
from oi.intelligence.eligibility.rules import RULES
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    conflict,
    met,
    not_applicable,
)

from . import builders as b

CATALOGUE = load_rule_catalogue()
GRAD_PARAMS = {"kind": "grad_window", "start": "2027-01-01", "end": "2027-12-31"}


@pytest.fixture
def fake_rules(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[RuleContext]]:
    """Replace every rule with a fake; return the list of contexts it saw."""

    seen: list[RuleContext] = []

    def install(default: Finding = met("ok"), **per_rule: Finding) -> list[RuleContext]:
        for constraint_id in list(RULES):
            finding = per_rule.get(constraint_id, default)

            def fake(context: RuleContext, finding: Finding = finding) -> Finding:
                seen.append(context)
                return finding

            monkeypatch.setitem(RULES, constraint_id, fake)
        return seen

    return install


def by_rule(result, rule_id):
    return [o for o in result.outcomes if o.rule_id == rule_id]


def test_registry_matches_the_catalogue() -> None:
    check_registry(CATALOGUE, RULES)


def test_registry_mismatch_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(RULES, "HC_LANGUAGE")
    with pytest.raises(ValueError, match="HC_LANGUAGE"):
        assess_eligibility(b.candidate(), b.job(), CATALOGUE)


def test_every_constraint_is_listed_in_catalogue_order(fake_rules) -> None:
    fake_rules()
    result = assess_eligibility(b.candidate(), b.job(), CATALOGUE)
    assert [o.rule_id for o in result.outcomes] == CATALOGUE.constraint_ids


def test_unstated_constraints_are_not_applicable_without_calling_the_rule(
    fake_rules,
) -> None:
    seen = fake_rules()
    result = assess_eligibility(b.candidate(), b.job(), CATALOGUE)
    # Only the job-location rule ran; the seven requirement rules had no trigger.
    assert [c.spec.constraint_id for c in seen] == ["HC_LOCATION"]
    for outcome in result.outcomes[1:]:
        assert outcome.status is RuleStatus.NOT_APPLICABLE
        assert outcome.requirement_id is None
    assert result.status is EligibilityStatus.ELIGIBLE


@pytest.mark.parametrize("modality", ["preferred", "optional"])
def test_non_mandatory_requirements_are_not_gates(fake_rules, modality) -> None:
    seen = fake_rules(default=conflict("fails"))
    job = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", modality)])
    result = assess_eligibility(b.candidate(), job, CATALOGUE)
    grad = by_rule(result, "HC_GRAD_WINDOW")[0]
    assert grad.status is RuleStatus.NOT_APPLICABLE
    assert grad.requirement_id == "req-1"
    assert "HC_GRAD_WINDOW" not in [c.spec.constraint_id for c in seen]


def test_unspecified_modality_turns_conflict_into_unknown(fake_rules) -> None:
    fake_rules(HC_LOCATION=not_applicable("n/a"), HC_GRAD_WINDOW=conflict("fails"))
    job = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "unspecified")])
    result = assess_eligibility(b.candidate(), job, CATALOGUE)
    grad = by_rule(result, "HC_GRAD_WINDOW")[0]
    assert grad.status is RuleStatus.UNKNOWN
    assert grad.unknown_cause is UnknownCause.NON_MANDATORY_MISMATCH
    assert result.status is EligibilityStatus.UNCERTAIN


def test_unspecified_modality_keeps_met(fake_rules) -> None:
    fake_rules()
    job = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "unspecified")])
    result = assess_eligibility(b.candidate(), job, CATALOGUE)
    assert by_rule(result, "HC_GRAD_WINDOW")[0].status is RuleStatus.MET


def test_mandatory_conflict_makes_the_job_ineligible(fake_rules) -> None:
    fake_rules(HC_GRAD_WINDOW=conflict("fails"))
    job = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")])
    assert assess_eligibility(b.candidate(), job, CATALOGUE).status is (
        EligibilityStatus.INELIGIBLE
    )


def test_each_requirement_gets_its_own_outcome_in_id_order(fake_rules) -> None:
    fake_rules()
    job = b.job(
        requirements=[
            ("req-b", "HC_LANGUAGE", "mandatory"),
            ("req-a", "HC_LANGUAGE", "mandatory"),
        ]
    )
    result = assess_eligibility(b.candidate(), job, CATALOGUE)
    assert [o.requirement_id for o in by_rule(result, "HC_LANGUAGE")] == ["req-a", "req-b"]


def test_unsupported_constraint_is_a_warning_only(fake_rules) -> None:
    fake_rules()
    job = b.job(requirements=[("req-1", "work_authorization_nl", "mandatory")])
    result = assess_eligibility(b.candidate(), job, CATALOGUE)
    assert result.status is EligibilityStatus.ELIGIBLE
    assert [(w.code, w.requirement_id) for w in result.warnings] == [
        (WarningCode.UNSUPPORTED_CONSTRAINT, "req-1")
    ]
    assert all(o.requirement_id != "req-1" for o in result.outcomes)


def test_parameters_reach_the_rule_and_are_cited(fake_rules) -> None:
    seen = fake_rules()
    job = b.job(
        requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")],
        extra_evidence=["ev-window"],
    )
    layer = b.parameters(
        ("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS), evidence_ids=["ev-window"]
    )
    result = assess_eligibility(b.candidate(), job, CATALOGUE, job_parameters=layer)
    grad_context = next(c for c in seen if c.spec.constraint_id == "HC_GRAD_WINDOW")
    assert grad_context.parameters is not None
    assert by_rule(result, "HC_GRAD_WINDOW")[0].job_evidence_ids == [
        "ev-job-req-1",
        "ev-window",
    ]
    assert result.parameter_layer_version == "0.1-temporary"


def test_invalid_parameters_are_withheld_with_a_warning(fake_rules) -> None:
    seen = fake_rules()
    job = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")])
    layer = b.parameters(
        ("req-1", "HC_GRAD_WINDOW", {"kind": "degree_level", "min_level": "master"})
    )
    result = assess_eligibility(b.candidate(), job, CATALOGUE, job_parameters=layer)
    grad_context = next(c for c in seen if c.spec.constraint_id == "HC_GRAD_WINDOW")
    assert grad_context.parameters is None
    assert [w.code for w in result.warnings] == [WarningCode.INVALID_JOB_PARAMETER]


def test_warnings_from_all_sources_are_sorted(fake_rules) -> None:
    fake_rules()
    candidate = b.candidate(answers={("relocation_willingness", "willing"): True})
    job = b.job(requirements=[("req-1", "graduation_window", "mandatory")])
    layer = b.parameters(("req-9", "HC_GRAD_WINDOW", GRAD_PARAMS), evidence_ids=["x"])
    result = assess_eligibility(candidate, job, CATALOGUE, job_parameters=layer)
    assert [w.code for w in result.warnings] == [
        WarningCode.ORPHAN_JOB_PARAMETER,
        WarningCode.UNKNOWN_ANSWER_KEY,
        WarningCode.UNSUPPORTED_CONSTRAINT,
    ]


def test_same_input_gives_an_equal_result(fake_rules) -> None:
    candidate = b.candidate(
        answers={("HC_GRAD_WINDOW", "expected_graduation_date"): date(2027, 7, 15)}
    )
    job = b.job(requirements=[("req-1", "HC_GRAD_WINDOW", "mandatory")])
    layer = b.parameters(("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS))
    first = assess_eligibility(candidate, job, CATALOGUE, job_parameters=layer)
    second = assess_eligibility(candidate, job, CATALOGUE, job_parameters=layer)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_cited_evidence_always_resolves() -> None:
    # Real rules here, including requirement evidence that does not resolve.
    candidate = b.candidate(
        answers={("HC_GRAD_WINDOW", "expected_graduation_date"): date(2027, 7, 15)},
        allowed_countries=["NL"],
        work_auth=[("NL", True, False)],
    )
    job = b.job(
        requirements=[
            ("req-1", "HC_GRAD_WINDOW", "mandatory"),
            ("req-2", "HC_WORK_AUTH", "mandatory"),
        ]
    )
    data = job.model_dump(mode="json")
    data["facts"]["requirements"][0]["evidence_ids"].append("ev-dangling")
    job = type(job).model_validate(data)
    result = assess_eligibility(
        candidate,
        job,
        CATALOGUE,
        job_parameters=b.parameters(("req-1", "HC_GRAD_WINDOW", GRAD_PARAMS)),
    )
    job_ids = {e.evidence_id for e in job.evidence}
    candidate_ids = {e.evidence_id for e in candidate.provenance.evidence}
    for outcome in result.outcomes:
        assert set(outcome.job_evidence_ids) <= job_ids
        assert set(outcome.candidate_evidence_ids) <= candidate_ids
    # Not cited, but not silently lost either (FR-06).
    assert [(w.code, w.evidence_id) for w in result.warnings] == [
        (WarningCode.UNRESOLVED_EVIDENCE, "ev-dangling")
    ]
