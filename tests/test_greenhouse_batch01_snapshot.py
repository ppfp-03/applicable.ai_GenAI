"""A-03: the committed real Greenhouse Batch 01 snapshot and its config runner.

The artifact tests read the committed `data/snapshots/` file only. The runner
tests stub the single-job fetch boundary, so no test performs live HTTP.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from oi.contracts import JobSnapshot
from oi.io import greenhouse_batch as batch_module
from oi.io.greenhouse import GreenhouseFetchError
from oi.io.greenhouse_batch import (
    FETCH_QUARANTINE_REASON,
    NORMALIZATION_QUARANTINE_REASON,
    BatchConfigError,
    GreenhouseTarget,
    load_batch_config,
    main,
    run_greenhouse_batch,
)
from oi.io.snapshot import load_snapshot

ROOT = Path(__file__).resolve().parents[1]
BATCH01_CONFIG = ROOT / "config" / "greenhouse_batch01.json"
BATCH01_SNAPSHOT = ROOT / "data" / "snapshots" / "greenhouse_batch01.json"

APPROVED_BATCH01 = [
    ("charlesriverassociates", "5174914"),
    ("temus", "5390013008"),
    ("rothesaygraduates", "8784142002"),
    ("wppmedia", "5424219008"),
    ("aircallioinc", "4317640009"),
    ("solarisbank", "8805758002"),
    ("workwize", "4653315101"),
    ("point72", "8491128002"),
]

OBSERVED_AT = datetime(2026, 9, 23, 8, 0, tzinfo=timezone.utc)


def endpoint(board_token: str, job_id: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"


@pytest.fixture(scope="module")
def batch01() -> JobSnapshot:
    return load_snapshot(BATCH01_SNAPSHOT)


# --- Batch 01 configuration ------------------------------------------------


def test_batch01_config_lists_exactly_the_approved_targets_in_order() -> None:
    config = load_batch_config(BATCH01_CONFIG)

    assert config.snapshot_id == "greenhouse-batch01"
    assert config.targets == tuple(
        GreenhouseTarget(board_token=board, job_id=job)
        for board, job in APPROVED_BATCH01
    )


# --- committed Batch 01 snapshot artifact ------------------------------------


def test_batch01_snapshot_loads_all_eight_jobs_in_config_order(
    batch01: JobSnapshot,
) -> None:
    assert batch01.schema_version == "0.2.1-draft"
    assert batch01.snapshot_id == "greenhouse-batch01"
    assert batch01.quarantine == []
    assert [(job.source, job.source_job_id) for job in batch01.jobs] == [
        ("greenhouse", job_id) for _, job_id in APPROVED_BATCH01
    ]
    for job in batch01.jobs:
        assert job.schema_version == "0.2.0-draft"
        assert job.job_id == f"greenhouse:{job.source_job_id}"
        assert job.company.strip()
        assert job.title.strip()
        assert job.description.text.strip()


def test_batch01_snapshot_has_no_semantic_facts_or_extraction(
    batch01: JobSnapshot,
) -> None:
    for job in batch01.jobs:
        assert job.facts is None
        assert job.extraction is None


def test_batch01_snapshot_records_provenance_for_every_job(
    batch01: JobSnapshot,
) -> None:
    assert len(batch01.source_manifest) == len(batch01.jobs)

    for (board, job_id), job, entry in zip(
        APPROVED_BATCH01, batch01.jobs, batch01.source_manifest, strict=True
    ):
        expected_endpoint = endpoint(board, job_id)
        assert entry.source == "greenhouse"
        assert entry.source_ref == expected_endpoint
        assert entry.retrieved_at == batch01.created_at
        assert entry.record_count == 1
        assert entry.redistribution_allowed is None

        assert job.first_seen_at == batch01.created_at
        assert job.last_seen_at == batch01.created_at
        assert job.url.startswith("https://")

        documents = [job.description, *job.source_documents]
        assert [document.kind.value for document in documents] == [
            "job",
            "ats_metadata",
        ]
        for document in documents:
            assert document.source_ref == expected_endpoint
            assert batch01.documents[document.document_id] == document

        metadata = json.loads(job.source_documents[0].text)
        assert str(metadata["id"]) == job_id

        embedded_ids = {document.document_id for document in documents}
        for evidence in job.evidence:
            assert evidence.document_id in embedded_ids

    assert len(batch01.documents) == 2 * len(batch01.jobs)


def test_batch01_snapshot_round_trips_through_json(batch01: JobSnapshot) -> None:
    serialized = batch01.model_dump_json()

    assert JobSnapshot.model_validate_json(serialized) == batch01


def test_batch01_snapshot_file_matches_the_writer_serialization(
    batch01: JobSnapshot,
) -> None:
    assert BATCH01_SNAPSHOT.read_text(encoding="utf-8") == (
        batch01.model_dump_json(indent=2) + "\n"
    )


# --- config loader failure handling ------------------------------------------


def write_config(tmp_path: Path, content: Any) -> Path:
    path = tmp_path / "batch.json"
    text = content if isinstance(content, str) else json.dumps(content)
    path.write_text(text, encoding="utf-8")
    return path


VALID_TARGET = {"board_token": "exampleboard", "job_id": "101"}


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("{not json", id="malformed-json"),
        pytest.param([VALID_TARGET], id="not-an-object"),
        pytest.param({"targets": [VALID_TARGET]}, id="missing-snapshot-id"),
        pytest.param({"snapshot_id": "s"}, id="missing-targets"),
        pytest.param(
            {"snapshot_id": "s", "targets": [VALID_TARGET], "extra": 1},
            id="unknown-field",
        ),
        pytest.param(
            {"snapshot_id": "  ", "targets": [VALID_TARGET]}, id="blank-id"
        ),
        pytest.param(
            {"snapshot_id": 7, "targets": [VALID_TARGET]}, id="non-str-id"
        ),
        pytest.param({"snapshot_id": "s", "targets": []}, id="empty-targets"),
        pytest.param(
            {"snapshot_id": "s", "targets": ["exampleboard/101"]}, id="bad-target"
        ),
        pytest.param(
            {"snapshot_id": "s", "targets": [{"board_token": "exampleboard"}]},
            id="target-missing-job-id",
        ),
        pytest.param(
            {"snapshot_id": "s", "targets": [{**VALID_TARGET, "note": "x"}]},
            id="target-unknown-field",
        ),
        pytest.param(
            {"snapshot_id": "s", "targets": [{"board_token": "b", "job_id": 101}]},
            id="non-str-job-id",
        ),
        pytest.param(
            {"snapshot_id": "s", "targets": [{"board_token": " ", "job_id": "1"}]},
            id="blank-board-token",
        ),
        pytest.param(
            {
                "snapshot_id": "s",
                "targets": [
                    VALID_TARGET,
                    {"board_token": " exampleboard", "job_id": "101 "},
                ],
            },
            id="duplicate-target",
        ),
    ],
)
def test_load_batch_config_rejects_unusable_config(
    tmp_path: Path, content: Any
) -> None:
    with pytest.raises(BatchConfigError):
        load_batch_config(write_config(tmp_path, content))


def test_load_batch_config_raises_for_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_batch_config(tmp_path / "missing.json")


# --- runner failure handling (network-free) ----------------------------------


def shaped_payload(job_id: str, **overrides: Any) -> dict[str, Any]:
    """Network-free Greenhouse-shaped fixture, not a captured live response."""

    payload: dict[str, Any] = {
        "id": int(job_id),
        "title": f"Analyst Programme {job_id}",
        "company_name": "Example Batch Employer",
        "first_published": "2026-09-04T09:15:00Z",
        "updated_at": "2026-09-10T13:20:00+00:00",
        "application_deadline": None,
        "location": {"name": "London"},
        "content": f"&lt;p&gt;Programme {job_id} description.&lt;/p&gt;",
        "absolute_url": f"https://job-boards.greenhouse.io/exampleboard/jobs/{job_id}",
    }
    payload.update(overrides)
    return payload


def install_fetch(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[tuple[str, str], Any],
    calls: list[tuple[str, str]] | None = None,
) -> None:
    def fake_fetch(
        board_token: str, job_id: str, *, timeout_s: float = 15.0
    ) -> dict[str, Any]:
        del timeout_s
        if calls is not None:
            calls.append((board_token, job_id))
        outcome = responses[(board_token, job_id)]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(batch_module, "fetch_greenhouse_job", fake_fetch)


THREE_TARGETS = {
    "snapshot_id": "example-batch",
    "targets": [
        {"board_token": "exampleboard", "job_id": "101"},
        {"board_token": "exampleboard", "job_id": "102"},
        {"board_token": "exampleboard", "job_id": "103"},
    ],
}


def test_run_writes_partial_snapshot_with_explicit_quarantine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fetch(
        monkeypatch,
        {
            ("exampleboard", "101"): shaped_payload("101"),
            ("exampleboard", "102"): GreenhouseFetchError("HTTP 404"),
            ("exampleboard", "103"): shaped_payload("103", content="   "),
        },
    )
    output = tmp_path / "snapshots" / "example.json"

    returned = run_greenhouse_batch(
        write_config(tmp_path, THREE_TARGETS), output, observed_at=OBSERVED_AT
    )

    persisted = load_snapshot(output)
    assert persisted == returned
    assert [job.source_job_id for job in persisted.jobs] == ["101"]
    assert [entry.source_ref for entry in persisted.source_manifest] == [
        endpoint("exampleboard", "101")
    ]
    assert [(q.reason, q.count) for q in persisted.quarantine] == [
        (FETCH_QUARANTINE_REASON, 1),
        (NORMALIZATION_QUARANTINE_REASON, 1),
    ]


def test_run_writes_zero_job_snapshot_when_every_target_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fetch(
        monkeypatch,
        {
            ("exampleboard", job_id): GreenhouseFetchError("timeout")
            for job_id in ("101", "102", "103")
        },
    )
    output = tmp_path / "example.json"

    run_greenhouse_batch(
        write_config(tmp_path, THREE_TARGETS), output, observed_at=OBSERVED_AT
    )

    persisted = load_snapshot(output)
    assert persisted.jobs == []
    assert persisted.documents == {}
    assert persisted.source_manifest == []
    assert [(q.reason, q.count) for q in persisted.quarantine] == [
        (FETCH_QUARANTINE_REASON, 3)
    ]


def test_run_rejects_bad_config_before_fetch_and_keeps_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    install_fetch(monkeypatch, {}, calls)
    output = tmp_path / "example.json"
    output.write_text("previous snapshot", encoding="utf-8")
    config = write_config(
        tmp_path,
        {"snapshot_id": "s", "targets": [VALID_TARGET, VALID_TARGET]},
    )

    with pytest.raises(BatchConfigError):
        run_greenhouse_batch(config, output, observed_at=OBSERVED_AT)

    assert calls == []
    assert output.read_text(encoding="utf-8") == "previous snapshot"


def test_run_propagates_unexpected_failure_and_keeps_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fetch(
        monkeypatch,
        {
            ("exampleboard", "101"): shaped_payload("101"),
            ("exampleboard", "102"): KeyError("programming error"),
            ("exampleboard", "103"): shaped_payload("103"),
        },
    )
    output = tmp_path / "example.json"
    output.write_text("previous snapshot", encoding="utf-8")

    with pytest.raises(KeyError):
        run_greenhouse_batch(
            write_config(tmp_path, THREE_TARGETS), output, observed_at=OBSERVED_AT
        )

    assert output.read_text(encoding="utf-8") == "previous snapshot"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "batch.json",
        "example.json",
    ]


def test_run_rejects_naive_observed_at_before_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    install_fetch(monkeypatch, {}, calls)

    with pytest.raises(ValueError, match="timezone-aware"):
        run_greenhouse_batch(
            write_config(tmp_path, THREE_TARGETS),
            tmp_path / "example.json",
            observed_at=datetime(2026, 9, 23, 8, 0),
        )

    assert calls == []
    assert not (tmp_path / "example.json").exists()


def test_main_reports_counts_and_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_fetch(
        monkeypatch,
        {
            ("exampleboard", "101"): shaped_payload("101"),
            ("exampleboard", "102"): shaped_payload("102"),
            ("exampleboard", "103"): GreenhouseFetchError("HTTP 404"),
        },
    )
    output = tmp_path / "example.json"

    exit_code = main(
        [
            "--config",
            str(write_config(tmp_path, THREE_TARGETS)),
            "--output",
            str(output),
            "--observed-at",
            "2026-09-23T08:00:00Z",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "example-batch: ingested 2/3 postings" in captured.out
    assert f"quarantined 1 posting(s): {FETCH_QUARANTINE_REASON}" in captured.err
    assert load_snapshot(output).created_at == OBSERVED_AT


def test_main_rejects_naive_observed_at(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--config",
                str(write_config(tmp_path, THREE_TARGETS)),
                "--output",
                str(tmp_path / "example.json"),
                "--observed-at",
                "2026-09-23T08:00:00",
            ]
        )
