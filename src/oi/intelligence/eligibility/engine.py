"""assess_eligibility: dispatch, modality gate, warnings and aggregation.

The engine owns everything that must be the same for every rule:

- each catalogue constraint appears in the result, in catalogue order;
- a constraint the job does not state is NOT_APPLICABLE;
- a requirement stated as preferred or optional is NOT_APPLICABLE, because it
  is not a hard gate;
- a failing comparison on a requirement whose modality is unspecified is
  UNKNOWN, never CONFLICT: only an explicitly mandatory requirement excludes;
- constraint IDs outside the catalogue only produce warnings;
- CONFLICT beats UNKNOWN beats ELIGIBLE.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from oi.contracts import CandidateProfile, JobRecord, RequirementFact, RequirementModality
from oi.intelligence.eligibility.catalogue import ConstraintSpec, RuleCatalogue
from oi.intelligence.eligibility.inputs import (
    answer_key_warnings,
    hard_requirements,
    orphan_parameter_warnings,
    resolvable_job_evidence,
    resolve_parameters,
)
from oi.intelligence.eligibility.models import (
    EligibilityResult,
    EligibilityWarning,
    RuleOutcome,
    RuleStatus,
    UnknownCause,
    WarningCode,
    aggregate_status,
    collect_missing_field_paths,
)
from oi.intelligence.eligibility.parameters import JobParameterSet
from oi.intelligence.eligibility.rules import RULES
from oi.intelligence.eligibility.rules.base import (
    Finding,
    RuleContext,
    RuleFn,
    not_applicable,
    unknown,
)

_NOT_A_GATE = (RequirementModality.PREFERRED, RequirementModality.OPTIONAL)


def check_registry(catalogue: RuleCatalogue, rules: Mapping[str, RuleFn]) -> None:
    """Every catalogue constraint has a rule and every rule is catalogued.

    Raises:
        ValueError: If the two sets differ.
    """

    catalogued, registered = set(catalogue.constraint_ids), set(rules)
    if catalogued != registered:
        raise ValueError(
            "rule registry and catalogue disagree: "
            f"without rule {sorted(catalogued - registered)}, "
            f"not catalogued {sorted(registered - catalogued)}"
        )


def _unique(ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def _outcome(
    spec: ConstraintSpec,
    finding: Finding,
    job: JobRecord,
    requirement: RequirementFact | None = None,
    parameter_evidence: Iterable[str] = (),
) -> RuleOutcome:
    job_evidence = [*(requirement.evidence_ids if requirement else ()), *parameter_evidence]
    return RuleOutcome(
        rule_id=spec.constraint_id,
        status=finding.status,
        candidate_evidence_ids=_unique(finding.candidate_evidence_ids),
        job_evidence_ids=resolvable_job_evidence(
            job, [*job_evidence, *finding.job_evidence_ids]
        ),
        reason=finding.reason,
        requirement_id=requirement.requirement_id if requirement else None,
        unknown_cause=finding.unknown_cause,
        missing_field_paths=sorted(set(finding.missing_field_paths)),
        rule_version=spec.rule_version,
    )


def _gate_unspecified(finding: Finding) -> Finding:
    """An unspecified-modality requirement can inform, not exclude."""

    if finding.status is not RuleStatus.CONFLICT:
        return finding
    return unknown(
        UnknownCause.NON_MANDATORY_MISMATCH,
        f"{finding.reason} The posting does not say this is mandatory, "
        "so it is not treated as a conflict.",
        finding.candidate_evidence_ids,
        finding.job_evidence_ids,
    )


def assess_eligibility(
    candidate: CandidateProfile,
    job: JobRecord,
    rule_catalogue: RuleCatalogue,
    *,
    job_parameters: JobParameterSet | None = None,
) -> EligibilityResult:
    """Decide whether `candidate` may apply to `job` under the catalogue.

    Args:
        candidate: The parsed and corrected candidate profile.
        job: The enriched job; only hard-constraint requirements are read.
        rule_catalogue: The internal catalogue naming the supported rules.
        job_parameters: The temporary job-side parameter layer. Without it,
            every parameter-driven rule is UNKNOWN, never CONFLICT.

    Returns:
        One EligibilityResult listing every catalogue constraint.

    Raises:
        ValueError: If the catalogue and the rule registry disagree.
    """

    check_registry(rule_catalogue, RULES)

    requirements = hard_requirements(job)
    warnings: list[EligibilityWarning] = [
        *answer_key_warnings(candidate, rule_catalogue),
        *orphan_parameter_warnings(job, job_parameters),
    ]
    for requirement in requirements:
        if rule_catalogue.get(requirement.constraint_id or "") is None:
            warnings.append(
                EligibilityWarning(
                    code=WarningCode.UNSUPPORTED_CONSTRAINT,
                    message=(
                        f"Constraint '{requirement.constraint_id}' is not in the "
                        "rule catalogue; it was not treated as a hard gate."
                    ),
                    constraint_id=requirement.constraint_id,
                    requirement_id=requirement.requirement_id,
                )
            )

    outcomes: list[RuleOutcome] = []
    for spec in rule_catalogue.constraints:
        rule = RULES[spec.constraint_id]

        if spec.trigger == "job_location":
            finding = rule(RuleContext(candidate, job, spec))
            outcomes.append(_outcome(spec, finding, job))
            continue

        matching = [r for r in requirements if r.constraint_id == spec.constraint_id]
        if not matching:
            outcomes.append(
                _outcome(
                    spec,
                    not_applicable(f"The posting states no {spec.label.lower()} requirement."),
                    job,
                )
            )
            continue

        for requirement in matching:
            if requirement.modality in _NOT_A_GATE:
                finding = not_applicable(
                    f"{spec.label} is stated as {requirement.modality.value}, "
                    "not as a hard requirement."
                )
                outcomes.append(_outcome(spec, finding, job, requirement))
                continue

            resolved = resolve_parameters(job, requirement, spec, job_parameters)
            warnings.extend(resolved.warnings)
            finding = rule(
                RuleContext(candidate, job, spec, requirement, resolved.parameters)
            )
            if requirement.modality is RequirementModality.UNSPECIFIED:
                finding = _gate_unspecified(finding)
            outcomes.append(
                _outcome(spec, finding, job, requirement, resolved.evidence_ids)
            )

    return EligibilityResult(
        candidate_id=candidate.candidate_id,
        job_id=job.job_id,
        catalogue_version=rule_catalogue.catalogue_version,
        parameter_layer_version=job_parameters.layer_version if job_parameters else None,
        status=aggregate_status(outcomes),
        outcomes=outcomes,
        missing_field_paths=collect_missing_field_paths(outcomes),
        warnings=sorted(warnings, key=EligibilityWarning.sort_key),
    )
