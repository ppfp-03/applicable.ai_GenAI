"""Orchestration for job requirement extraction.

This module mirrors `oi.intelligence.extraction` for jobs. It takes normalized
`JobRecord`s, hands each description to a model client, and returns the same
jobs enriched with evidence-backed `JobFacts`, the `EvidenceRef`s behind them
and an `ExtractionReceipt`.

The model proposes; this layer decides:

- A skill, experience, education item or requirement survives only if its
  quote is found in the job description. The stored quote is the
  description's own span.
- A requirement stays a `hard_constraint` only if it is `mandatory` and names
  a rule-catalogue constraint that is triggered by requirements. Anything else
  the model marks as hard becomes `fit`, so the model cannot invent a gate
  (PROJECT_CONTEXT, closed hard-constraint taxonomy; FR-12).
- `role_family` is left unset: no approved role-family vocabulary exists, and
  ranking compares the label with candidate preferences as-is.

Extraction is all-or-nothing. A job that cannot be extracted raises, and no
enriched jobs are returned, so a failure can never look like a job with no
requirements.

The demo uses a prepared enriched snapshot rather than live extraction:

    PYTHONPATH=src python -m oi.intelligence.job_extraction \\
        --input data/snapshots/greenhouse_batch01.json \\
        --output data/snapshots/greenhouse_batch01_enriched.json
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from oi.contracts import (
    CONTRACT_VERSION,
    EvidenceRef,
    ExtractionMode,
    ExtractionReceipt,
    JobFacts,
    JobRecord,
    JobSnapshot,
    RequirementClassification,
    RequirementFact,
    RequirementModality,
    SupportedText,
)
from oi.intelligence.eligibility import load_rule_catalogue
from oi.providers.model_client import (
    ExtractedJobFields,
    ExtractedRequirement,
    ModelClient,
    load_job_prompt,
)

logger = logging.getLogger(__name__)

#: JobFacts fields filled from the description, with the short name used in
#: evidence ids.
JOB_FIELDS = (
    ("skills", "skill"),
    ("experience", "experience"),
    ("education", "education"),
)


def enrich_jobs(jobs: list[JobRecord], model_client: ModelClient) -> list[JobRecord]:
    """Enrich jobs with evidence-backed facts extracted from their descriptions.

    Flow: JobRecord.description -> model client -> quote check -> hard
    constraint check -> enriched JobRecord.

    Args:
        jobs: Normalized jobs not yet enriched (`facts` and `extraction` null).
        model_client: The client used to perform the extraction.

    Returns:
        The jobs in input order, each with `facts`, the new evidence appended
        to its existing evidence, and an `extraction` receipt.

    Raises:
        ValueError: If a job ID repeats, a job is already enriched, or a
            description has no text. Checked for every job before any model
            call.
        ExtractionError: Propagated from the provider when a request fails or
            its response cannot be parsed. Never swallowed.
    """
    seen: set[str] = set()
    for job in jobs:
        if job.job_id in seen:
            raise ValueError(f"Job '{job.job_id}' appears more than once.")
        seen.add(job.job_id)
        if job.facts is not None or job.extraction is not None:
            raise ValueError(f"Job '{job.job_id}' is already enriched.")
        if not job.description.text.strip():
            raise ValueError(
                f"Job '{job.job_id}' description has no text to extract from."
            )

    prompt_version = load_job_prompt().version
    hard_constraint_ids = frozenset(
        spec.constraint_id
        for spec in load_rule_catalogue().constraints
        if spec.trigger == "requirement"
    )
    return [
        _enrich_job(job, model_client, prompt_version, hard_constraint_ids)
        for job in jobs
    ]


def _enrich_job(
    job: JobRecord,
    model_client: ModelClient,
    prompt_version: str,
    hard_constraint_ids: frozenset[str],
) -> JobRecord:
    document = job.description

    started = time.perf_counter()
    fields: ExtractedJobFields = model_client.extract_job_fields(document.text)
    latency_ms = round((time.perf_counter() - started) * 1000)

    evidence: list[EvidenceRef] = []

    def cite(short_name: str, field_path: str, quote: str) -> str:
        count = sum(1 for ref in evidence if ref.field_path == field_path)
        evidence_id = f"{job.job_id}:{short_name}-{count + 1:03d}"
        evidence.append(
            EvidenceRef(
                evidence_id=evidence_id,
                document_id=document.document_id,
                quote=quote,
                field_path=field_path,
            )
        )
        return evidence_id

    supported: dict[str, list[SupportedText]] = {}
    for field_name, short_name in JOB_FIELDS:
        supported[field_name] = []
        for fact in getattr(fields, field_name):
            quote = _find_quote(fact.value, fact.quote, document.text)
            if quote is None:
                logger.warning(
                    "Dropped %s fact %r from '%s': quote not found in description.",
                    field_name,
                    fact.value,
                    job.job_id,
                )
                continue
            evidence_id = cite(short_name, f"facts.{field_name}", quote)
            supported[field_name].append(
                SupportedText(value=fact.value.strip(), evidence_ids=[evidence_id])
            )

    requirements: list[RequirementFact] = []
    for item in fields.requirements:
        quote = _find_quote(item.text, item.quote, document.text)
        if quote is None:
            logger.warning(
                "Dropped requirement %r from '%s': quote not found in description.",
                item.text,
                job.job_id,
            )
            continue
        classification, constraint_id = _checked_classification(
            item, hard_constraint_ids, job.job_id
        )
        evidence_id = cite("requirement", "facts.requirements", quote)
        requirements.append(
            RequirementFact(
                requirement_id=f"{job.job_id}:req-{len(requirements) + 1:03d}",
                text=item.text.strip(),
                classification=classification,
                modality=item.modality,
                constraint_id=constraint_id,
                evidence_ids=[evidence_id],
            )
        )

    existing_ids = {ref.evidence_id for ref in job.evidence}
    clashes = sorted(existing_ids & {ref.evidence_id for ref in evidence})
    if clashes:
        raise ValueError(f"Job '{job.job_id}' already has evidence ids {clashes}.")

    receipt = ExtractionReceipt(
        mode=ExtractionMode.LIVE,
        provider=model_client.provider_name,
        model_id=model_client.model_id,
        prompt_version=prompt_version,
        schema_version=CONTRACT_VERSION,
        input_hash=document.content_hash,
        produced_at=datetime.now(timezone.utc),
        latency_ms=latency_ms,
    )
    facts = JobFacts(
        skills=supported["skills"],
        experience=supported["experience"],
        education=supported["education"],
        role_family=None,
        requirements=requirements,
    )
    enriched = job.model_copy(
        update={
            "facts": facts,
            "evidence": [*job.evidence, *evidence],
            "extraction": receipt,
        }
    )
    # model_copy does not validate; round-trip so the contract checks quotes.
    return JobRecord.model_validate(enriched.model_dump())


def _checked_classification(
    item: ExtractedRequirement,
    hard_constraint_ids: frozenset[str],
    job_id: str,
) -> tuple[RequirementClassification, str | None]:
    """The model's classification, unless it would invent a hard constraint.

    A hard constraint must be mandatory and name a catalogue constraint that
    requirements trigger; otherwise it is kept as a `fit` requirement. A
    constraint id on a non-hard requirement is discarded.
    """
    if item.classification is not RequirementClassification.HARD_CONSTRAINT:
        if item.constraint_id is not None:
            logger.warning(
                "Ignored constraint id %r on %s requirement %r in '%s'.",
                item.constraint_id,
                item.classification.value,
                item.text,
                job_id,
            )
        return item.classification, None

    if item.constraint_id not in hard_constraint_ids:
        reason = f"constraint id {item.constraint_id!r} is not approved"
    elif item.modality is not RequirementModality.MANDATORY:
        reason = f"modality is {item.modality.value}"
    else:
        return item.classification, item.constraint_id

    logger.warning(
        "Kept hard constraint %r in '%s' as fit: %s.", item.text, job_id, reason
    )
    return RequirementClassification.FIT, None


def _find_quote(value: str, quote: str, text: str) -> str | None:
    """Locate a quote in the description and return the description's span.

    Matching tolerates differences in whitespace only, as in
    `oi.intelligence.extraction`. Returns None when the value or quote is
    blank, or the quote is absent.
    """
    if not value.strip():
        return None
    words = quote.split()
    if not words:
        return None
    match = re.search(r"\s+".join(map(re.escape, words)), text)
    return match.group(0) if match else None


def enrich_snapshot(snapshot: JobSnapshot, model_client: ModelClient) -> JobSnapshot:
    """The same snapshot with every job enriched, under a derived snapshot ID.

    Documents, source manifest, quarantine and creation time are kept: the
    postings and their observation are unchanged, and each job's receipt
    records when its extraction happened.
    """
    return JobSnapshot(
        schema_version=snapshot.schema_version,
        snapshot_id=f"{snapshot.snapshot_id}-enriched",
        created_at=snapshot.created_at,
        jobs=enrich_jobs(snapshot.jobs, model_client),
        documents=snapshot.documents,
        source_manifest=snapshot.source_manifest,
        quarantine=snapshot.quarantine,
    )


def main(argv: Sequence[str] | None = None) -> int:
    from dotenv import load_dotenv

    from oi.io.greenhouse_batch import write_snapshot
    from oi.io.snapshot import load_snapshot
    from oi.providers.kimi import KimiClient

    parser = argparse.ArgumentParser(
        description="Enrich every job in a snapshot and write the result."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # KimiClient reads its key from the environment; a set variable wins.
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")

    source = load_snapshot(args.input)
    snapshot = enrich_snapshot(source, KimiClient())
    write_snapshot(snapshot, args.output)

    for job in snapshot.jobs:
        facts = job.facts
        hard = [r.constraint_id for r in facts.requirements if r.constraint_id]
        print(
            f"{job.job_id}: {len(facts.skills)} skills, "
            f"{len(facts.experience)} experience, {len(facts.education)} education, "
            f"{len(facts.requirements)} requirements (hard: {hard or 'none'}), "
            f"{job.extraction.latency_ms} ms"
        )
    print(f"{snapshot.snapshot_id}: enriched {len(snapshot.jobs)} jobs into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
