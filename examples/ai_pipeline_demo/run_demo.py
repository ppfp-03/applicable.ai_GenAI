"""AI pipeline demonstration: one synthetic CV and one prepared JobSnapshot,
run end to end outside the Streamlit app.

    PYTHONPATH=src python -m examples.ai_pipeline_demo.run_demo

The steps are the existing intelligence modules, called in order; this module
only wires them together and labels how each semantic result was produced:

1. CV -> CandidateProfile: `oi.intelligence.extraction.extract_candidate`.
2. JobSnapshot -> JobFacts: `oi.runtime.jobs.load_jobs`, which enriches with
   `oi.intelligence.job_extraction` in ``live`` mode and checks the committed
   enrichment in ``cache`` mode.
3. Eligibility: `oi.intelligence.eligibility.assess_eligibility`, per job.
4. Ranking, only with ``--include-ranking``:
   `oi.intelligence.ranking_adapter.rank_with_eligibility`. It is a
   development diagnostic, not a product result: the weights and horizons are
   development values, and with the prepared jobs only some factors have a
   value. The report names the active and missing factors.

CV and job modes are chosen separately (PROJECT_CONTEXT, "Three explicitly
labeled execution modes"), and a mode never falls back to another one:

- CV ``live``: the model reads the CV during this run.
- CV ``cache``: a profile recorded by an earlier live run, served only when
  its receipt matches the cache key -- the CV's content hash, the expected
  provider and model, the current candidate prompt version and the contract
  schema version. A stale cache raises.
- CV ``fixture``: a handcrafted model reply (`cv_fixture_reply.json`) passed
  through the same extraction code, receipted as ``fixture``. It proves the
  plumbing, never model quality.
- Job modes are `oi.runtime.jobs.JobMode`: ``snapshot`` (no facts),
  ``cache`` and ``live``.

With the defaults (CV cache, job cache) no model is called and no key is
needed, and the report is identical on every run: the ranking clock `now`
is the snapshot's creation time unless given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from oi.contracts import (
    CONTRACT_VERSION,
    CandidateProfile,
    DocumentKind,
    ExtractionMode,
    SourceDocument,
)
from oi.intelligence.eligibility import (
    EligibilityResult,
    RuleStatus,
    assess_eligibility,
    load_job_parameters,
    load_rule_catalogue,
)
from oi.intelligence.extraction import extract_candidate
from oi.intelligence.ranking import PipelineEntry
from oi.intelligence.ranking_adapter import AdaptedRanking, rank_with_eligibility
from oi.io.pdf import extract_pdf_text
from oi.providers.model_client import (
    ExtractedFields,
    ExtractedJobFields,
    ExtractionError,
    ModelClient,
    load_candidate_prompt,
)
from oi.runtime.jobs import JobMode, JobRuntime, ModelIdentity, StaleCacheError, load_jobs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CV_PATH = HERE / "synthetic_cv.txt"
CV_CACHE_PATH = HERE / "cv_cache.json"
CV_FIXTURE_PATH = HERE / "cv_fixture_reply.json"
RANKING_CONFIG_PATH = ROOT / "config" / "ranking.json"

#: No approved horizon exists; these are the development values the ranking
#: tests use, and the report prints them.
DEADLINE_HORIZON_DAYS = 30
FRESHNESS_HORIZON_DAYS = 30


class CvMode(str, Enum):
    """How the CandidateProfile is produced; see the module docstring."""

    LIVE = "live"
    CACHE = "cache"
    FIXTURE = "fixture"


class FixtureModelClient:
    """A ModelClient that returns a handcrafted candidate reply."""

    provider_name = "fixture"
    model_id = "handcrafted"

    def __init__(self, reply: ExtractedFields) -> None:
        self.reply = reply

    def extract_candidate_fields(self, document_text: str) -> ExtractedFields:
        return self.reply

    def extract_job_fields(self, description_text: str) -> ExtractedJobFields:
        raise NotImplementedError("The CV fixture has no job replies.")


def load_cv(path: Path) -> SourceDocument:
    """The CV as a SourceDocument: PDFs through the app's PDF ingestion,
    anything else read as UTF-8 text. The content hash is of the file bytes,
    so any edit to the CV changes the cache key."""
    data = path.read_bytes()
    document_id = f"cv-{path.stem.replace('_', '-')}"
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(data, document_id)
    return SourceDocument(
        document_id=document_id,
        kind=DocumentKind.CV,
        text=data.decode("utf-8"),
        content_hash=hashlib.sha256(data).hexdigest(),
        source_ref=f"file:{path.name}",
    )


def extract_cv(
    document: SourceDocument,
    mode: CvMode,
    *,
    model_client: ModelClient | None = None,
    cache_model: ModelIdentity | None = None,
    cache_path: Path = CV_CACHE_PATH,
    fixture_path: Path = CV_FIXTURE_PATH,
) -> CandidateProfile:
    """The CandidateProfile for `document` in `mode`.

    Raises:
        ValueError: If `model_client` is missing in ``live`` mode or
            `cache_model` is missing in ``cache`` mode.
        StaleCacheError: In ``cache`` mode, if the cache does not match.
        ExtractionError: In ``live`` mode, propagated from the provider.
    """
    if mode is CvMode.LIVE:
        if model_client is None:
            raise ValueError("Live CV mode needs a model client.")
        return extract_candidate(document, model_client)
    if mode is CvMode.CACHE:
        if cache_model is None:
            raise ValueError("Cache CV mode needs the expected provider and model.")
        cached = CandidateProfile.model_validate_json(cache_path.read_text(encoding="utf-8"))
        check_cv_cache(document, cached, cache_model)
        return cached

    reply = ExtractedFields.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    profile = extract_candidate(document, FixtureModelClient(reply))
    receipt = profile.provenance.extraction.model_copy(update={"mode": ExtractionMode.FIXTURE})
    provenance = profile.provenance.model_copy(update={"extraction": receipt})
    return profile.model_copy(update={"provenance": provenance})


def check_cv_cache(document: SourceDocument, cached: CandidateProfile, model: ModelIdentity) -> None:
    """Check that `cached` is a current extraction of `document` by `model`.

    Raises:
        StaleCacheError: If the profile is for another document or its
            receipt fails the cache key.
    """
    receipt = cached.provenance.extraction
    if receipt is None:
        raise StaleCacheError(f"Cached profile '{cached.candidate_id}' has no receipt.")
    key = {
        "input hash": (receipt.input_hash, document.content_hash),
        "document id": (cached.cv_document_id, document.document_id),
        "provider": (receipt.provider, model.provider),
        "model id": (receipt.model_id, model.model_id),
        "prompt version": (receipt.prompt_version, load_candidate_prompt().version),
        "schema version": (receipt.schema_version, CONTRACT_VERSION),
    }
    for name, (cached_value, current) in key.items():
        if cached_value != current:
            raise StaleCacheError(
                f"Cached profile has {name} {cached_value!r}, expected {current!r}. "
                "Re-record it with --cv-mode live --record-cv-cache."
            )


def assess_jobs(profile: CandidateProfile, jobs: JobRuntime) -> list[EligibilityResult]:
    """Eligibility for every job."""
    catalogue = load_rule_catalogue()
    parameters = load_job_parameters()
    return [
        assess_eligibility(profile, job, catalogue, job_parameters=parameters)
        for job in jobs.jobs
    ]


def rank_jobs(
    profile: CandidateProfile,
    jobs: JobRuntime,
    results: list[EligibilityResult],
    *,
    now: datetime | None = None,
) -> tuple[AdaptedRanking, dict[str, Any]]:
    """The development ranking of every job and the settings used."""
    config = json.loads(RANKING_CONFIG_PATH.read_text(encoding="utf-8"))
    now = now or jobs.snapshot.created_at
    settings = {
        "weights_version": config["version"],
        "factors": config["factors"],
        "weights": config["weights"],
        "now": now.isoformat(),
        "deadline_horizon_days": DEADLINE_HORIZON_DAYS,
        "freshness_horizon_days": FRESHNESS_HORIZON_DAYS,
    }
    ranked = rank_with_eligibility(
        profile,
        jobs.jobs,
        results,
        weights=config["weights"],
        now=now,
        deadline_horizon_days=DEADLINE_HORIZON_DAYS,
        freshness_horizon_days=FRESHNESS_HORIZON_DAYS,
        limit=len(jobs.jobs),
    )
    return ranked, settings


# --- Report -----------------------------------------------------------------


def _entry(rank: int | None, entry: PipelineEntry) -> dict[str, Any]:
    return {
        "rank": rank,
        "job_id": entry.job_id,
        "title": entry.assessed.job.title,
        "company": entry.assessed.job.company,
        "eligibility": entry.assessed.eligibility,
        "score": entry.score,
        "factors": dict(entry.breakdown.factors),
        "missing_factors": list(entry.breakdown.missing),
        "effective_weights": dict(entry.breakdown.effective_weights),
    }


def _ranking(ranked: AdaptedRanking, settings: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, Any] = {"settings": settings}
    for name in ("eligible", "uncertain"):
        group = getattr(ranked.pipeline, name)
        scored = [*group.top, *group.rest]
        groups[name] = [
            *(_entry(i, entry) for i, entry in enumerate(scored, 1)),
            *(_entry(None, entry) for entry in group.unscored),
        ]
    groups["excluded"] = [
        {"job_id": item.job_id, "title": item.assessed.job.title, "reason": item.reason}
        for item in ranked.pipeline.excluded
    ]
    groups["diagnostics"] = [{"code": d.code, "job_id": d.job_id} for d in ranked.diagnostics]
    # A factor is active when at least one job has a value for it.
    valued = {
        name
        for group in ("eligible", "uncertain")
        for entry in groups[group]
        for name, value in entry["factors"].items()
        if value is not None
    }
    groups["active_factors"] = [name for name in settings["factors"] if name in valued]
    groups["missing_factors"] = [name for name in settings["factors"] if name not in valued]
    return groups


def build_report(
    cv_mode: CvMode,
    document: SourceDocument,
    profile: CandidateProfile,
    jobs: JobRuntime,
    results: list[EligibilityResult],
    ranking: tuple[AdaptedRanking, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Everything the run produced, as JSON-ready data. `ranking` is the
    result of `rank_jobs`; without it the report's ranking is None."""
    return {
        "modes": {"cv_extraction": cv_mode.value, "job_extraction": jobs.mode.value},
        "inputs": {
            "cv_document_id": document.document_id,
            "cv_source_ref": document.source_ref,
            "cv_content_hash": document.content_hash,
            "snapshot_id": jobs.snapshot.snapshot_id,
            "job_count": len(jobs.jobs),
        },
        "candidate_profile": profile.model_dump(mode="json"),
        "jobs": [
            {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "extraction": None if job.extraction is None else job.extraction.model_dump(mode="json"),
                "facts": None if job.facts is None else job.facts.model_dump(mode="json"),
                "evidence": [ref.model_dump(mode="json") for ref in job.evidence],
            }
            for job in jobs.jobs
        ],
        "eligibility": [result.model_dump(mode="json") for result in results],
        "ranking": None if ranking is None else _ranking(*ranking),
    }


MODE_NOTES = {
    "live": "model called during this run",
    "cache": "recorded model output, cache key checked",
    "fixture": "handcrafted reply, NOT model output; proves plumbing, not quality",
    "snapshot": "no extraction; jobs carry no facts",
}


def _provenance(current_mode: str, receipt: dict[str, Any]) -> str:
    """How a result was produced. A cache hit says which mode originally
    produced the cached result, so a cached live result is not read as a live
    call during this run."""
    if current_mode == "cache":
        return f"current mode CACHE, cached result originally produced {receipt['mode'].upper()}"
    return f"current mode {receipt['mode'].upper()}"


def _quote(text: str, width: int) -> str:
    text = " ".join(text.split())
    return f'"{text if len(text) <= width else text[: width - 3] + "..."}"'


def render(report: dict[str, Any]) -> str:
    """The report as terminal text: every section, evidence quoted inline."""
    lines: list[str] = []
    out = lines.append
    modes, inputs = report["modes"], report["inputs"]
    profile = report["candidate_profile"]
    receipt = profile["provenance"]["extraction"]
    evidence = {ref["evidence_id"]: ref["quote"] for ref in profile["provenance"]["evidence"]}

    out("AI PIPELINE DEMO")
    out("=" * 78)
    for stage, mode in modes.items():
        out(f"  {stage:<16} {mode.upper():<9} {MODE_NOTES[mode]}")
    out(f"  CV provenance    {_provenance(modes['cv_extraction'], receipt)}")
    out(
        f"                   provider/model {receipt['provider']} / {receipt['model_id']}"
        f" | prompt {receipt['prompt_version']} | produced {receipt['produced_at']}"
    )
    out(f"  CV input         {inputs['cv_source_ref']} (sha256 {inputs['cv_content_hash'][:12]}...)")
    out(f"  Job snapshot     {inputs['snapshot_id']} ({inputs['job_count']} jobs)")

    out("")
    out("[1] CandidateProfile  (every fact cites a verbatim CV quote)")
    for field in ("education", "experience", "skills"):
        for fact in profile[field]:
            out(f"  {field:<10} {fact['value']}")
            for ref in fact["evidence_ids"]:
                out(f"             {ref}: {_quote(evidence[ref], 70)}")
    for answers in profile["eligibility_answers"].values():
        for answer in answers:
            out(f"  language   {answer['answer_key']} = {answer['value']} ({answer['state']})")
            for ref in answer["evidence_ids"]:
                out(f"             {ref}: {_quote(evidence[ref], 70)}")

    out("")
    out("[2] JobFacts  (hard constraints and the posting text behind them)")
    for job in report["jobs"]:
        out(f"  {job['job_id']}  {job['title']} ({job['company']})")
        facts = job["facts"]
        if facts is None:
            out("    no facts: this job mode runs no extraction")
            continue
        job_quotes = {ref["evidence_id"]: ref["quote"] for ref in job["evidence"]}
        counts = ", ".join(
            f"{len(facts[k])} {k}" for k in ("skills", "experience", "education", "requirements")
        )
        extraction = job["extraction"]
        out(
            f"    {counts} | {_provenance(modes['job_extraction'], extraction)}"
            f" | {extraction['provider']} / {extraction['model_id']}"
        )
        for req in facts["requirements"]:
            if req["classification"] == "hard_constraint":
                out(f"    HARD {req['constraint_id']}: {req['text']}")
                for ref in req["evidence_ids"]:
                    out(f"         {ref}: {_quote(job_quotes[ref], 64)}")

    out("")
    out("[3] Eligibility  (deterministic rules; not-applicable rules hidden)")
    for result in report["eligibility"]:
        out(f"  {result['job_id']:<24} {result['status'].upper()}")
        for outcome in result["outcomes"]:
            if outcome["status"] == RuleStatus.NOT_APPLICABLE.value:
                continue
            out(f"    {outcome['rule_id']:<18} {outcome['status']:<8} {outcome['reason']}")
            cited = outcome["candidate_evidence_ids"] + outcome["job_evidence_ids"]
            if cited:
                out(f"    {'':<18} evidence: {', '.join(cited)}")
        if result["missing_field_paths"]:
            out(f"    to clarify: {', '.join(result['missing_field_paths'])}")

    ranking = report["ranking"]
    if ranking is None:
        return "\n".join(lines)
    settings = ranking["settings"]
    weights = ", ".join(f"{name}={value}" for name, value in settings["weights"].items())
    out("")
    out("[4] Ranking  DEVELOPMENT DIAGNOSTIC")
    out("  WARNING: not the product demo ranking. Development weights and horizons;")
    out("  scores use only the active factors, so they are not a job recommendation.")
    out(f"  weights          {settings['weights_version']} ({weights})")
    out(
        f"  horizons         deadline {settings['deadline_horizon_days']} days, "
        f"freshness {settings['freshness_horizon_days']} days (development values)"
    )
    out(f"  clock            {settings['now']}")
    out(f"  active factors   {', '.join(ranking['active_factors']) or 'none'}")
    out(f"  missing factors  {', '.join(ranking['missing_factors']) or 'none'} (no value for any job)")
    for group in ("eligible", "uncertain"):
        out(f"  {group}:")
        if not ranking[group]:
            out("    none")
        for entry in ranking[group]:
            score = "unscored" if entry["score"] is None else f"{entry['score']:.3f}"
            rank = "-" if entry["rank"] is None else str(entry["rank"])
            factors = ", ".join(
                f"{name}={'n/a' if value is None else f'{value:.2f}'}"
                for name, value in entry["factors"].items()
            )
            effective = ", ".join(
                f"{name}={value:.2f}" for name, value in entry["effective_weights"].items()
            )
            out(f"    {rank:>2}. {score:<8} {entry['title']}")
            out(f"        {factors}")
            out(f"        effective weights: {effective or 'none'}")
    if ranking["excluded"]:
        out("  excluded:")
        for item in ranking["excluded"]:
            out(f"    {item['reason']:<10} {item['title']}")
    return "\n".join(lines)


# --- Command line -------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cv", type=Path, default=CV_PATH, help="CV file (.pdf or text)")
    parser.add_argument("--cv-mode", type=CvMode, choices=list(CvMode), default=CvMode.CACHE)
    parser.add_argument("--job-mode", type=JobMode, choices=list(JobMode), default=JobMode.CACHE)
    parser.add_argument(
        "--now", type=datetime.fromisoformat, help="Ranking clock, ISO 8601 with offset"
    )
    parser.add_argument("--json", type=Path, help="Also write the full report here")
    parser.add_argument(
        "--record-cv-cache",
        action="store_true",
        help=f"With --cv-mode live, save the profile to {CV_CACHE_PATH.name}",
    )
    parser.add_argument(
        "--include-ranking",
        action="store_true",
        help="Also run and print the ranking, labeled as a development diagnostic",
    )
    args = parser.parse_args(argv)
    if args.record_cv_cache and args.cv_mode is not CvMode.LIVE:
        parser.error("--record-cv-cache needs --cv-mode live")
    if args.now is not None and not args.include_ranking:
        parser.error("--now only sets the ranking clock; it needs --include-ranking")

    from dotenv import load_dotenv

    from oi.runtime.app_adapter import kimi_identity

    # KimiClient reads its key and model from the environment; a set variable wins.
    load_dotenv(ROOT / ".env")
    client = None
    if args.cv_mode is CvMode.LIVE or args.job_mode is JobMode.LIVE:
        from oi.providers.kimi import KimiClient

        client = KimiClient()
    identity = kimi_identity()

    document = load_cv(args.cv)
    try:
        profile = extract_cv(
            document,
            args.cv_mode,
            model_client=client if args.cv_mode is CvMode.LIVE else None,
            cache_model=identity if args.cv_mode is CvMode.CACHE else None,
        )
        jobs = load_jobs(
            args.job_mode,
            client if args.job_mode is JobMode.LIVE else None,
            cache_model=identity if args.job_mode is JobMode.CACHE else None,
        )
    except (StaleCacheError, ExtractionError) as error:
        # No fallback: the presenter picks another mode explicitly.
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    if args.record_cv_cache:
        CV_CACHE_PATH.write_text(profile.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"Recorded CV cache: {CV_CACHE_PATH}", file=sys.stderr)

    results = assess_jobs(profile, jobs)
    ranking = rank_jobs(profile, jobs, results, now=args.now) if args.include_ranking else None
    report = build_report(args.cv_mode, document, profile, jobs, results, ranking)
    print(render(report))
    if args.json:
        args.json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"\nFull report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
