"""The job runtime: explicit modes, no silent fallback, consumable output."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from oi.contracts import CandidateProfile, ExtractionMode, JobRecord, JobSnapshot
from oi.intelligence.eligibility import assess_eligibility, load_rule_catalogue
from oi.intelligence.extraction import extract_candidate
from oi.intelligence.ranking_adapter import rank_with_eligibility
from oi.io.demo_snapshot import get_demo_snapshot
from oi.io.greenhouse_batch import write_snapshot
from oi.io.pdf import extract_pdf_text
from oi.io.snapshot import load_snapshot
from oi.providers import kimi
from oi.runtime import app_adapter
from oi.runtime.jobs import (
    CACHE_PATH,
    JobMode,
    ModelIdentity,
    StaleCacheError,
    load_jobs,
    parse_mode,
)
from tests import test_candidate_extraction as cv
from tests.test_io import build_text_pdf
from tests.test_job_extraction import FakeModelClient, make_job

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "tests" / "fixtures" / "contracts" / "v0.2.0-draft" / "candidate_profile.json"

#: Who made the committed cache, and who the fake client says it is.
KIMI_K3 = ModelIdentity("kimi", "moonshotai/kimi-k3")
FAKE = ModelIdentity(FakeModelClient.provider_name, FakeModelClient.model_id)


def synthetic_job(job_id: str) -> JobRecord:
    """A not-yet-enriched job whose description document is its own."""
    raw = make_job(job_id).model_dump(mode="json")
    old_id = raw["description"]["document_id"]
    raw["description"]["document_id"] = f"job-doc-{job_id}"
    raw["source_documents"] = []
    raw["evidence"] = [
        {**ref, "document_id": f"job-doc-{job_id}"}
        for ref in raw["evidence"]
        if ref["document_id"] == old_id
    ]
    return JobRecord.model_validate(raw)


def synthetic_snapshot(tmp_path: Path) -> Path:
    """A two-job, not-yet-enriched snapshot on disk; returns its path."""
    jobs = [synthetic_job("1"), synthetic_job("2")]
    documents = {job.description.document_id: job.description for job in jobs}
    snapshot = JobSnapshot(
        schema_version="0.2.1-draft",
        snapshot_id="synthetic",
        created_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
        jobs=jobs,
        documents=documents,
        source_manifest=[],
        quarantine=[],
    )
    path = tmp_path / "synthetic.json"
    write_snapshot(snapshot, path)
    return path


def fresh_cache(tmp_path: Path, source: Path, **receipt_update) -> Path:
    """`source` enriched by a fake model, with receipts changed as given."""
    enriched = load_jobs(JobMode.LIVE, FakeModelClient(), source_path=source).snapshot
    raw = json.loads(enriched.model_dump_json())
    for job in raw["jobs"]:
        job["extraction"].update(receipt_update)
    path = tmp_path / "cache.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


@pytest.fixture
def app_env(monkeypatch):
    """A clean job environment for the adapter, and a fresh process cache."""
    for name in (app_adapter.MODE_ENV, "KIMI_MODEL", "KIMI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    app_adapter.app_jobs.cache_clear()
    yield monkeypatch
    app_adapter.app_jobs.cache_clear()


# --- mode selection -------------------------------------------------------


def test_job_mode_does_not_reuse_the_extraction_fixture_label() -> None:
    assert [m.value for m in JobMode] == ["snapshot", "cache", "live"]
    assert "fixture" in {m.value for m in ExtractionMode}  # the contract is unchanged


@pytest.mark.parametrize("value", ["snapshot", "cache", "live", " Cache "])
def test_parse_mode(value: str) -> None:
    assert parse_mode(value) is JobMode(value.strip().lower())


@pytest.mark.parametrize("value", ["", "fixture", "demo", "auto"])
def test_unknown_mode_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="Unknown job mode"):
        parse_mode(value)


def test_live_mode_needs_a_model_client() -> None:
    with pytest.raises(ValueError, match="needs a model client"):
        load_jobs(JobMode.LIVE)


def test_cache_mode_needs_the_expected_model() -> None:
    with pytest.raises(ValueError, match="needs the expected provider and model"):
        load_jobs(JobMode.CACHE)


@pytest.mark.parametrize("mode", [JobMode.SNAPSHOT, JobMode.CACHE])
def test_offline_modes_refuse_a_model_client(mode: JobMode) -> None:
    client = FakeModelClient()
    with pytest.raises(ValueError, match="calls no model"):
        load_jobs(mode, client, cache_model=KIMI_K3)
    assert client.calls == []


@pytest.mark.parametrize("mode", [JobMode.SNAPSHOT, JobMode.LIVE])
def test_other_modes_refuse_a_cache_model(mode: JobMode) -> None:
    client = FakeModelClient() if mode is JobMode.LIVE else None
    with pytest.raises(ValueError, match="reads no cache"):
        load_jobs(mode, client, cache_model=KIMI_K3)


# --- app adapter ----------------------------------------------------------


def test_adapter_defaults_to_the_demo_snapshot(app_env) -> None:
    assert app_adapter.configured_mode() is JobMode.SNAPSHOT
    assert app_adapter.app_jobs().mode is JobMode.SNAPSHOT


def test_adapter_refuses_an_unknown_mode(app_env) -> None:
    app_env.setenv(app_adapter.MODE_ENV, "fixture")
    with pytest.raises(ValueError, match="Unknown job mode"):
        app_adapter.app_jobs()


def test_adapter_checks_the_cache_against_kimi_without_a_key(app_env) -> None:
    app_env.setenv(app_adapter.MODE_ENV, "cache")
    assert app_adapter.kimi_identity() == ModelIdentity("kimi", kimi.DEFAULT_MODEL)
    assert app_adapter.app_jobs().mode is JobMode.CACHE


def test_adapter_refuses_a_cache_from_another_model(app_env) -> None:
    app_env.setenv(app_adapter.MODE_ENV, "cache")
    app_env.setenv("KIMI_MODEL", "moonshotai/another-model")
    with pytest.raises(StaleCacheError, match="model id"):
        app_adapter.app_jobs()


def test_adapter_live_mode_fails_loudly_without_credentials(app_env) -> None:
    app_env.setenv(app_adapter.MODE_ENV, "live")
    with pytest.raises(RuntimeError, match="KIMI_API_KEY"):
        app_adapter.app_jobs()


def test_ui_and_demo_store_do_not_import_the_runtime() -> None:
    for folder in ("core", "views", "ui"):
        for path in (ROOT / folder).glob("*.py"):
            assert "oi.runtime" not in path.read_text(encoding="utf-8"), path
    assert "oi.runtime" not in (ROOT / "app.py").read_text(encoding="utf-8")


# --- snapshot mode --------------------------------------------------------


def test_snapshot_mode_serves_the_demo_snapshot_as_ingested() -> None:
    loaded = load_jobs(JobMode.SNAPSHOT)
    assert loaded.mode is JobMode.SNAPSHOT
    assert loaded.snapshot == get_demo_snapshot()
    assert loaded.jobs and all(j.facts is None and j.extraction is None for j in loaded.jobs)


# --- cache mode -----------------------------------------------------------


def test_cache_mode_serves_the_committed_enrichment() -> None:
    loaded = load_jobs(JobMode.CACHE, cache_model=KIMI_K3)
    assert loaded.mode is JobMode.CACHE
    assert loaded.snapshot == load_snapshot(CACHE_PATH)
    assert [j.job_id for j in loaded.jobs] == [j.job_id for j in get_demo_snapshot().jobs]


def test_cache_mode_accepts_a_current_cache(tmp_path: Path) -> None:
    source = synthetic_snapshot(tmp_path)
    loaded = load_jobs(
        JobMode.CACHE, cache_model=FAKE, source_path=source, cache_path=fresh_cache(tmp_path, source)
    )
    assert loaded.mode is JobMode.CACHE
    assert all(job.facts is not None for job in loaded.jobs)


@pytest.mark.parametrize(
    ("update", "what"),
    [
        ({"input_hash": "changed"}, "input hash"),
        ({"provider": "other"}, "provider"),
        ({"model_id": "fake-model-2"}, "model id"),
        ({"prompt_version": "sha256:0000000000000000"}, "prompt version"),
        ({"schema_version": "0.1.0-draft"}, "schema version"),
    ],
)
def test_cache_mode_refuses_a_stale_key(tmp_path: Path, update: dict, what: str) -> None:
    source = synthetic_snapshot(tmp_path)
    cache = fresh_cache(tmp_path, source, **update)
    with pytest.raises(StaleCacheError, match=what):
        load_jobs(JobMode.CACHE, cache_model=FAKE, source_path=source, cache_path=cache)


def test_cache_mode_refuses_an_unrelated_snapshot(tmp_path: Path) -> None:
    with pytest.raises(StaleCacheError, match="not an enrichment"):
        load_jobs(JobMode.CACHE, cache_model=KIMI_K3, source_path=synthetic_snapshot(tmp_path))


def test_cache_mode_refuses_an_unenriched_cache(tmp_path: Path) -> None:
    source = synthetic_snapshot(tmp_path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    raw["snapshot_id"] = "synthetic-enriched"
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(StaleCacheError, match="not enriched"):
        load_jobs(JobMode.CACHE, cache_model=FAKE, source_path=source, cache_path=cache)


# --- live mode ------------------------------------------------------------


def test_live_mode_enriches_a_synthetic_snapshot(tmp_path: Path) -> None:
    client = FakeModelClient()
    loaded = load_jobs(JobMode.LIVE, client, source_path=synthetic_snapshot(tmp_path))

    assert loaded.mode is JobMode.LIVE
    assert loaded.snapshot.snapshot_id == "synthetic-enriched"
    assert len(client.calls) == 2
    for job in loaded.jobs:
        assert job.facts is not None and job.facts.requirements
        assert job.extraction.mode is ExtractionMode.LIVE
        assert job.extraction.model_id == client.model_id


def test_live_jobs_feed_eligibility_and_ranking(tmp_path: Path) -> None:
    loaded = load_jobs(JobMode.LIVE, FakeModelClient(), source_path=synthetic_snapshot(tmp_path))
    candidate = CandidateProfile.model_validate_json(CANDIDATE.read_text(encoding="utf-8"))
    catalogue = load_rule_catalogue()

    results = [assess_eligibility(candidate, job, catalogue) for job in loaded.jobs]
    ranked = rank_with_eligibility(
        candidate,
        loaded.jobs,
        results,
        weights={"profile_fit": 0.40, "preference_fit": 0.25, "deadline_urgency": 0.20, "freshness": 0.15},
        now=datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc),
        deadline_horizon_days=30,
        freshness_horizon_days=30,
    )

    assert set(ranked.eligibility) == {job.job_id for job in loaded.jobs}


# --- candidate extraction path -------------------------------------------


def test_cv_path_is_pdf_text_then_candidate_extraction() -> None:
    """The path onboarding runs: PDF bytes -> extract_pdf_text ->
    extract_candidate, receipted live against the uploaded file's hash."""
    pdf = build_text_pdf("Skills: Python")
    document = extract_pdf_text(pdf, "cv-test")
    client = cv.FakeModelClient(cv.make_fields(education=[], experience=[]))

    profile = extract_candidate(document, client)

    assert client.calls == [document.text]
    assert [s.value for s in profile.skills] == ["Python"]
    assert profile.provenance.extraction.mode is ExtractionMode.LIVE
    assert profile.provenance.extraction.input_hash == hashlib.sha256(pdf).hexdigest()
