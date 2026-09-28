"""The standalone AI pipeline demo: explicit modes, current cache, stable output,
ranking only as a labeled development diagnostic."""

import json
from pathlib import Path

import dotenv
import pytest

from examples.ai_pipeline_demo import run_demo as demo
from oi.contracts import ExtractionMode
from oi.providers.model_client import ExtractedFields
from oi.runtime.jobs import JobMode, ModelIdentity, StaleCacheError, load_jobs

#: Who recorded the committed CV and job caches.
KIMI_K3 = ModelIdentity("kimi", "moonshotai/kimi-k3")


@pytest.fixture
def no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep main() from loading the developer's .env into the test process."""
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("KIMI_MODEL", KIMI_K3.model_id)


def fixture_reply() -> ExtractedFields:
    return ExtractedFields.model_validate_json(demo.CV_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_committed_cv_cache_matches_the_synthetic_cv() -> None:
    """Demo-day guard: a prompt, schema or CV edit makes this fail until the
    cache is re-recorded live."""
    document = demo.load_cv(demo.CV_PATH)
    profile = demo.extract_cv(document, demo.CvMode.CACHE, cache_model=KIMI_K3)

    receipt = profile.provenance.extraction
    assert receipt.mode is ExtractionMode.LIVE
    assert receipt.input_hash == document.content_hash
    assert profile.skills and profile.education and profile.experience


def test_cv_cache_refuses_a_modified_cv(tmp_path: Path) -> None:
    modified = tmp_path / "synthetic_cv.txt"
    modified.write_text(demo.CV_PATH.read_text(encoding="utf-8") + "\nChess\n", encoding="utf-8")

    with pytest.raises(StaleCacheError, match="input hash"):
        demo.extract_cv(demo.load_cv(modified), demo.CvMode.CACHE, cache_model=KIMI_K3)


def test_cv_cache_refuses_another_model() -> None:
    document = demo.load_cv(demo.CV_PATH)
    with pytest.raises(StaleCacheError, match="model id"):
        demo.extract_cv(
            document, demo.CvMode.CACHE, cache_model=ModelIdentity("kimi", "other-model")
        )


def test_fixture_mode_runs_real_extraction_and_is_labeled_fixture() -> None:
    reply = fixture_reply()
    profile = demo.extract_cv(demo.load_cv(demo.CV_PATH), demo.CvMode.FIXTURE)

    receipt = profile.provenance.extraction
    assert receipt.mode is ExtractionMode.FIXTURE
    assert receipt.provider == "fixture"
    # Every handcrafted quote is in the CV, so nothing is dropped.
    assert len(profile.skills) == len(reply.skills)
    assert len(profile.experience) == len(reply.experience)
    assert len(profile.eligibility_answers["HC_LANGUAGE"]) == len(reply.languages)


def test_live_mode_uses_the_given_client_and_is_labeled_live() -> None:
    client = demo.FixtureModelClient(fixture_reply())
    profile = demo.extract_cv(demo.load_cv(demo.CV_PATH), demo.CvMode.LIVE, model_client=client)

    assert profile.provenance.extraction.mode is ExtractionMode.LIVE


def test_modes_refuse_missing_inputs() -> None:
    document = demo.load_cv(demo.CV_PATH)
    with pytest.raises(ValueError, match="model client"):
        demo.extract_cv(document, demo.CvMode.LIVE)
    with pytest.raises(ValueError, match="provider and model"):
        demo.extract_cv(document, demo.CvMode.CACHE)


def test_ranking_covers_every_job_and_names_its_factors() -> None:
    document = demo.load_cv(demo.CV_PATH)
    profile = demo.extract_cv(document, demo.CvMode.FIXTURE)
    jobs = load_jobs(JobMode.CACHE, cache_model=KIMI_K3)

    results = demo.assess_jobs(profile, jobs)
    ranking = demo.rank_jobs(profile, jobs, results)
    report = demo.build_report(demo.CvMode.FIXTURE, document, profile, jobs, results, ranking)

    job_ids = {job.job_id for job in jobs.jobs}
    assert {r["job_id"] for r in report["eligibility"]} == job_ids
    placed = [
        entry["job_id"]
        for group in ("eligible", "uncertain", "excluded")
        for entry in report["ranking"][group]
    ]
    assert sorted(placed) == sorted(job_ids)
    settings = report["ranking"]["settings"]
    assert settings["now"] == jobs.snapshot.created_at.isoformat()
    # Active and missing factors partition the configured factors.
    assert sorted(report["ranking"]["active_factors"] + report["ranking"]["missing_factors"]) == sorted(
        settings["factors"]
    )
    text = demo.render(report)
    assert "FIXTURE" in text
    assert "DEVELOPMENT DIAGNOSTIC" in text and "not the product demo ranking" in text


def test_default_run_is_cache_only_and_reproducible(
    no_dotenv: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    assert demo.main(["--json", str(first)]) == 0
    assert demo.main(["--json", str(second)]) == 0

    assert first.read_bytes() == second.read_bytes()
    report = json.loads(first.read_text(encoding="utf-8"))
    assert report["modes"] == {"cv_extraction": "cache", "job_extraction": "cache"}
    assert report["ranking"] is None
    out = capsys.readouterr().out
    assert "cv_extraction    CACHE" in out and "job_extraction   CACHE" in out
    # The cached receipt says LIVE; the output must not read as a live call now.
    assert "current mode CACHE, cached result originally produced LIVE" in out
    assert "Ranking" not in out


def test_ranking_is_printed_only_on_request(
    no_dotenv: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "report.json"

    assert demo.main(["--include-ranking", "--json", str(path)]) == 0

    ranking = json.loads(path.read_text(encoding="utf-8"))["ranking"]
    out = capsys.readouterr().out
    assert "[4] Ranking  DEVELOPMENT DIAGNOSTIC" in out
    assert f"active factors   {', '.join(ranking['active_factors'])}" in out
    assert f"missing factors  {', '.join(ranking['missing_factors'])}" in out
    assert ranking["settings"]["weights_version"] in out


def test_now_needs_include_ranking(no_dotenv: None) -> None:
    with pytest.raises(SystemExit):
        demo.main(["--now", "2026-09-24T00:00:00+00:00"])


def test_stale_cache_fails_without_fallback(
    no_dotenv: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    modified = tmp_path / "synthetic_cv.txt"
    modified.write_text("A different CV\n", encoding="utf-8")

    assert demo.main(["--cv", str(modified)]) == 1
    captured = capsys.readouterr()
    assert "StaleCacheError" in captured.err
    assert "AI PIPELINE DEMO" not in captured.out
