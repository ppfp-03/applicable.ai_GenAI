"""Internal RuleCatalogue v0.1: the closed list of hard constraints.

This is an implementation catalogue, not a frozen shared contract. It names
each supported constraint, the candidate answer keys that feed it, the kind of
job-side parameters it needs and its rule-level settings. The rule logic
itself lives in `rules/`; this file only describes it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from oi.contracts import (
    CHOICE_ANSWER_TYPES,
    AnswerType,
    ContractModel,
    NonEmptyStr,
    validate_candidate_field_path,
)

DEFAULT_CATALOGUE_PATH = (
    Path(__file__).resolve().parents[4] / "config" / "eligibility" / "rule_catalogue.json"
)

# Closed vocabularies shared by answer keys and job parameters.
DEGREE_LEVELS = ("bachelor", "master", "phd")
DEGREE_STATUSES = ("completed", "in_progress")
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
LANGUAGE_LEVELS = CEFR_LEVELS + ("native",)
STUDENT_STATUSES = ("enrolled_student", "recent_graduate", "neither")
IN_PROGRESS_POLICIES = ("counts", "does_not_count", "undecided")

#: Rule-level settings each constraint accepts, with their allowed values.
ALLOWED_SETTINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "HC_DEGREE_LEVEL": {"in_progress_policy": IN_PROGRESS_POLICIES},
}

Trigger = Literal["job_location", "requirement"]


class AnswerKeySpec(ContractModel):
    """One candidate answer key a constraint may read."""

    answer_key: NonEmptyStr
    answer_type: AnswerType
    allowed_values: list[NonEmptyStr] | None = None
    description: NonEmptyStr
    #: Decision that approved the key, e.g. "D-040"; None while pending.
    approval_ref: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_allowed_values(self) -> "AnswerKeySpec":
        """Choice keys list their values; other types must not."""

        is_choice = self.answer_type in CHOICE_ANSWER_TYPES
        if is_choice and not self.allowed_values:
            raise ValueError(f"{self.answer_key}: choice keys need allowed_values")
        if not is_choice and self.allowed_values is not None:
            raise ValueError(f"{self.answer_key}: only choice keys take allowed_values")
        if self.allowed_values and len(set(self.allowed_values)) != len(
            self.allowed_values
        ):
            raise ValueError(f"{self.answer_key}: allowed_values must not repeat")
        return self


class ConstraintSpec(ContractModel):
    """Metadata for one supported hard constraint."""

    constraint_id: str = Field(pattern=r"^HC_[A-Z_]+$")
    label: NonEmptyStr
    hard_only_when: NonEmptyStr
    trigger: Trigger
    answer_keys: list[AnswerKeySpec] = []
    #: The JobParameters `kind` this constraint reads, if any.
    parameter_kind: NonEmptyStr | None = None
    settings: dict[NonEmptyStr, NonEmptyStr] = {}
    rule_version: NonEmptyStr

    @model_validator(mode="after")
    def validate_spec(self) -> "ConstraintSpec":
        """Answer keys are unique, paths are approved and settings are known."""

        keys = [spec.answer_key for spec in self.answer_keys]
        if len(set(keys)) != len(keys):
            raise ValueError(f"{self.constraint_id}: answer keys must be unique")

        for key in keys:
            validate_candidate_field_path(self.field_path(key))

        allowed = ALLOWED_SETTINGS.get(self.constraint_id, {})
        for name, value in self.settings.items():
            if name not in allowed:
                raise ValueError(f"{self.constraint_id}: unknown setting '{name}'")
            if value not in allowed[name]:
                raise ValueError(
                    f"{self.constraint_id}: setting '{name}' must be one of "
                    f"{list(allowed[name])}, got '{value}'"
                )
        return self

    def answer_key(self, key: str) -> AnswerKeySpec | None:
        """The spec for `key`, or None if this constraint does not read it."""

        return next((spec for spec in self.answer_keys if spec.answer_key == key), None)

    def field_path(self, key: str) -> str:
        """The shared candidate path for one of this constraint's answer keys."""

        return f"eligibility_answers.{self.constraint_id}.{key}"


class RuleCatalogue(ContractModel):
    """The closed, ordered set of constraints the engine evaluates."""

    catalogue_version: Literal["0.1-internal"]
    contract_status: Literal["internal-not-frozen"]
    constraints: list[ConstraintSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "RuleCatalogue":
        ids = self.constraint_ids
        if len(set(ids)) != len(ids):
            raise ValueError("constraint IDs must be unique")
        return self

    @property
    def constraint_ids(self) -> list[str]:
        """Constraint IDs in evaluation and display order."""

        return [spec.constraint_id for spec in self.constraints]

    def get(self, constraint_id: str) -> ConstraintSpec | None:
        """The spec for `constraint_id`, or None when it is unsupported."""

        return next(
            (spec for spec in self.constraints if spec.constraint_id == constraint_id),
            None,
        )


def load_rule_catalogue(path: Path = DEFAULT_CATALOGUE_PATH) -> RuleCatalogue:
    """Load and validate the internal rule catalogue.

    Raises:
        OSError: If the file cannot be read.
        pydantic.ValidationError: If the catalogue is malformed.
    """

    return RuleCatalogue.model_validate(json.loads(path.read_text(encoding="utf-8")))
