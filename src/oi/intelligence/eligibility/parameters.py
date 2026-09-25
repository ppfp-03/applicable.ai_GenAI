"""Temporary job-side parameter layer.

The frozen `RequirementFact` carries a hard constraint's text, modality and
constraint ID, but not the values a rule compares against (a window's dates, a
language's level). Rather than parse prose, those values sit here, beside the
JobRecord, keyed by (job_id, requirement_id). Entries are human-curated for now;
`origin` leaves room for extraction to fill the same shape later.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import Field, Strict, model_validator

from oi.contracts import ContractModel, CountryCode, NonEmptyStr

DEFAULT_PARAMETERS_PATH = (
    Path(__file__).resolve().parents[4] / "config" / "eligibility" / "job_parameters.json"
)

DegreeLevel = Literal["bachelor", "master", "phd"]
CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
StudentStatus = Literal["enrolled_student", "recent_graduate", "neither"]
InProgressPolicy = Literal["counts", "does_not_count", "undecided"]
EmployerSponsorship = Literal["offered", "not_offered", "not_stated"]


class GradWindowParams(ContractModel):
    """Inclusive graduation window."""

    kind: Literal["grad_window"]
    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> "GradWindowParams":
        if self.start > self.end:
            raise ValueError("grad_window start must not be after end")
        return self


class StudentStatusParams(ContractModel):
    """Statuses the programme accepts."""

    kind: Literal["student_status"]
    accepted: list[StudentStatus] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique(self) -> "StudentStatusParams":
        if len(set(self.accepted)) != len(self.accepted):
            raise ValueError("accepted statuses must not repeat")
        return self


class DegreeLevelParams(ContractModel):
    """Minimum degree level, with an optional per-job in-progress policy."""

    kind: Literal["degree_level"]
    min_level: DegreeLevel
    #: Overrides the catalogue default for this job only.
    in_progress_policy: InProgressPolicy | None = None


class FieldOfStudyParams(ContractModel):
    """Accepted fields, and whether "a related field" is also accepted."""

    kind: Literal["field_of_study"]
    accepted: list[NonEmptyStr] = Field(min_length=1)
    related_accepted: bool

    @model_validator(mode="after")
    def validate_unique(self) -> "FieldOfStudyParams":
        if len(set(self.accepted)) != len(self.accepted):
            raise ValueError("accepted fields must not repeat")
        return self


class LanguageParams(ContractModel):
    """One required language (ISO 639-1) at a minimum CEFR level."""

    kind: Literal["language"]
    language: str = Field(pattern=r"^[a-z]{2}$")
    min_level: CefrLevel


class MinExperienceParams(ContractModel):
    """Either a minimum number of months, or one approved boolean answer key."""

    kind: Literal["min_experience"]
    min_months: Annotated[int, Strict()] | None = Field(default=None, ge=1)
    answer_key: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_exactly_one(self) -> "MinExperienceParams":
        if (self.min_months is None) == (self.answer_key is None):
            raise ValueError("set exactly one of min_months and answer_key")
        return self


class WorkAuthParams(ContractModel):
    """Country the authorization is for, and the employer's sponsorship policy."""

    kind: Literal["work_auth"]
    #: None means: use the job's single resolved location country.
    country_code: CountryCode | None = None
    employer_sponsorship: EmployerSponsorship


JobParameters = Annotated[
    Union[
        GradWindowParams,
        StudentStatusParams,
        DegreeLevelParams,
        FieldOfStudyParams,
        LanguageParams,
        MinExperienceParams,
        WorkAuthParams,
    ],
    Field(discriminator="kind"),
]


class JobParameterEntry(ContractModel):
    """Typed rule parameters for one hard-constraint requirement of one job."""

    job_id: NonEmptyStr
    requirement_id: NonEmptyStr
    constraint_id: NonEmptyStr
    parameters: JobParameters
    #: Job evidence the values were read from; must resolve in job.evidence.
    evidence_ids: list[NonEmptyStr] = Field(min_length=1)
    origin: Literal["curated", "extraction"]
    note: str | None = None


class JobParameterSet(ContractModel):
    """All parameter entries, unique per (job_id, requirement_id)."""

    layer_version: Literal["0.1-temporary"]
    entries: list[JobParameterEntry]

    @model_validator(mode="after")
    def validate_unique_keys(self) -> "JobParameterSet":
        keys = [(entry.job_id, entry.requirement_id) for entry in self.entries]
        if len(set(keys)) != len(keys):
            raise ValueError("entries must be unique per (job_id, requirement_id)")
        return self

    def for_job(self, job_id: str) -> list[JobParameterEntry]:
        """Entries for one job, in requirement_id order."""

        return sorted(
            (entry for entry in self.entries if entry.job_id == job_id),
            key=lambda entry: entry.requirement_id,
        )

    def get(self, job_id: str, requirement_id: str) -> JobParameterEntry | None:
        """The entry for one requirement, or None."""

        return next(
            (
                entry
                for entry in self.entries
                if entry.job_id == job_id and entry.requirement_id == requirement_id
            ),
            None,
        )


def load_job_parameters(path: Path = DEFAULT_PARAMETERS_PATH) -> JobParameterSet:
    """Load and validate the job-side parameter layer.

    Raises:
        OSError: If the file cannot be read.
        pydantic.ValidationError: If an entry is malformed.
    """

    return JobParameterSet.model_validate(json.loads(path.read_text(encoding="utf-8")))
