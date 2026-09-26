"""Read-only access to the structured facts the rules may use.

Everything the rules know about a candidate or a job goes through here. It
reads declared answers, declarations, job locations, hard-constraint
requirements and the parameter layer, and nothing else: no free text, no
citizenship, no model output beyond the already-classified requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from oi.contracts import (
    AnswerState,
    AnswerType,
    CandidateProfile,
    EligibilityAnswer,
    JobRecord,
    RequirementClassification,
    RequirementFact,
    WorkAuthorizationDeclaration,
)
from oi.intelligence.eligibility.catalogue import ConstraintSpec, RuleCatalogue
from oi.intelligence.eligibility.models import EligibilityWarning, WarningCode
from oi.intelligence.eligibility.parameters import (
    FieldOfStudyParams,
    JobParameters,
    JobParameterSet,
    LanguageParams,
    MinExperienceParams,
)


# ───────────────────────────── Candidate side ─────────────────────────────


def known_answer(
    candidate: CandidateProfile, constraint_id: str, answer_key: str
) -> EligibilityAnswer | None:
    """The candidate's known answer for one key, or None.

    An answer with state "unknown" counts as missing. If the profile holds
    several known answers for the key that disagree, none of them is used:
    picking one would be deciding which fact is true.
    """

    answers = [
        answer
        for answer in candidate.eligibility_answers.get(constraint_id, [])
        if answer.answer_key == answer_key and answer.state is AnswerState.KNOWN
    ]
    if not answers:
        return None
    if any(answer.value != answers[0].value for answer in answers[1:]):
        return None
    return answers[0]


def work_authorization(
    candidate: CandidateProfile, country_code: str
) -> WorkAuthorizationDeclaration | None:
    """The candidate's declaration for one country. Citizenship is never read."""

    return next(
        (
            declaration
            for declaration in candidate.declarations.work_authorizations
            if declaration.country_code == country_code
        ),
        None,
    )


def answer_key_warnings(
    candidate: CandidateProfile, catalogue: RuleCatalogue
) -> list[EligibilityWarning]:
    """Warn about answers the catalogue does not know; they are ignored."""

    warnings: list[EligibilityWarning] = []
    for constraint_id, answers in sorted(candidate.eligibility_answers.items()):
        spec = catalogue.get(constraint_id)
        for answer in answers:
            if spec is None:
                message = (
                    f"Answer '{answer.answer_key}' is filed under unsupported "
                    f"constraint '{constraint_id}' and was ignored."
                )
            elif spec.answer_key(answer.answer_key) is None:
                message = (
                    f"Answer key '{answer.answer_key}' is not in the catalogue "
                    f"for {constraint_id} and was ignored."
                )
            else:
                continue
            warnings.append(
                EligibilityWarning(
                    code=WarningCode.UNKNOWN_ANSWER_KEY,
                    message=message,
                    constraint_id=constraint_id,
                )
            )
    return warnings


# ──────────────────────────────── Job side ────────────────────────────────


@dataclass(frozen=True)
class JobCountries:
    """Resolved location countries of a job."""

    codes: list[str]
    has_unresolved: bool
    evidence_ids: list[str]


def job_countries(job: JobRecord) -> JobCountries:
    """Distinct resolved countries, whether any location lacks one, and evidence."""

    codes = sorted(
        {location.country_code for location in job.locations if location.country_code}
    )
    has_unresolved = not job.locations or any(
        location.country_code is None for location in job.locations
    )
    evidence = resolvable_job_evidence(
        job, (eid for location in job.locations for eid in location.evidence_ids)
    )
    return JobCountries(codes, has_unresolved, evidence)


@dataclass(frozen=True)
class JobLocationContext:
    """One alternative location of a job, as the rules see it.

    Locations sharing a country are one alternative: every rule gives them the
    same answer. Locations without a country form one "unresolved" alternative,
    for which no country is invented.
    """

    key: str
    country_code: str | None
    evidence_ids: tuple[str, ...]


def job_location_contexts(job: JobRecord, unresolved_key: str) -> list[JobLocationContext]:
    """Alternative locations in country order, the unresolved one last.

    A job with no locations at all is a single unresolved alternative.
    """

    by_country: dict[str | None, list[str]] = {}
    for location in job.locations:
        by_country.setdefault(location.country_code, []).extend(location.evidence_ids)

    contexts = [
        JobLocationContext(
            code, code, tuple(resolvable_job_evidence(job, by_country[code]))
        )
        for code in sorted(code for code in by_country if code is not None)
    ]
    if None in by_country or not contexts:
        contexts.append(
            JobLocationContext(
                unresolved_key,
                None,
                tuple(resolvable_job_evidence(job, by_country.get(None, []))),
            )
        )
    return contexts


def hard_requirements(job: JobRecord) -> list[RequirementFact]:
    """The job's hard-constraint requirements, in requirement_id order."""

    if job.facts is None:
        return []
    return sorted(
        (
            requirement
            for requirement in job.facts.requirements
            if requirement.classification is RequirementClassification.HARD_CONSTRAINT
        ),
        key=lambda requirement: requirement.requirement_id,
    )


def resolvable_job_evidence(job: JobRecord, evidence_ids: Iterable[str]) -> list[str]:
    """Evidence IDs that resolve in job.evidence, de-duplicated, order kept.

    JobRecord does not check that requirement evidence resolves, so an outcome
    only cites what a reader could actually look up.
    """

    registry = {reference.evidence_id for reference in job.evidence}
    seen: list[str] = []
    for evidence_id in evidence_ids:
        if evidence_id in registry and evidence_id not in seen:
            seen.append(evidence_id)
    return seen


# ──────────────────────────── Parameter layer ─────────────────────────────


@dataclass(frozen=True)
class ResolvedParameters:
    """Parameters usable for one requirement, or None with the reason why."""

    parameters: JobParameters | None
    evidence_ids: list[str] = field(default_factory=list)
    warnings: list[EligibilityWarning] = field(default_factory=list)


def _vocabulary_problem(parameters: JobParameters, spec: ConstraintSpec) -> str | None:
    """Values the catalogue cannot evaluate, or None when all is usable."""

    if isinstance(parameters, FieldOfStudyParams):
        key = spec.answer_key("field_of_study")
        allowed = set(key.allowed_values or ()) if key else set()
        unknown = sorted(set(parameters.accepted) - allowed)
        if unknown:
            return f"fields {unknown} are not in the field_of_study vocabulary"

    if isinstance(parameters, LanguageParams):
        if spec.answer_key(f"level_{parameters.language}") is None:
            return f"language '{parameters.language}' has no answer key in the catalogue"

    if isinstance(parameters, MinExperienceParams):
        if parameters.answer_key is not None:
            key = spec.answer_key(parameters.answer_key)
            if key is None or key.answer_type is not AnswerType.BOOLEAN:
                return (
                    f"answer key '{parameters.answer_key}' is not a boolean key "
                    f"of {spec.constraint_id}"
                )
        elif spec.answer_key("prior_experience_months") is None:
            return "min_months needs the prior_experience_months answer key"

    return None


def resolve_parameters(
    job: JobRecord,
    requirement: RequirementFact,
    spec: ConstraintSpec,
    layer: JobParameterSet | None,
) -> ResolvedParameters:
    """Look up and check the parameter entry for one requirement.

    A missing entry is not a warning: the rule simply cannot compare. An entry
    that is present but unusable is ignored with a warning, so a curation
    mistake can make a rule UNKNOWN but never CONFLICT.
    """

    entry = layer.get(job.job_id, requirement.requirement_id) if layer else None
    if entry is None:
        return ResolvedParameters(None)

    problem: str | None = None
    if entry.constraint_id != requirement.constraint_id:
        problem = (
            f"entry is for {entry.constraint_id} but the requirement is "
            f"{requirement.constraint_id}"
        )
    elif entry.parameters.kind != spec.parameter_kind:
        problem = (
            f"kind '{entry.parameters.kind}' does not match "
            f"{spec.constraint_id} ('{spec.parameter_kind}')"
        )
    else:
        registry = {reference.evidence_id for reference in job.evidence}
        unresolved = [eid for eid in entry.evidence_ids if eid not in registry]
        if unresolved:
            problem = f"evidence {unresolved} does not resolve in the job"
        else:
            problem = _vocabulary_problem(entry.parameters, spec)

    if problem is not None:
        return ResolvedParameters(
            None,
            warnings=[
                EligibilityWarning(
                    code=WarningCode.INVALID_JOB_PARAMETER,
                    message=f"Job parameters ignored: {problem}.",
                    constraint_id=requirement.constraint_id,
                    requirement_id=requirement.requirement_id,
                )
            ],
        )

    return ResolvedParameters(entry.parameters, list(entry.evidence_ids))


def orphan_parameter_warnings(
    job: JobRecord, layer: JobParameterSet | None
) -> list[EligibilityWarning]:
    """Entries for this job whose requirement is not a hard constraint on it."""

    if layer is None:
        return []
    requirement_ids = {requirement.requirement_id for requirement in hard_requirements(job)}
    return [
        EligibilityWarning(
            code=WarningCode.ORPHAN_JOB_PARAMETER,
            message=(
                f"Job parameters for '{entry.requirement_id}' match no "
                "hard-constraint requirement on this job."
            ),
            constraint_id=entry.constraint_id,
            requirement_id=entry.requirement_id,
        )
        for entry in layer.for_job(job.job_id)
        if entry.requirement_id not in requirement_ids
    ]
