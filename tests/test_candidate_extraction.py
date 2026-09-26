"""Tests for candidate extraction: provider boundary and profile assembly."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from oi.contracts import (
    CONTRACT_VERSION,
    CandidateProfile,
    ExtractionMode,
    SourceDocument,
)
from oi.intelligence.extraction import extract_candidate
from oi.providers.model_client import (
    ExtractedFact,
    ExtractedFields,
    ExtractionError,
    ModelClient,
    load_candidate_prompt,
    model_input_version,
)

CV_TEXT = (
    "Giulia Rossi\n"
    "MSc Finance, Bocconi University, 2026\n"
    "Summer Analyst, Mediobanco, June-August 2025\n"
    "Skills: Python, financial modelling in Excel,\n"
    "valuation (DCF, comparables)\n"
)


def make_cv(text: str = CV_TEXT, **overrides: Any) -> SourceDocument:
    payload: dict[str, Any] = {
        "document_id": "cv-001",
        "kind": "cv",
        "text": text,
        "content_hash": "sha256-of-cv-bytes",
        "source_ref": "uploaded_pdf",
    }
    payload.update(overrides)
    return SourceDocument(**payload)


def fact(value: str, quote: str) -> ExtractedFact:
    return ExtractedFact(value=value, quote=quote)


def make_fields(**overrides: list[ExtractedFact]) -> ExtractedFields:
    payload: dict[str, list[ExtractedFact]] = {
        "skills": [fact("Python", "Skills: Python")],
        "education": [
            fact(
                "MSc Finance, Bocconi University",
                "MSc Finance, Bocconi University, 2026",
            )
        ],
        "experience": [
            fact(
                "Summer Analyst at Mediobanco",
                "Summer Analyst, Mediobanco, June-August 2025",
            )
        ],
    }
    payload.update(overrides)
    return ExtractedFields(**payload)


class FakeModelClient:
    """A ModelClient that returns a canned reply or raises a canned error."""

    provider_name = "fake"
    model_id = "fake-model-1"

    def __init__(
        self,
        fields: ExtractedFields | None = None,
        error: Exception | None = None,
    ) -> None:
        self.fields = fields if fields is not None else make_fields()
        self.error = error
        self.calls: list[str] = []

    def extract_candidate_fields(self, document_text: str) -> ExtractedFields:
        self.calls.append(document_text)
        if self.error is not None:
            raise self.error
        return self.fields


# --- extract_candidate ----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    assert isinstance(FakeModelClient(), ModelClient)


def test_valid_extraction_creates_valid_candidate_profile() -> None:
    document = make_cv()

    profile = extract_candidate(document, FakeModelClient())

    # Re-validating the dumped profile proves it round-trips the contract.
    assert CandidateProfile.model_validate(profile.model_dump()) == profile
    assert profile.schema_version == CONTRACT_VERSION
    assert profile.candidate_id == "cv-001"
    assert profile.cv_document_id == "cv-001"
    assert profile.provenance.documents == {"cv-001": document}

    assert [s.value for s in profile.skills] == ["Python"]
    assert [s.value for s in profile.education] == ["MSc Finance, Bocconi University"]
    assert [s.value for s in profile.experience] == ["Summer Analyst at Mediobanco"]

    evidence = {ref.evidence_id: ref for ref in profile.provenance.evidence}
    assert set(evidence) == {
        "ev-cv-001-skill-001",
        "ev-cv-001-education-001",
        "ev-cv-001-experience-001",
    }
    for field_name in ("skills", "education", "experience"):
        for supported in getattr(profile, field_name):
            (evidence_id,) = supported.evidence_ids
            ref = evidence[evidence_id]
            assert ref.field_path == field_name
            assert ref.document_id == "cv-001"
            assert ref.quote in document.text


def test_valid_extraction_records_complete_receipt() -> None:
    profile = extract_candidate(make_cv(), FakeModelClient())

    receipt = profile.provenance.extraction
    assert receipt.mode is ExtractionMode.LIVE
    assert receipt.provider == "fake"
    assert receipt.model_id == "fake-model-1"
    assert receipt.prompt_version == load_candidate_prompt().version
    assert receipt.prompt_version.startswith("sha256:")
    assert receipt.schema_version == CONTRACT_VERSION
    assert receipt.input_hash == "sha256-of-cv-bytes"
    assert receipt.produced_at.tzinfo is not None
    assert receipt.latency_ms is not None and receipt.latency_ms >= 0


def test_facts_the_cv_cannot_support_start_empty() -> None:
    profile = extract_candidate(make_cv(), FakeModelClient())

    assert profile.preferences.preferred_country_codes == []
    assert profile.preferences.allowed_country_codes is None
    assert profile.declarations.additional_citizenships == []
    assert profile.declarations.work_authorizations == []
    assert profile.eligibility_answers == {}


def test_invalid_quote_is_rejected() -> None:
    fields = make_fields(
        skills=[
            fact("Python", "Skills: Python"),
            fact("Bloomberg Terminal", "Tools: Bloomberg Terminal"),
        ]
    )

    profile = extract_candidate(make_cv(), FakeModelClient(fields))

    assert [s.value for s in profile.skills] == ["Python"]
    quotes = [ref.quote for ref in profile.provenance.evidence]
    assert "Tools: Bloomberg Terminal" not in quotes
    assert len(profile.provenance.evidence) == 3


def test_near_miss_quote_is_rejected() -> None:
    # Only whitespace is forgiven; a changed character is a different quote.
    fields = make_fields(skills=[fact("Python", "skills: python")])

    profile = extract_candidate(make_cv(), FakeModelClient(fields))

    assert profile.skills == []


def test_blank_fact_or_quote_is_rejected() -> None:
    fields = make_fields(
        skills=[fact("   ", "Skills: Python"), fact("Python", "   ")]
    )

    profile = extract_candidate(make_cv(), FakeModelClient(fields))

    assert profile.skills == []


def test_quote_across_line_break_is_stored_verbatim() -> None:
    fields = make_fields(
        skills=[
            fact(
                "Financial modelling and valuation",
                "financial modelling in Excel, valuation (DCF, comparables)",
            )
        ]
    )

    profile = extract_candidate(make_cv(), FakeModelClient(fields))

    (ref,) = [r for r in profile.provenance.evidence if r.field_path == "skills"]
    assert ref.quote == "financial modelling in Excel,\nvaluation (DCF, comparables)"
    assert ref.quote in CV_TEXT


def test_provider_failure_propagates() -> None:
    client = FakeModelClient(error=ExtractionError("provider is down"))

    with pytest.raises(ExtractionError, match="provider is down"):
        extract_candidate(make_cv(), client)


def test_empty_document_fails_before_calling_provider() -> None:
    client = FakeModelClient()

    with pytest.raises(ValueError, match="no text"):
        extract_candidate(make_cv(text="  \n\t "), client)

    assert client.calls == []


def test_non_cv_document_fails_before_calling_provider() -> None:
    client = FakeModelClient()

    with pytest.raises(ValueError, match="not 'cv'"):
        extract_candidate(make_cv(kind="job"), client)

    assert client.calls == []


# --- prompt and its version -----------------------------------------------


def test_prompt_keeps_programming_languages_and_leaves_out_human_languages() -> None:
    # Human languages feed HC_LANGUAGE through a separate path, not skills.
    text = load_candidate_prompt().text
    skills_rule = text.split("- **skills**", 1)[1].split("- **education**", 1)[0]

    assert "including\n  programming languages" in skills_rule
    assert "Leave out spoken or written human languages" in skills_rule


def test_prompt_asks_for_one_entry_per_role_and_per_degree() -> None:
    text = load_candidate_prompt().text
    education_rule = text.split("- **education**", 1)[1].split("- **experience**", 1)[0]
    experience_rule = text.split("- **experience**", 1)[1].split("##", 1)[0]

    assert "One entry per\n  degree" in education_rule
    assert "One\n  entry per role" in experience_rule
    assert "Never merge\n  roles" in experience_rule


def test_prompt_asks_for_three_part_education_and_experience_values() -> None:
    text = load_candidate_prompt().text

    assert 'joined\nby " · "' in text
    assert "MSc in International Management · Fudan University · Sep 2025 –\nJul 2027" in text
    assert "never fill it in" in text


def test_several_roles_become_distinct_experience_entries() -> None:
    text = CV_TEXT + "Analyst, Acme, 2024\nIntern, Acme, 2023\n"
    roles = [
        fact("Summer Analyst at Mediobanco", "Summer Analyst, Mediobanco, June-August 2025"),
        fact("Analyst at Acme", "Analyst, Acme, 2024"),
        fact("Intern at Acme", "Intern, Acme, 2023"),
    ]

    profile = extract_candidate(make_cv(text), FakeModelClient(fields=make_fields(experience=roles)))

    assert [e.value for e in profile.experience] == ["Summer Analyst at Mediobanco", "Analyst at Acme", "Intern at Acme"]
    assert len({e.evidence_ids[0] for e in profile.experience}) == 3


def test_model_input_version_is_deterministic() -> None:
    schema = ExtractedFields.model_json_schema()
    reordered = dict(reversed(list(schema.items())))

    assert model_input_version("prompt", schema) == model_input_version(
        "prompt", ExtractedFields.model_json_schema()
    )
    assert model_input_version("prompt", schema) == model_input_version(
        "prompt", reordered
    )


def test_model_input_version_changes_with_schema() -> None:
    schema = ExtractedFields.model_json_schema()
    changed = json.loads(json.dumps(schema))
    changed["$defs"]["ExtractedFact"]["properties"]["quote"]["description"] = "x"

    assert model_input_version("prompt", schema) != model_input_version(
        "prompt", changed
    )


def test_model_input_version_changes_with_prompt_text() -> None:
    schema = ExtractedFields.model_json_schema()

    assert model_input_version("prompt", schema) != model_input_version(
        "prompt.", schema
    )


def test_loaded_prompt_version_covers_text_and_schema() -> None:
    prompt = load_candidate_prompt()

    assert prompt.schema == ExtractedFields.model_json_schema()
    assert prompt.version == model_input_version(prompt.text, prompt.schema)


# --- provider boundary ----------------------------------------------------


def test_extracted_fields_schema_is_strict() -> None:
    # Strict structured output rejects schemas with optional or extra keys.
    schema = ExtractedFields.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"skills", "education", "experience"}
    fact_schema = schema["$defs"]["ExtractedFact"]
    assert fact_schema["additionalProperties"] is False
    assert set(fact_schema["required"]) == {"value", "quote"}


def _kimi_with_reply(content: str | None) -> Any:
    pytest.importorskip("openai")
    from oi.providers.kimi import KimiClient

    client = KimiClient(api_key="test-key")
    requests: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    client.requests = requests
    return client


def test_kimi_returns_extracted_fields() -> None:
    reply = make_fields().model_dump()
    client = _kimi_with_reply(json.dumps(reply))

    fields = client.extract_candidate_fields(CV_TEXT)

    assert fields == make_fields()
    (request,) = client.requests
    assert request["messages"][0]["content"] == load_candidate_prompt().text
    assert request["messages"][1]["content"] == CV_TEXT
    json_schema = request["response_format"]["json_schema"]
    assert json_schema["strict"] is True
    # The schema sent is the one the receipt's prompt_version was hashed from.
    assert json_schema["schema"] == load_candidate_prompt().schema


@pytest.mark.parametrize(
    "content",
    [None, "not json", json.dumps({"skills": []}), json.dumps({"name": "Giulia"})],
)
def test_kimi_unusable_reply_raises_extraction_error(content: str | None) -> None:
    client = _kimi_with_reply(content)

    with pytest.raises(ExtractionError):
        client.extract_candidate_fields(CV_TEXT)
