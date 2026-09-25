"""Result envelopes of the eligibility engine.

These are internal, versioned shapes (`eligibility-0.1-internal`). They follow
the design-only RuleOutcome of PROJECT_CONTEXT section F and add the fields the
engine needs to be auditable; they are not a frozen shared contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Literal

from pydantic import model_validator

from oi.contracts import CandidateFieldPath, ContractModel, NonEmptyStr

ELIGIBILITY_SCHEMA_VERSION = "eligibility-0.1-internal"


class RuleStatus(str, Enum):
    """Outcome of one rule for one candidate-job pair."""

    MET = "met"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class UnknownCause(str, Enum):
    """Why a rule could not decide. Only CANDIDATE_MISSING is askable."""

    CANDIDATE_MISSING = "candidate_missing"
    JOB_PARAMETER_MISSING = "job_parameter_missing"
    JOB_DATA_AMBIGUOUS = "job_data_ambiguous"
    POLICY_UNDECIDED = "policy_undecided"
    NON_MANDATORY_MISMATCH = "non_mandatory_mismatch"


class EligibilityStatus(str, Enum):
    """Aggregate standing of one job for one candidate."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"


class WarningCode(str, Enum):
    """Data problems worth reporting that never change the status."""

    UNSUPPORTED_CONSTRAINT = "unsupported_constraint"
    UNKNOWN_ANSWER_KEY = "unknown_answer_key"
    INVALID_JOB_PARAMETER = "invalid_job_parameter"
    ORPHAN_JOB_PARAMETER = "orphan_job_parameter"


class EligibilityWarning(ContractModel):
    """A deterministic note about input data the engine could not use."""

    code: WarningCode
    message: NonEmptyStr
    constraint_id: str | None = None
    requirement_id: str | None = None

    def sort_key(self) -> tuple[str, str, str, str]:
        return (
            self.code.value,
            self.constraint_id or "",
            self.requirement_id or "",
            self.message,
        )


class RuleOutcome(ContractModel):
    """What one rule concluded, with the evidence on both sides."""

    rule_id: NonEmptyStr
    status: RuleStatus
    candidate_evidence_ids: list[NonEmptyStr]
    job_evidence_ids: list[NonEmptyStr]
    reason: NonEmptyStr
    requirement_id: str | None = None
    unknown_cause: UnknownCause | None = None
    missing_field_paths: list[CandidateFieldPath] = []
    rule_version: NonEmptyStr

    @model_validator(mode="after")
    def validate_unknown_fields(self) -> "RuleOutcome":
        """A cause belongs to UNKNOWN only; missing paths to CANDIDATE_MISSING only."""

        if (self.status is RuleStatus.UNKNOWN) != (self.unknown_cause is not None):
            raise ValueError("unknown_cause is required for, and only for, UNKNOWN")

        askable = self.unknown_cause is UnknownCause.CANDIDATE_MISSING
        if askable != bool(self.missing_field_paths):
            raise ValueError(
                "missing_field_paths is required for, and only for, "
                "unknown_cause=candidate_missing"
            )

        if len(set(self.missing_field_paths)) != len(self.missing_field_paths):
            raise ValueError("missing_field_paths must not repeat")

        return self


def aggregate_status(outcomes: Iterable[RuleOutcome]) -> EligibilityStatus:
    """CONFLICT beats UNKNOWN beats everything else.

    No score or fit can soften a conflict, and not knowing is never the same
    as being eligible.
    """

    statuses = {outcome.status for outcome in outcomes}
    if RuleStatus.CONFLICT in statuses:
        return EligibilityStatus.INELIGIBLE
    if RuleStatus.UNKNOWN in statuses:
        return EligibilityStatus.UNCERTAIN
    return EligibilityStatus.ELIGIBLE


def collect_missing_field_paths(outcomes: Iterable[RuleOutcome]) -> list[str]:
    """Sorted, de-duplicated union of the askable candidate paths."""

    return sorted({path for outcome in outcomes for path in outcome.missing_field_paths})


class EligibilityResult(ContractModel):
    """Eligibility of one job for one candidate, with every rule's outcome."""

    schema_version: Literal["eligibility-0.1-internal"] = ELIGIBILITY_SCHEMA_VERSION
    candidate_id: NonEmptyStr
    job_id: NonEmptyStr
    catalogue_version: NonEmptyStr
    parameter_layer_version: str | None = None
    status: EligibilityStatus
    outcomes: list[RuleOutcome]
    missing_field_paths: list[CandidateFieldPath]
    warnings: list[EligibilityWarning]

    @model_validator(mode="after")
    def validate_derived_fields(self) -> "EligibilityResult":
        """Status and missing paths are derived; they may not disagree."""

        if self.status is not aggregate_status(self.outcomes):
            raise ValueError("status does not match the aggregated outcomes")

        if self.missing_field_paths != collect_missing_field_paths(self.outcomes):
            raise ValueError(
                "missing_field_paths must be the sorted union of outcome paths"
            )

        return self
