"""assess_eligibility: dispatch, modality gate, warnings and aggregation.

The engine owns everything that must be the same for every rule:

- each catalogue constraint appears in the result, in catalogue order;
- a constraint the job does not state is NOT_APPLICABLE;
- a requirement stated as preferred or optional is NOT_APPLICABLE, because it
  is not a hard gate;
- a failing comparison on a requirement whose modality is unspecified is
  UNKNOWN, never CONFLICT: only an explicitly mandatory requirement excludes;
- constraint IDs outside the catalogue only produce warnings;
- every rule is evaluated separately for each alternative job location;
- within a location, CONFLICT beats UNKNOWN beats ELIGIBLE;
- across locations, one eligible location is enough, otherwise one uncertain
  location keeps the job uncertain, and only all-incompatible is ineligible.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from oi.contracts import CandidateProfile, JobRecord, RequirementFact, RequirementModality
from oi.intelligence.eligibility.catalogue import ConstraintSpec, RuleCatalogue
from oi.intelligence.eligibility.inputs import (
    JobLocationContext,
    answer_key_warnings,
    hard_requirements,
    job_location_contexts,
    orphan_parameter_warnings,
    resolvable_job_evidence,
    resolve_parameters,
    unresolved_evidence_warnings,
)
from oi.intelligence.eligibility.models import (
    UNRESOLVED_LOCATION,
    EligibilityResult,
    EligibilityWarning,
    LocationAssessment,
    RuleOutcome,
    RuleStatus,
    UnknownCause,
    WarningCode,
    aggregate_locations,
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
    location_key: str,
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
        location_key=location_key,
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
        *unresolved_evidence_warnings(job),
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

    locations: list[LocationAssessment] = []
    for location in job_location_contexts(job, UNRESOLVED_LOCATION):
        outcomes = _assess_location(
            candidate,
            job,
            rule_catalogue,
            requirements,
            job_parameters,
            location,
            warnings,
        )
        locations.append(
            LocationAssessment(
                location_key=location.key,
                country_code=location.country_code,
                status=aggregate_status(outcomes),
                outcomes=outcomes,
            )
        )

    all_outcomes = [outcome for location in locations for outcome in location.outcomes]
    # Parameter warnings repeat once per location; report each once.
    unique_warnings = {warning.sort_key(): warning for warning in warnings}
    return EligibilityResult(
        candidate_id=candidate.candidate_id,
        job_id=job.job_id,
        catalogue_version=rule_catalogue.catalogue_version,
        parameter_layer_version=job_parameters.layer_version if job_parameters else None,
        status=aggregate_locations(locations),
        outcomes=all_outcomes,
        missing_field_paths=collect_missing_field_paths(all_outcomes),
        warnings=[unique_warnings[key] for key in sorted(unique_warnings)],
        locations=locations,
    )


def _assess_location(
    candidate: CandidateProfile,
    job: JobRecord,
    rule_catalogue: RuleCatalogue,
    requirements: list[RequirementFact],
    job_parameters: JobParameterSet | None,
    location: JobLocationContext,
    warnings: list[EligibilityWarning],
) -> list[RuleOutcome]:
    """Every catalogue constraint, evaluated for one alternative location."""

    def context(spec, requirement=None, parameters=None) -> RuleContext:
        return RuleContext(
            candidate,
            job,
            spec,
            requirement,
            parameters,
            location.country_code,
            location.evidence_ids,
        )

    outcomes: list[RuleOutcome] = []
    for spec in rule_catalogue.constraints:
        rule = RULES[spec.constraint_id]

        if spec.trigger == "job_location":
            outcomes.append(_outcome(spec, rule(context(spec)), job, location.key))
            continue

        matching = [r for r in requirements if r.constraint_id == spec.constraint_id]
        if not matching:
            finding = not_applicable(
                f"The posting states no {spec.label.lower()} requirement."
            )
            outcomes.append(_outcome(spec, finding, job, location.key))
            continue

        for requirement in matching:
            if requirement.modality in _NOT_A_GATE:
                finding = not_applicable(
                    f"{spec.label} is stated as {requirement.modality.value}, "
                    "not as a hard requirement."
                )
                outcomes.append(_outcome(spec, finding, job, location.key, requirement))
                continue

            resolved = resolve_parameters(job, requirement, spec, job_parameters)
            warnings.extend(resolved.warnings)
            finding = rule(context(spec, requirement, resolved.parameters))
            if requirement.modality is RequirementModality.UNSPECIFIED:
                finding = _gate_unspecified(finding)
            outcomes.append(
                _outcome(
                    spec, finding, job, location.key, requirement, resolved.evidence_ids
                )
            )
    return outcomes
