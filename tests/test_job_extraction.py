"""Tests for job requirement extraction: grounding, gates and provenance."""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from oi.contracts import (
    CONTRACT_VERSION,
    ExtractionMode,
    JobRecord,
    RequirementClassification,
    RequirementModality,
)
from oi.intelligence.eligibility import load_rule_catalogue
from oi.intelligence.job_extraction import enrich_jobs, enrich_snapshot
from oi.io.greenhouse_batch import write_snapshot
from oi.io.snapshot import load_snapshot
from oi.providers.model_client import (
    JOB_PROMPT_PATH,
    ExtractedJobFact,
    ExtractedJobFields,
    ExtractedRequirement,
    ExtractionError,
    ModelClient,
    load_job_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "contracts" / "v0.2.0-draft" / "job_record.json"
BATCH01 = ROOT / "data" / "snapshots" / "greenhouse_batch01.json"
BATCH01_ENRICHED = ROOT / "data" / "snapshots" / "greenhouse_batch01_enriched.json"

DESCRIPTION = (
    "Location: Amsterdam, Netherlands\n"
    "You will build and maintain financial models.\n"
    "Requirements:\n"
    "- Bachelor degree in economics, finance or\n"
    "  management\n"
    "- Applicants must hold a valid work permit for the Netherlands.\n"
    "- Fluent Dutch is a plus.\n"
    "- Excellent Excel skills.\n"
    "The internship starts in January 2027.\n"
)

#: Requirement-triggered constraints: the only ids a job requirement may name.
HARD_IDS = {
    spec.constraint_id
    for spec in load_rule_catalogue().constraints
    if spec.trigger == "requirement"
}


def make_job(job_id: str = "42", text: str = DESCRIPTION) -> JobRecord:
    """A not-yet-enriched job built from the shared contract fixture."""
    data = json.loads(FIXTURE.read_text())
    data.update(
        job_id=f"{data['source']}:{job_id}",
        source_job_id=job_id,
        facts=None,
        extraction=None,
        evidence=[e for e in data["evidence"] if e["field_path"] == "locations"],
    )
    data["description"].update(text=text, content_hash=f"hash-{job_id}")
    return JobRecord.model_validate(data)


def blank_description_job() -> JobRecord:
    """A job whose description is whitespace only (no evidence cites it)."""
    job = make_job("2")
    description = job.description.model_copy(update={"text": "   \n"})
    return job.model_copy(update={"description": description, "evidence": []})


def fact(value: str, quote: str) -> ExtractedJobFact:
    return ExtractedJobFact(value=value, quote=quote)


def requirement(
    text: str,
    quote: str,
    classification: str = "fit",
    modality: str = "unspecified",
    constraint_id: str | None = None,
) -> ExtractedRequirement:
    return ExtractedRequirement(
        text=text,
        quote=quote,
        classification=RequirementClassification(classification),
        modality=RequirementModality(modality),
        constraint_id=constraint_id,
    )


def make_fields(**overrides: Any) -> ExtractedJobFields:
    payload: dict[str, Any] = {
        "skills": [fact("Financial modelling", "build and maintain financial models")],
        "experience": [],
        "education": [
            fact(
                "Bachelor degree in economics, finance or management",
                # Joined across the line break, as a model would quote it.
                "Bachelor degree in economics, finance or management",
            )
        ],
        "requirements": [
            requirement(
                "Valid work permit for the Netherlands",
                "Applicants must hold a valid work permit for the Netherlands.",
                "hard_constraint",
                "mandatory",
                "HC_WORK_AUTH",
            ),
            requirement("Fluent Dutch", "Fluent Dutch is a plus.", "fit", "preferred"),
        ],
    }
    payload.update(overrides)
    return ExtractedJobFields(**payload)


class FakeModelClient:
    """A ModelClient that returns canned job fields or raises a canned error."""

    provider_name = "fake"
    model_id = "fake-model-1"

    def __init__(
        self,
        fields: ExtractedJobFields | None = None,
        error: Exception | None = None,
        fail_on_call: int | None = None,
    ) -> None:
        self.fields = fields if fields is not None else make_fields()
        self.error = error
        self.fail_on_call = fail_on_call
        self.calls: list[str] = []

    def extract_candidate_fields(self, document_text: str) -> Any:
        raise AssertionError("job extraction must not extract candidate fields")

    def extract_job_fields(self, description_text: str) -> ExtractedJobFields:
        self.calls.append(description_text)
        if self.error is not None and self.fail_on_call in (None, len(self.calls)):
            raise self.error
        return self.fields


def enrich_one(fields: ExtractedJobFields, job: JobRecord | None = None) -> JobRecord:
    [enriched] = enrich_jobs([job or make_job()], FakeModelClient(fields))
    return enriched


def evidence_by_id(job: JobRecord) -> dict[str, Any]:
    return {ref.evidence_id: ref for ref in job.evidence}


# --- successful extraction ------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    assert isinstance(FakeModelClient(), ModelClient)


def test_successful_extraction_enriches_job() -> None:
    job = make_job()
    client = FakeModelClient()

    [enriched] = enrich_jobs([job], client)

    assert client.calls == [DESCRIPTION]
    assert enriched.facts is not None
    assert [s.value for s in enriched.facts.skills] == ["Financial modelling"]
    assert enriched.facts.experience == []
    assert [e.value for e in enriched.facts.education] == [
        "Bachelor degree in economics, finance or management"
    ]
    assert [r.text for r in enriched.facts.requirements] == [
        "Valid work permit for the Netherlands",
        "Fluent Dutch",
    ]
    assert [r.requirement_id for r in enriched.facts.requirements] == [
        "synthetic:42:req-001",
        "synthetic:42:req-002",
    ]
    assert enriched.facts.role_family is None


def test_enrichment_keeps_everything_else_unchanged() -> None:
    job = make_job()

    enriched = enrich_one(make_fields())

    untouched = {"facts", "evidence", "extraction"}
    assert enriched.model_dump(exclude=untouched) == job.model_dump(exclude=untouched)
    assert enriched.evidence[: len(job.evidence)] == job.evidence


def test_jobs_are_returned_in_input_order() -> None:
    jobs = [make_job("2"), make_job("1"), make_job("3")]

    enriched = enrich_jobs(jobs, FakeModelClient())

    assert [j.job_id for j in enriched] == [j.job_id for j in jobs]


# --- evidence references --------------------------------------------------


def test_every_fact_and_requirement_cites_resolvable_evidence() -> None:
    enriched = enrich_one(make_fields())
    registry = evidence_by_id(enriched)
    facts = enriched.facts

    cited = [
        (path, eid)
        for path, items in (
            ("facts.skills", facts.skills),
            ("facts.education", facts.education),
            ("facts.requirements", facts.requirements),
        )
        for item in items
        for eid in item.evidence_ids
    ]

    assert cited
    for path, evidence_id in cited:
        reference = registry[evidence_id]
        assert reference.field_path == path
        assert reference.document_id == enriched.description.document_id
        assert reference.quote in enriched.description.text


def test_evidence_ids_are_unique_and_namespaced_by_job() -> None:
    enriched = enrich_one(make_fields())
    ids = [ref.evidence_id for ref in enriched.evidence]

    assert len(ids) == len(set(ids))
    new_ids = ids[1:]  # after the fixture's location evidence
    assert new_ids == [
        "synthetic:42:skill-001",
        "synthetic:42:education-001",
        "synthetic:42:requirement-001",
        "synthetic:42:requirement-002",
    ]


def test_quote_is_stored_as_the_descriptions_own_span() -> None:
    enriched = enrich_one(make_fields())
    [education] = enriched.facts.education

    quote = evidence_by_id(enriched)[education.evidence_ids[0]].quote

    assert quote == "Bachelor degree in economics, finance or\n  management"


def test_items_whose_quote_is_not_in_the_description_are_dropped() -> None:
    fields = make_fields(
        skills=[
            fact("Financial modelling", "build and maintain financial models"),
            fact("Python", "Strong Python skills"),
        ],
        requirements=[
            requirement(
                "Valid work permit for the Netherlands",
                "Applicants need an EU passport",
                "hard_constraint",
                "mandatory",
                "HC_WORK_AUTH",
            ),
        ],
    )

    enriched = enrich_one(fields)

    assert [s.value for s in enriched.facts.skills] == ["Financial modelling"]
    assert enriched.facts.requirements == []
    assert all("passport" not in ref.quote for ref in enriched.evidence)


@pytest.mark.parametrize("blank", ["", "   \n"])
def test_blank_values_and_quotes_are_dropped(blank: str) -> None:
    fields = make_fields(
        skills=[fact(blank, "build and maintain financial models"), fact("Excel", blank)],
        requirements=[requirement(blank, "Excellent Excel skills.")],
    )

    enriched = enrich_one(fields)

    assert enriched.facts.skills == []
    assert enriched.facts.requirements == []


# --- receipt --------------------------------------------------------------


def test_receipt_records_provenance() -> None:
    job = make_job()

    enriched = enrich_one(make_fields(), job)
    receipt = enriched.extraction

    assert receipt is not None
    assert receipt.mode is ExtractionMode.LIVE
    assert receipt.provider == "fake"
    assert receipt.model_id == "fake-model-1"
    assert receipt.prompt_version == load_job_prompt().version
    assert receipt.schema_version == CONTRACT_VERSION
    assert receipt.input_hash == job.description.content_hash
    assert receipt.produced_at.tzinfo is not None
    assert receipt.latency_ms is not None and receipt.latency_ms >= 0


def test_prompt_version_follows_prompt_and_schema() -> None:
    prompt = load_job_prompt()

    assert prompt.text == JOB_PROMPT_PATH.read_text(encoding="utf-8")
    assert prompt.schema == ExtractedJobFields.model_json_schema()
    assert re.fullmatch(r"sha256:[0-9a-f]{16}", prompt.version)


# --- no invented hard constraints ----------------------------------------


def test_approved_mandatory_hard_constraint_is_kept() -> None:
    [work_auth, _] = enrich_one(make_fields()).facts.requirements

    assert work_auth.classification is RequirementClassification.HARD_CONSTRAINT
    assert work_auth.modality is RequirementModality.MANDATORY
    assert work_auth.constraint_id == "HC_WORK_AUTH"


@pytest.mark.parametrize(
    ("modality", "constraint_id"),
    [
        ("mandatory", "HC_VISA_SPONSORSHIP"),  # not in the catalogue
        ("mandatory", "work_authorization_nl"),  # not a catalogue id at all
        ("mandatory", None),
        ("mandatory", "HC_LOCATION"),  # read from locations, not requirements
        ("preferred", "HC_LANGUAGE"),  # approved id, but not mandatory
        ("unspecified", "HC_DEGREE_LEVEL"),
    ],
)
def test_unsupported_hard_constraint_is_kept_as_fit(
    modality: str, constraint_id: str | None
) -> None:
    fields = make_fields(
        requirements=[
            requirement(
                "Fluent Dutch",
                "Fluent Dutch is a plus.",
                "hard_constraint",
                modality,
                constraint_id,
            )
        ]
    )

    [kept] = enrich_one(fields).facts.requirements

    assert kept.classification is RequirementClassification.FIT
    assert kept.constraint_id is None
    assert kept.modality is RequirementModality(modality)


@pytest.mark.parametrize("classification", ["fit", "informational"])
def test_constraint_id_on_non_hard_requirement_is_discarded(
    classification: str,
) -> None:
    fields = make_fields(
        requirements=[
            requirement(
                "Starts January 2027",
                "The internship starts in January 2027.",
                classification,
                "unspecified",
                "HC_GRAD_WINDOW",
            )
        ]
    )

    [kept] = enrich_one(fields).facts.requirements

    assert kept.classification is RequirementClassification(classification)
    assert kept.constraint_id is None


def test_empty_model_answer_invents_nothing() -> None:
    fields = ExtractedJobFields(skills=[], experience=[], education=[], requirements=[])
    job = make_job()

    enriched = enrich_one(fields, job)

    assert enriched.facts.model_dump() == {
        "skills": [],
        "experience": [],
        "education": [],
        "role_family": None,
        "requirements": [],
    }
    assert enriched.evidence == job.evidence


def test_prompt_lists_exactly_the_requirement_constraints() -> None:
    listed = set(re.findall(r"`(HC_[A-Z_]+)`", JOB_PROMPT_PATH.read_text()))

    assert listed == HARD_IDS


# --- failures -------------------------------------------------------------


def test_provider_error_propagates() -> None:
    client = FakeModelClient(error=ExtractionError("Kimi request failed"))

    with pytest.raises(ExtractionError, match="request failed"):
        enrich_jobs([make_job()], client)


def test_failure_on_a_later_job_returns_nothing() -> None:
    client = FakeModelClient(error=ExtractionError("boom"), fail_on_call=2)

    with pytest.raises(ExtractionError, match="boom"):
        enrich_jobs([make_job("1"), make_job("2"), make_job("3")], client)
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    ("jobs", "message"),
    [
        (lambda: [make_job("1"), make_job("1")], "appears more than once"),
        (lambda: [make_job("1"), enrich_one(make_fields(), make_job("2"))], "already enriched"),
        (lambda: [make_job("1"), blank_description_job()], "no text"),
    ],
)
def test_input_defects_are_rejected_before_any_model_call(jobs, message: str) -> None:
    client = FakeModelClient()

    with pytest.raises(ValueError, match=message):
        enrich_jobs(jobs(), client)
    assert client.calls == []


# --- Kimi structured output ----------------------------------------------


def kimi_with_reply(content: str) -> Any:
    pytest.importorskip("openai")
    from oi.providers.kimi import KimiClient

    client = KimiClient(api_key="test-key")
    requests: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        message = SimpleNamespace(content=content, reasoning_content=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason="stop")],
            usage=None,
        )

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    client.requests = requests
    return client


def test_kimi_requests_strict_job_schema() -> None:
    client = kimi_with_reply(make_fields().model_dump_json())

    fields = client.extract_job_fields(DESCRIPTION)

    assert fields == make_fields()
    [request] = client.requests
    schema = request["response_format"]["json_schema"]
    assert schema["name"] == "job_fields"
    assert schema["strict"] is True
    assert schema["schema"] == load_job_prompt().schema
    assert request["messages"][0]["content"] == load_job_prompt().text
    assert request["messages"][1]["content"] == DESCRIPTION


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        ("not json", "valid JSON"),
        ('{"skills": []}', "expected schema"),
        (
            make_fields().model_dump_json().replace('"fit"', '"nice_to_have"'),
            "expected schema",
        ),
    ],
)
def test_kimi_invalid_job_reply_raises_extraction_error(reply: str, message: str) -> None:
    client = kimi_with_reply(reply)

    with pytest.raises(ExtractionError, match=message):
        client.extract_job_fields(DESCRIPTION)


def test_kimi_rejects_empty_description() -> None:
    client = kimi_with_reply("{}")

    with pytest.raises(ValueError, match="empty description"):
        client.extract_job_fields("  \n")
    assert client.requests == []


# --- snapshot -------------------------------------------------------------


def test_enriched_snapshot_round_trips(tmp_path: Path) -> None:
    source = load_snapshot(BATCH01)
    empty = ExtractedJobFields(skills=[], experience=[], education=[], requirements=[])

    snapshot = enrich_snapshot(source, FakeModelClient(empty))
    write_snapshot(snapshot, tmp_path / "enriched.json")

    assert load_snapshot(tmp_path / "enriched.json") == snapshot
    assert snapshot.snapshot_id == f"{source.snapshot_id}-enriched"
    assert snapshot.created_at == source.created_at
    assert snapshot.documents == source.documents
    assert snapshot.source_manifest == source.source_manifest
    assert snapshot.quarantine == source.quarantine
    assert [j.job_id for j in snapshot.jobs] == [j.job_id for j in source.jobs]
