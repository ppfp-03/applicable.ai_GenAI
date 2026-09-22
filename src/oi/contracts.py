"""Shared data contracts for the candidate intelligence pipeline.

These models are the common vocabulary between PDF extraction, model-based
extraction, the candidate profile, and the UI layer. They carry data only:
no validation rules, no business logic.

The file holds two related vocabularies, in this order:

Ingestion
    What a document says: SourceDocument, EvidenceRef, ExtractionReceipt,
    CandidateProfile. Produced by `oi.io` and `oi.intelligence.extraction`.
Decision
    What we conclude and show: Source, Evidence, Requirement, Opportunity,
    Question, Fact, Delta. Produced by the rules and ranking layers, consumed
    by the UI. These mirror the contracts in design-system/40-build-spec.md.

They stay distinct because they answer different questions, and a fact must
survive the trip from one to the other without losing its source.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """A raw input document (e.g. a CV) and its extracted text.

    Provenance is recorded in two independent fields:

    source_ref
        Where the document came from -- its origin (e.g. "uploaded_pdf").
    extraction_method
        How the text was obtained from it (e.g. "native_pdf", "ocr").

    Keeping these separate lets the same origin be read by different means:
    an uploaded PDF may be parsed natively or, when it is a scan, via OCR.
    """

    document_id: str
    kind: str
    text: str
    content_hash: Optional[str] = None
    source_ref: Optional[str] = None
    extraction_method: str


class EvidenceRef(BaseModel):
    """A quote from a source document backing one field of a profile."""

    evidence_id: str
    document_id: str
    quote: str
    field_path: str


class ExtractionReceipt(BaseModel):
    """Provenance of an extraction run: how and by what it was produced."""

    mode: str
    provider: str
    model_id: Optional[str] = None
    produced_at: Optional[str] = None


class CandidateProfile(BaseModel):
    """Structured view of a candidate, with its supporting evidence."""

    candidate_id: str
    name: Optional[str] = None
    skills: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    languages: list[str] = []
    evidence: list[EvidenceRef] = []
    extraction: Optional[ExtractionReceipt] = None


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
