"""Shared serializable data contracts for Applicable.ai.

These models validate data shape and types only.
Business rules such as eligibility and ranking live elsewhere.

The file holds two vocabularies. The ingestion and job contracts come first;
the decision vocabulary at the end (Source, Evidence, Requirement, Opportunity,
Question, Fact, Delta) is what the rules and ranking layers produce for the UI,
mirroring design-system/40-build-spec.md.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    Strict,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


CONTRACT_VERSION = "0.2.0-draft"



class ContractModel(BaseModel):
    """Base class for all shared cross-group contracts."""

    model_config = ConfigDict(extra="forbid")


class DocumentKind(str, Enum):
    """Supported source-document categories."""

    CV = "cv"
    JOB = "job"
    QUESTIONNAIRE = "questionnaire"
    ATS_METADATA = "ats_metadata"


class ExtractionMode(str, Enum):
    """How a semantic extraction result was produced."""

    LIVE = "live"
    CACHE = "cache"
    FIXTURE = "fixture"


class SourceDocument(ContractModel):
    """Raw source text plus stable provenance."""

    document_id: str = Field(min_length=1)
    kind: DocumentKind
    text: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)


class EvidenceRef(ContractModel):
    """A source quote supporting one structured field."""

    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    field_path: str = Field(min_length=1)


class SupportedText(ContractModel):
    """Text value together with the evidence that supports it."""

    value: str = Field(min_length=1)
    evidence_ids: list[str]


class ExtractionReceipt(ContractModel):
    """Provenance and reproducibility metadata for an extraction."""

    mode: ExtractionMode
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    input_hash: str = Field(min_length=1)
    produced_at: AwareDatetime
    latency_ms: int | None = Field(default=None, ge=0)

    @field_validator("produced_at")
    @classmethod
    def normalize_produced_at_to_utc(cls, value: datetime) -> datetime:
        """Serialize extraction timestamps consistently in UTC."""

        return value.astimezone(timezone.utc)


class RequirementClassification(str, Enum):
    """Semantic role of a requirement extracted from a job."""

    HARD_CONSTRAINT = "hard_constraint"
    FIT = "fit"
    INFORMATIONAL = "informational"


class RequirementModality(str, Enum):
    """How strongly the source states a requirement."""

    MANDATORY = "mandatory"
    PREFERRED = "preferred"
    OPTIONAL = "optional"
    UNSPECIFIED = "unspecified"


class ActiveState(str, Enum):
    """Observed availability state of a job."""

    ACTIVE = "active"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class DiscoveryKind(str, Enum):
    """How a job entered the dataset."""

    INITIAL_SNAPSHOT = "initial_snapshot"
    LATER_OBSERVATION = "later_observation"
    SYNTHETIC_SCENARIO = "synthetic_scenario"


class RequirementFact(ContractModel):
    """Structured intelligence-layer interpretation of a job requirement."""

    requirement_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    classification: RequirementClassification
    modality: RequirementModality
    constraint_id: str | None = Field(default=None, min_length=1)
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_constraint_link(self) -> "RequirementFact":
        """Hard constraints must map to a rule-catalogue ID only."""

        if (
            self.classification == RequirementClassification.HARD_CONSTRAINT
            and self.constraint_id is None
        ):
            raise ValueError("hard_constraint requirements need constraint_id")

        if (
            self.classification != RequirementClassification.HARD_CONSTRAINT
            and self.constraint_id is not None
        ):
            raise ValueError("constraint_id is only valid for hard_constraint")

        return self


class JobFacts(ContractModel):
    """Semantic facts extracted from a job description."""

    skills: list[SupportedText]
    experience: list[SupportedText]
    education: list[SupportedText]
    role_family: SupportedText | None = None
    requirements: list[RequirementFact]


class JobLocation(ContractModel):
    """Source-supported job location."""

    country_code: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    evidence_ids: list[str]


class JobRecord(ContractModel):
    """Normalized job shared between data/input and intelligence layers."""

    schema_version: str = Field(pattern=r"^0\.2\.0-draft$")
    job_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)

    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)

    description: SourceDocument
    source_documents: list[SourceDocument]
    locations: list[JobLocation]

    source_published_at: AwareDatetime | None = None
    source_updated_at: AwareDatetime | None = None
    deadline_at: AwareDatetime | None = None

    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime

    active_state: ActiveState
    discovery_kind: DiscoveryKind

    facts: JobFacts | None = None
    evidence: list[EvidenceRef]
    extraction: ExtractionReceipt | None = None

    @field_validator(
        "source_published_at",
        "source_updated_at",
        "deadline_at",
        "first_seen_at",
        "last_seen_at",
    )
    @classmethod
    def normalize_job_timestamps_to_utc(
        cls, value: datetime | None
    ) -> datetime | None:
        """Serialize source and observation timestamps consistently in UTC."""

        if value is None:
            return None
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_job_record(self) -> "JobRecord":
        """Validate cross-field invariants of the shared job contract."""

        expected_job_id = f"{self.source}:{self.source_job_id}"
        if self.job_id != expected_job_id:
            raise ValueError(
                f"job_id must be namespaced as '{expected_job_id}'"
            )

        if self.description.kind != DocumentKind.JOB:
            raise ValueError("description must have kind='job'")

        if any(
            document.document_id == self.description.document_id
            for document in self.source_documents
        ):
            raise ValueError(
                "description must not be duplicated in source_documents"
            )

        if self.last_seen_at < self.first_seen_at:
            raise ValueError("last_seen_at cannot be before first_seen_at")

        return self


ISO_3166_1_ALPHA_2: frozenset[str] = frozenset(
    """
    AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ
    BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ
    CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ
    DE DJ DK DM DO DZ
    EC EE EG EH ER ES ET
    FI FJ FK FM FO FR
    GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY
    HK HM HN HR HT HU
    ID IE IL IM IN IO IQ IR IS IT
    JE JM JO JP
    KE KG KH KI KM KN KP KR KW KY KZ
    LA LB LC LI LK LR LS LT LU LV LY
    MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ
    NA NC NE NF NG NI NL NO NP NR NU NZ
    OM
    PA PE PF PG PH PK PL PM PN PR PS PT PW PY
    QA
    RE RO RS RU RW
    SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ
    TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ
    UA UG UM US UY UZ
    VA VC VE VG VI VN VU
    WF WS
    YE YT
    ZA ZM ZW
    """.split()
)
"""Officially assigned ISO 3166-1 alpha-2 codes, kept local to avoid a new dependency."""


def validate_country_code(value: str) -> str:
    """Accept only uppercase officially assigned ISO 3166-1 alpha-2 codes."""

    if value not in ISO_3166_1_ALPHA_2:
        raise ValueError(
            f"'{value}' is not an uppercase ISO 3166-1 alpha-2 country code"
        )
    return value


def reject_duplicate_country_codes(values: list[str]) -> list[str]:
    """Country-code collections describe a set, so duplicates are a defect."""

    if len(set(values)) != len(values):
        raise ValueError("duplicate country codes are not allowed")
    return values


NonEmptyStr = Annotated[str, Field(min_length=1)]
CountryCode = Annotated[str, AfterValidator(validate_country_code)]
UniqueCountryCodes = Annotated[
    list[CountryCode], AfterValidator(reject_duplicate_country_codes)
]


class AnswerState(str, Enum):
    """Whether a candidate answer carries a value."""

    KNOWN = "known"
    UNKNOWN = "unknown"


class AnswerType(str, Enum):
    """Logical value type of a candidate answer."""

    BOOLEAN = "boolean"
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    TEXT = "text"
    DATE = "date"
    INTEGER = "integer"


class ClarificationPriority(str, Enum):
    """How urgently a clarification should be asked."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


CHOICE_ANSWER_TYPES = frozenset({AnswerType.SINGLE_CHOICE, AnswerType.MULTI_CHOICE})


def _is_exact_str_list(value: Any) -> bool:
    return type(value) is list and all(type(item) is str for item in value)


StrictDate = Annotated[date, Strict()]
StrictStrList = Annotated[list[StrictStr], Strict()]

EligibilityAnswerValue = (
    StrictBool | StrictInt | StrictStr | StrictDate | StrictStrList | None
)
"""Closed value union for candidate answers.

Every member is strict, so Pydantic coerces across no boundary here: not
boolean/integer, not string/date, and not tuple or set into list. A `date`
value therefore has to arrive as a real `date`, which only
`parse_iso_date_value` produces, and only for a `date` answer.
"""


ANSWER_VALUE_CHECKS = {
    # `type(...) is` keeps bool out of int and datetime out of date.
    AnswerType.BOOLEAN: lambda value: type(value) is bool,
    AnswerType.SINGLE_CHOICE: lambda value: type(value) is str,
    AnswerType.MULTI_CHOICE: _is_exact_str_list,
    AnswerType.TEXT: lambda value: type(value) is str,
    AnswerType.DATE: lambda value: type(value) is date,
    AnswerType.INTEGER: lambda value: type(value) is int,
}


class CandidatePreferences(ContractModel):
    """Declared candidate preferences and the optional country perimeter."""

    allowed_country_codes: UniqueCountryCodes | None = None
    preferred_country_codes: UniqueCountryCodes
    preferred_role_families: list[NonEmptyStr]
    preferred_industries: list[NonEmptyStr]

    @model_validator(mode="after")
    def validate_country_perimeter(self) -> "CandidatePreferences":
        """A declared perimeter must be usable and must contain the preferences."""

        if self.allowed_country_codes is None:
            return self

        if not self.allowed_country_codes:
            raise ValueError(
                "allowed_country_codes must be non-empty when declared; "
                "use null for no declared restriction"
            )

        allowed = set(self.allowed_country_codes)
        outside = sorted(
            code for code in self.preferred_country_codes if code not in allowed
        )
        if outside:
            raise ValueError(
                f"preferred countries outside allowed_country_codes: {outside}"
            )

        return self


class WorkAuthorizationDeclaration(ContractModel):
    """Candidate-declared work-authorization facts for one country."""

    country_code: CountryCode
    authorized_to_work: bool | None = None
    requires_sponsorship: bool | None = None
    evidence_ids: list[NonEmptyStr]


class UserDeclarations(ContractModel):
    """Candidate-declared citizenship and work-authorization facts."""

    additional_citizenships: UniqueCountryCodes
    work_authorizations: list[WorkAuthorizationDeclaration]

    @model_validator(mode="after")
    def validate_one_declaration_per_country(self) -> "UserDeclarations":
        """Two declarations for one country would make the fact ambiguous."""

        codes = [
            declaration.country_code for declaration in self.work_authorizations
        ]
        if len(set(codes)) != len(codes):
            raise ValueError(
                "work_authorizations must hold at most one declaration per country"
            )

        return self


ISO_CALENDAR_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
"""JSON dates are exactly YYYY-MM-DD; ordinal and week forms are not accepted."""


class EligibilityAnswer(ContractModel):
    """One structured candidate answer feeding the deterministic rule engine."""

    constraint_id: NonEmptyStr
    answer_key: NonEmptyStr
    state: AnswerState
    answer_type: AnswerType
    value: EligibilityAnswerValue = Field(default=None, union_mode="left_to_right")
    evidence_ids: list[NonEmptyStr]
    source_document_id: NonEmptyStr

    @model_validator(mode="before")
    @classmethod
    def parse_iso_date_value(cls, data: Any) -> Any:
        """JSON carries dates as ISO strings; the model holds `date`."""

        if not isinstance(data, dict):
            return data

        answer_type = data.get("answer_type")
        if isinstance(answer_type, AnswerType):
            answer_type = answer_type.value
        if answer_type != AnswerType.DATE.value:
            return data

        value = data.get("value")
        if not isinstance(value, str):
            return data

        # `date.fromisoformat` alone would also accept ordinal ("20270715")
        # and week ("2027-W28-4") forms, so the shape is pinned first and the
        # calendar itself is validated second.
        if not ISO_CALENDAR_DATE_PATTERN.match(value):
            raise ValueError("date answers use ISO 'YYYY-MM-DD' values")

        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                "date answers use ISO 'YYYY-MM-DD' values"
            ) from error

        return {**data, "value": parsed}

    @model_validator(mode="after")
    def validate_answer_value(self) -> "EligibilityAnswer":
        """State and answer type together close the accepted value shape."""

        if self.state is AnswerState.UNKNOWN:
            if self.value is not None:
                raise ValueError("unknown answers must not carry a value")
            return self

        if self.value is None:
            raise ValueError("known answers must carry a non-null value")

        if not ANSWER_VALUE_CHECKS[self.answer_type](self.value):
            raise ValueError(
                f"{self.answer_type.value} answers reject value "
                f"of type '{type(self.value).__name__}'"
            )

        return self


class CandidateProvenance(ContractModel):
    """Document, evidence and extraction registries backing a candidate profile."""

    questionnaire_document_ids: list[NonEmptyStr]
    clarification_document_ids: list[NonEmptyStr]
    documents: dict[NonEmptyStr, SourceDocument]
    evidence: list[EvidenceRef]
    extraction: ExtractionReceipt

    @model_validator(mode="after")
    def validate_registries(self) -> "CandidateProvenance":
        """Registry keys and every internal reference must resolve."""

        for document_id, document in self.documents.items():
            if document.document_id != document_id:
                raise ValueError(
                    f"document registry key '{document_id}' does not match "
                    f"document_id '{document.document_id}'"
                )

        # The registry is keyed by evidence_id downstream, so a repeated ID
        # would make reference resolution depend on list order.
        evidence_ids = [reference.evidence_id for reference in self.evidence]
        if len(set(evidence_ids)) != len(evidence_ids):
            duplicates = sorted(
                {
                    evidence_id
                    for evidence_id in evidence_ids
                    if evidence_ids.count(evidence_id) > 1
                }
            )
            raise ValueError(
                f"evidence_id must be unique in provenance.evidence: {duplicates}"
            )

        for reference in self.evidence:
            if reference.document_id not in self.documents:
                raise ValueError(
                    f"evidence '{reference.evidence_id}' references unknown "
                    f"document '{reference.document_id}'"
                )

        sourced_ids = (
            ("questionnaire", self.questionnaire_document_ids),
            ("clarification", self.clarification_document_ids),
        )
        for label, document_ids in sourced_ids:
            for document_id in document_ids:
                document = self.documents.get(document_id)
                if document is None:
                    raise ValueError(
                        f"{label} document '{document_id}' is not registered "
                        "in documents"
                    )
                if document.kind is not DocumentKind.QUESTIONNAIRE:
                    raise ValueError(
                        f"{label} document '{document_id}' must have "
                        "kind='questionnaire'"
                    )

        return self


class CandidateProfile(ContractModel):
    """Normalized candidate shared between data/input and intelligence layers."""

    schema_version: str = Field(pattern=r"^0\.2\.0-draft$")
    candidate_id: NonEmptyStr
    cv_document_id: NonEmptyStr

    skills: list[SupportedText]
    education: list[SupportedText]
    experience: list[SupportedText]

    preferences: CandidatePreferences
    declarations: UserDeclarations
    eligibility_answers: dict[NonEmptyStr, list[EligibilityAnswer]]
    provenance: CandidateProvenance

    @model_validator(mode="after")
    def validate_candidate_references(self) -> "CandidateProfile":
        """Every candidate-side reference must resolve inside provenance."""

        documents = self.provenance.documents
        evidence_by_id = {
            reference.evidence_id: reference for reference in self.provenance.evidence
        }

        cv_document = documents.get(self.cv_document_id)
        if cv_document is None:
            raise ValueError(
                f"cv_document_id '{self.cv_document_id}' is not registered "
                "in provenance.documents"
            )
        if cv_document.kind is not DocumentKind.CV:
            raise ValueError(
                f"cv_document_id '{self.cv_document_id}' must have kind='cv'"
            )

        def require_evidence(evidence_ids: list[str], location: str) -> None:
            for evidence_id in evidence_ids:
                if evidence_id not in evidence_by_id:
                    raise ValueError(
                        f"{location} references unknown evidence '{evidence_id}'"
                    )

        for field_name in ("skills", "education", "experience"):
            for index, supported in enumerate(getattr(self, field_name)):
                require_evidence(supported.evidence_ids, f"{field_name}[{index}]")

        for declaration in self.declarations.work_authorizations:
            require_evidence(
                declaration.evidence_ids,
                f"declarations.work_authorizations.{declaration.country_code}",
            )

        for constraint_id, answers in self.eligibility_answers.items():
            for answer in answers:
                if answer.constraint_id != constraint_id:
                    raise ValueError(
                        f"eligibility_answers key '{constraint_id}' does not match "
                        f"contained constraint_id '{answer.constraint_id}'"
                    )

                location = f"eligibility_answers.{constraint_id}.{answer.answer_key}"
                require_evidence(answer.evidence_ids, location)

                if answer.source_document_id not in documents:
                    raise ValueError(
                        f"{location} references unknown source document "
                        f"'{answer.source_document_id}'"
                    )

                for evidence_id in answer.evidence_ids:
                    if (
                        evidence_by_id[evidence_id].document_id
                        != answer.source_document_id
                    ):
                        raise ValueError(
                            f"{location} evidence '{evidence_id}' must belong to "
                            f"source document '{answer.source_document_id}'"
                        )

        return self


SIMPLE_CANDIDATE_FIELD_PATHS = frozenset(
    {
        "preferences.allowed_country_codes",
        "preferences.preferred_country_codes",
        "preferences.preferred_role_families",
        "preferences.preferred_industries",
        "declarations.additional_citizenships",
    }
)

WORK_AUTHORIZATION_FIELD_PATH_LEAVES = frozenset(
    {"authorized_to_work", "requires_sponsorship"}
)


def eligibility_field_path_constraint_id(field_path: str) -> str | None:
    """Return the constraint component of an eligibility path, else None."""

    tokens = field_path.split(".")
    if len(tokens) == 3 and tokens[0] == "eligibility_answers":
        return tokens[1]
    return None


def validate_candidate_field_path(value: str) -> str:
    """Accept only the approved candidate destination families.

    Eligibility paths are checked for structure only. Whether an answer key
    belongs to a constraint is RuleCatalogue business, not contract shape.
    """

    if value in SIMPLE_CANDIDATE_FIELD_PATHS:
        return value

    tokens = value.split(".")

    if (
        len(tokens) == 4
        and tokens[0] == "declarations"
        and tokens[1] == "work_authorizations"
        and tokens[3] in WORK_AUTHORIZATION_FIELD_PATH_LEAVES
    ):
        validate_country_code(tokens[2])
        return value

    if len(tokens) == 3 and tokens[0] == "eligibility_answers":
        if not tokens[1] or not tokens[2]:
            raise ValueError(
                f"'{value}' needs non-empty constraint and answer-key tokens"
            )
        return value

    raise ValueError(f"'{value}' is not an approved candidate field path")


CandidateFieldPath = Annotated[str, AfterValidator(validate_candidate_field_path)]


class ClarificationRequest(ContractModel):
    """A targeted question asked when a candidate fact is missing."""

    question_id: NonEmptyStr
    field_path: CandidateFieldPath | None = None
    constraint_id: NonEmptyStr | None = None
    question: NonEmptyStr
    answer_type: AnswerType
    allowed_choices: list[NonEmptyStr] | None = None
    reason: NonEmptyStr
    job_ids: list[NonEmptyStr]
    evidence_ids: list[NonEmptyStr]
    priority: ClarificationPriority

    @model_validator(mode="after")
    def validate_clarification(self) -> "ClarificationRequest":
        """A clarification needs a destination and a coherent answer shape."""

        if self.field_path is None and self.constraint_id is None:
            raise ValueError(
                "clarification needs at least one of field_path or constraint_id"
            )

        if self.answer_type in CHOICE_ANSWER_TYPES:
            if not self.allowed_choices:
                raise ValueError(
                    f"{self.answer_type.value} answers need non-empty allowed_choices"
                )
        elif self.allowed_choices is not None:
            raise ValueError(
                "allowed_choices is only valid for single_choice and multi_choice"
            )

        if self.field_path is not None and self.constraint_id is not None:
            path_constraint_id = eligibility_field_path_constraint_id(self.field_path)
            if (
                path_constraint_id is not None
                and path_constraint_id != self.constraint_id
            ):
                raise ValueError(
                    f"field_path constraint '{path_constraint_id}' conflicts with "
                    f"constraint_id '{self.constraint_id}'"
                )

        return self


SNAPSHOT_CONTRACT_VERSION = "0.2.1-draft"
"""Version of the snapshot envelope wrapped around frozen 0.2.0-draft payloads."""


class SourceManifestEntry(ContractModel):
    """Provenance of one source contributing to a snapshot."""

    source: NonEmptyStr
    source_ref: NonEmptyStr
    retrieved_at: AwareDatetime
    record_count: StrictInt = Field(ge=0)
    redistribution_allowed: StrictBool | None = None

    @field_validator("retrieved_at")
    @classmethod
    def normalize_retrieved_at_to_utc(cls, value: datetime) -> datetime:
        """Serialize retrieval timestamps consistently in UTC."""

        return value.astimezone(timezone.utc)


class QuarantineSummary(ContractModel):
    """How many records one source-quality reason removed from a snapshot.

    Summary metadata only: the quarantined payloads themselves stay out of
    the shared snapshot.
    """

    reason: NonEmptyStr
    count: StrictInt = Field(gt=0)


class JobSnapshot(ContractModel):
    """One reproducible job snapshot shared between data/input and intelligence.

    `documents` is the canonical registry: every document a job embeds or
    references by evidence must also appear here under its own ID.
    """

    schema_version: str = Field(pattern=r"^0\.2\.1-draft$")
    snapshot_id: NonEmptyStr
    created_at: AwareDatetime

    jobs: list[JobRecord]
    documents: dict[NonEmptyStr, SourceDocument]
    source_manifest: list[SourceManifestEntry]
    quarantine: list[QuarantineSummary]

    @field_validator("created_at")
    @classmethod
    def normalize_created_at_to_utc(cls, value: datetime) -> datetime:
        """Serialize snapshot creation timestamps consistently in UTC."""

        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_snapshot_references(self) -> "JobSnapshot":
        """Registry keys and every job-side document reference must resolve."""

        for document_id, document in self.documents.items():
            if document.document_id != document_id:
                raise ValueError(
                    f"document registry key '{document_id}' does not match "
                    f"document_id '{document.document_id}'"
                )

        for job in self.jobs:
            embedded = [("description", job.description)]
            embedded.extend(
                (f"source_documents[{index}]", document)
                for index, document in enumerate(job.source_documents)
            )

            for location, document in embedded:
                registered = self.documents.get(document.document_id)
                if registered is None:
                    raise ValueError(
                        f"job '{job.job_id}' {location} document "
                        f"'{document.document_id}' is not registered in documents"
                    )
                if registered != document:
                    raise ValueError(
                        f"job '{job.job_id}' {location} document "
                        f"'{document.document_id}' differs from the registered copy"
                    )

            for reference in job.evidence:
                if reference.document_id not in self.documents:
                    raise ValueError(
                        f"job '{job.job_id}' evidence '{reference.evidence_id}' "
                        f"references unknown document '{reference.document_id}'"
                    )

        return self


# --------------------------------------------------------------------------
# Decision vocabulary
#
# From here on: what the product concludes and shows. See the module docstring
# for why these sit beside the ingestion models rather than replacing them.
# --------------------------------------------------------------------------

#: The three decisions, plus Closed for a passed deadline. Never a fifth.
Verdict = Literal["apply", "clarify", "skip", "closed"]

#: Whether one requirement is satisfied, unknown, or blocking.
ReqStatus = Literal["met", "confirm", "conflict"]

#: Where a claim comes from. RULE is deterministic policy, never the model.
SourceKind = Literal["CV", "JOB", "YOU", "RULE"]


class Source(BaseModel):
    """Where a single claim came from.

    `where` is a human-readable locator shown in the UI, e.g. "p.1 -
    Experience", "Requirements, l.2", or for RULE the rule that fired:
    "CH - EU/EFTA - contract >= 12 months".
    """

    kind: SourceKind
    where: str


class Evidence(BaseModel):
    """A verbatim quote backing a claim, with the span to highlight.

    `text` is quoted exactly as the source wrote it -- never paraphrased,
    because the product's promise is that the user can check it. `highlight`
    is a (start, end) character span within `text`; None means show the quote
    without a highlighter mark.
    """

    text: str
    highlight: Optional[tuple[int, int]] = None
    source: Source


class Requirement(BaseModel):
    """One thing a posting asks for, and whether the candidate meets it.

    `evidence` is None when the CV simply does not say. That is a legitimate
    answer -- it renders as "Not stated in your CV" -- and is never filled in
    with a guess. When `status` is "confirm", `question_id` points at the
    question that would settle it.
    """

    ask: str
    kind: Literal["must", "nice"]
    status: ReqStatus
    evidence: Optional[Evidence] = None
    job_source: Source
    question_id: Optional[str] = None


class EligibilityCheck(BaseModel):
    """One hard constraint, decided by `core.rules` and never by a model.

    These are the checks that can stop an application outright: the right to
    work, the graduation window, the location. They are kept apart from
    `Requirement` -- and rendered apart -- because the two answer different
    questions. A requirement is how well you fit; an eligibility check is
    whether you are allowed to apply at all, and no weighting can soften it.

    `constraint_id` matches an id in `config/hard_constraints.json`, so an
    outcome on screen can be traced to the constraint that produced it.
    """

    constraint_id: str
    label: str
    status: ReqStatus
    explanation: str
    source: Source


class PostingWarning(BaseModel):
    """Something the user should know that is not a gap in their profile.

    Gaps are about the candidate; warnings are about the posting or about the
    limits of what we could read. Keeping them separate stops "we could not
    parse the salary section" from looking like a shortcoming of the person.
    """

    text: str
    kind: Literal["posting", "reading", "deadline"] = "posting"


class Opportunity(BaseModel):
    """One posting, judged.

    `verdict` and `priority` are computed by the rules and ranking layers.
    Nothing a model returns may set them: the model explains a decision, it
    does not make one.
    """

    id: str
    title: str
    company: str
    city: str
    #: ISO 3166-1 alpha-2 of where the role is based, for the rules layer.
    country: str = ""
    contract: str
    contract_months: Optional[int] = None
    deadline_days: int
    #: Days since we first saw the posting. None where the source gives no
    #: date: freshness is then left out rather than guessed.
    posted_days_ago: Optional[int] = None
    verdict: Verdict
    why: Evidence
    requirements: list[Requirement] = []
    priority: int
    factors: dict[str, float] = {}
    provisional: bool = False
    #: Hard constraints, decided by rules. Empty until they have been run.
    eligibility: list[EligibilityCheck] = []
    #: Caveats about the posting, kept apart from the candidate's gaps.
    warnings: list[PostingWarning] = []
    #: (task, hours) pairs shown in the "Before you apply" rail.
    before_you_apply: list[tuple[str, float]] = Field(default_factory=list)

    @property
    def eligibility_status(self) -> ReqStatus:
        """The strictest outcome among the hard constraints.

        One conflict blocks; anything unconfirmed asks; otherwise eligible.
        With no checks run yet the answer is "confirm", because not having
        looked is not the same as having found nothing wrong.
        """
        if not self.eligibility:
            return "confirm"
        if any(c.status == "conflict" for c in self.eligibility):
            return "conflict"
        if any(c.status == "confirm" for c in self.eligibility):
            return "confirm"
        return "met"


class Question(BaseModel):
    """A missing fact, asked only when a real posting depends on it.

    `unlocks` lists the opportunity ids the answer would re-evaluate, and
    `impact` states the effect in the user's terms ("could move #3 to #2"),
    so the cost of answering is visible before they answer.
    """

    id: str
    text: str
    reason: Evidence
    #: Always includes an explicit "Not sure" -- declining is a valid answer.
    options: list[str]
    #: Which answers settle the requirement and which block it. An answer not
    #: listed here leaves it open: recording that we asked is not the same as
    #: inventing a fact, and "Not sure" is a real answer.
    resolution: dict[str, list[str]] = {}
    unlocks: list[str] = []
    impact: str


class Fact(BaseModel):
    """Something the user told us, kept and reused with its date."""

    key: str
    value: str
    date: str


class Delta(BaseModel):
    """What one answer changed, as before/after pairs.

    Each tuple is (verdict, priority, rank). `changes` carries the readable
    lines shown to the user, e.g. ("Requirement 'German B2'", "To confirm ->
    Met").
    """

    opportunity_id: str
    before: tuple[Verdict, int, int]
    after: tuple[Verdict, int, int]
    changes: list[tuple[str, str]] = []
