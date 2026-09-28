"""Integrity of the prepared enriched Batch 01 snapshot (JOB-EXT-01).

Validates the generated file only. Nothing here calls a model: the artifact
is produced once by `python -m oi.intelligence.job_extraction` and reused.
"""

from pathlib import Path

import pytest

from oi.contracts import (
    CONTRACT_VERSION,
    ExtractionMode,
    JobSnapshot,
    RequirementClassification,
    RequirementModality,
    quote_occurs_in,
)
from oi.intelligence.eligibility import load_rule_catalogue
from oi.io.snapshot import load_snapshot
from oi.providers.model_client import load_job_prompt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "snapshots" / "greenhouse_batch01.json"
ENRICHED = ROOT / "data" / "snapshots" / "greenhouse_batch01_enriched.json"

FACT_FIELDS = ("skills", "experience", "education")
ENRICHED_FIELDS = {"facts", "evidence", "extraction"}


@pytest.fixture(scope="module")
def source() -> JobSnapshot:
    return load_snapshot(SOURCE)


@pytest.fixture(scope="module")
def enriched() -> JobSnapshot:
    return load_snapshot(ENRICHED)


def test_snapshot_identity(source: JobSnapshot, enriched: JobSnapshot) -> None:
    assert enriched.schema_version == source.schema_version
    assert enriched.snapshot_id == f"{source.snapshot_id}-enriched"
    assert enriched.created_at == source.created_at
    assert enriched.documents == source.documents
    assert enriched.source_manifest == source.source_manifest
    assert enriched.quarantine == source.quarantine


def test_contains_exactly_the_batch01_jobs(
    source: JobSnapshot, enriched: JobSnapshot
) -> None:
    assert len(enriched.jobs) == 8
    assert [job.job_id for job in enriched.jobs] == [job.job_id for job in source.jobs]


def test_only_enrichment_fields_differ_from_source(
    source: JobSnapshot, enriched: JobSnapshot
) -> None:
    for before, after in zip(source.jobs, enriched.jobs):
        assert after.model_dump(exclude=ENRICHED_FIELDS) == before.model_dump(
            exclude=ENRICHED_FIELDS
        ), after.job_id
        assert after.evidence[: len(before.evidence)] == before.evidence, after.job_id


def test_every_job_has_facts_requirements_and_receipt(enriched: JobSnapshot) -> None:
    for job in enriched.jobs:
        assert job.facts is not None, job.job_id
        assert job.facts.requirements, job.job_id
        assert job.extraction is not None, job.job_id
        assert job.facts.role_family is None, job.job_id


def test_every_cited_evidence_id_resolves(enriched: JobSnapshot) -> None:
    for job in enriched.jobs:
        registry = {ref.evidence_id: ref for ref in job.evidence}
        assert len(registry) == len(job.evidence), f"{job.job_id}: duplicate ids"

        cited = [
            (f"facts.{name}", evidence_id)
            for name in FACT_FIELDS
            for item in getattr(job.facts, name)
            for evidence_id in item.evidence_ids
        ] + [
            ("facts.requirements", evidence_id)
            for requirement in job.facts.requirements
            for evidence_id in requirement.evidence_ids
        ]

        for field_path, evidence_id in cited:
            reference = registry.get(evidence_id)
            assert reference is not None, f"{job.job_id}: {evidence_id} missing"
            assert reference.field_path == field_path, evidence_id
            assert reference.document_id == job.description.document_id, evidence_id
            assert quote_occurs_in(reference.quote, job.description.text), evidence_id


def test_no_orphan_extraction_evidence(enriched: JobSnapshot) -> None:
    for job in enriched.jobs:
        cited = {
            evidence_id
            for name in FACT_FIELDS
            for item in getattr(job.facts, name)
            for evidence_id in item.evidence_ids
        } | {
            evidence_id
            for requirement in job.facts.requirements
            for evidence_id in requirement.evidence_ids
        }
        extracted = {
            ref.evidence_id
            for ref in job.evidence
            if ref.field_path.startswith("facts.")
        }
        assert extracted == cited, job.job_id


def test_requirement_ids_are_unique_and_namespaced(enriched: JobSnapshot) -> None:
    ids = [r.requirement_id for job in enriched.jobs for r in job.facts.requirements]
    assert len(ids) == len(set(ids))
    for job in enriched.jobs:
        for requirement in job.facts.requirements:
            assert requirement.requirement_id.startswith(f"{job.job_id}:req-")


def test_no_unsupported_hard_constraints(enriched: JobSnapshot) -> None:
    approved = {
        spec.constraint_id
        for spec in load_rule_catalogue().constraints
        if spec.trigger == "requirement"
    }
    for job in enriched.jobs:
        for requirement in job.facts.requirements:
            if requirement.classification is RequirementClassification.HARD_CONSTRAINT:
                assert requirement.constraint_id in approved, requirement.requirement_id
                assert requirement.modality is RequirementModality.MANDATORY, (
                    requirement.requirement_id
                )
            else:
                assert requirement.constraint_id is None, requirement.requirement_id


def test_alternative_path_requirement_is_not_a_student_status_gate(
    enriched: JobSnapshot,
) -> None:
    """WPP Media welcomes students, recent graduates and early-career
    professionals alike, so student status must not become a hard gate."""
    job = next(job for job in enriched.jobs if job.job_id == "greenhouse:5424219008")
    registry = {ref.evidence_id: ref for ref in job.evidence}

    citing = [
        requirement
        for requirement in job.facts.requirements
        if any(
            "Early career professionals" in registry[evidence_id].quote
            for evidence_id in requirement.evidence_ids
        )
    ]

    assert citing, "the alternative-path requirement was not extracted"
    for requirement in citing:
        assert (
            requirement.classification is not RequirementClassification.HARD_CONSTRAINT
        ), requirement.requirement_id
        assert requirement.constraint_id is None, requirement.requirement_id
        assert "early career" in requirement.text.casefold(), requirement.text
    assert not any(
        requirement.constraint_id == "HC_STUDENT_STATUS"
        for requirement in job.facts.requirements
    )


def test_extraction_provenance(enriched: JobSnapshot) -> None:
    prompt_versions = {job.extraction.prompt_version for job in enriched.jobs}
    assert len(prompt_versions) == 1

    for job in enriched.jobs:
        receipt = job.extraction
        assert receipt.mode is ExtractionMode.LIVE, job.job_id
        assert receipt.provider == "kimi", job.job_id
        assert receipt.model_id, job.job_id
        assert receipt.schema_version == CONTRACT_VERSION, job.job_id
        assert receipt.input_hash == job.description.content_hash, job.job_id
        assert receipt.latency_ms is not None and receipt.latency_ms > 0, job.job_id


def test_artifact_matches_the_current_prompt(enriched: JobSnapshot) -> None:
    """A prompt or schema change must be followed by regenerating the file."""
    assert enriched.jobs[0].extraction.prompt_version == load_job_prompt().version
