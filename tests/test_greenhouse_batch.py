from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from oi.contracts import JobSnapshot
from oi.io import greenhouse_batch as batch_module
from oi.io.greenhouse import GreenhouseFetchError
from oi.io.greenhouse_batch import (
    FETCH_QUARANTINE_REASON,
    NORMALIZATION_QUARANTINE_REASON,
    DocumentRegistryConflictError,
    DuplicateTargetError,
    GreenhouseTarget,
    build_greenhouse_snapshot,
)

OBSERVED_AT = datetime(2026, 9, 22, 8, 0, tzinfo=timezone.utc)
BOARD = "examplebatchboard"


class UnexpectedBoundaryError(Exception):
    """Stands in for a programming failure that must not be quarantined."""


def shaped_payload(job_id: str, **overrides: Any) -> dict[str, Any]:
    """Network-free Greenhouse-shaped fixture, not a captured live response."""

    payload: dict[str, Any] = {
        "id": int(job_id),
        "internal_job_id": 900000 + int(job_id),
        "title": f"Analyst Programme {job_id}",
        "company_name": "Example Batch Employer",
        "first_published": "2026-09-04T09:15:00Z",
        "updated_at": "2026-09-10T13:20:00+00:00",
        "application_deadline": None,
        "location": {"name": "London"},
        "content": f"&lt;p&gt;Programme {job_id} description.&lt;/p&gt;",
        "absolute_url": (
            f"https://job-boards.greenhouse.io/{BOARD}/jobs/{job_id}"
        ),
        "language": "en",
    }
    payload.update(overrides)
    return payload


def endpoint(job_id: str, board_token: str = BOARD) -> str:
    return (
        f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
    )


def install_fetch(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[tuple[str, str], Any],
    *,
    calls: list[tuple[str, str]] | None = None,
) -> None:
    """Replace the single-job fetch boundary with a deterministic stub.

    A mapped value that is an exception instance is raised; otherwise it is
    returned as the decoded payload.
    """

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


def build(targets: Any, **kwargs: Any) -> JobSnapshot:
    return build_greenhouse_snapshot(
        targets,
        snapshot_id=kwargs.pop("snapshot_id", "greenhouse-batch-01"),
        observed_at=kwargs.pop("observed_at", OBSERVED_AT),
        **kwargs,
    )


def test_two_valid_targets_produce_one_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): shaped_payload("222"),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert snapshot.schema_version == "0.2.1-draft"
    assert snapshot.snapshot_id == "greenhouse-batch-01"
    assert snapshot.created_at == OBSERVED_AT
    assert [job.job_id for job in snapshot.jobs] == [
        "greenhouse:111",
        "greenhouse:222",
    ]
    assert len(snapshot.source_manifest) == 2
    assert snapshot.quarantine == []


def test_valid_target_survives_a_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): GreenhouseFetchError("unreachable"),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert [job.job_id for job in snapshot.jobs] == ["greenhouse:111"]
    assert len(snapshot.source_manifest) == 1
    assert [(entry.reason, entry.count) for entry in snapshot.quarantine] == [
        (FETCH_QUARANTINE_REASON, 1)
    ]


def test_valid_target_survives_a_normalization_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): shaped_payload("222", content="   "),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert [job.job_id for job in snapshot.jobs] == ["greenhouse:111"]
    assert len(snapshot.source_manifest) == 1
    assert [(entry.reason, entry.count) for entry in snapshot.quarantine] == [
        (NORMALIZATION_QUARANTINE_REASON, 1)
    ]


def test_two_fetch_failures_aggregate_into_one_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): GreenhouseFetchError("unreachable"),
            (BOARD, "222"): GreenhouseFetchError("http 404"),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert [(entry.reason, entry.count) for entry in snapshot.quarantine] == [
        (FETCH_QUARANTINE_REASON, 2)
    ]


def test_two_normalization_failures_aggregate_into_one_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111", content="   "),
            (BOARD, "222"): shaped_payload("222", title="  "),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert [(entry.reason, entry.count) for entry in snapshot.quarantine] == [
        (NORMALIZATION_QUARANTINE_REASON, 2)
    ]


def test_fetch_and_normalization_failures_stay_separate_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): GreenhouseFetchError("unreachable"),
            (BOARD, "222"): shaped_payload("222", content="   "),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert snapshot.jobs == []
    assert {(entry.reason, entry.count) for entry in snapshot.quarantine} == {
        (FETCH_QUARANTINE_REASON, 1),
        (NORMALIZATION_QUARANTINE_REASON, 1),
    }


def test_duplicate_target_is_rejected_before_any_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    install_fetch(
        monkeypatch,
        {(BOARD, "111"): shaped_payload("111")},
        calls=calls,
    )

    with pytest.raises(DuplicateTargetError):
        build([(BOARD, "111"), (BOARD, "111")])

    assert calls == []


def test_output_preserves_caller_input_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "333"): shaped_payload("333"),
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): shaped_payload("222"),
        },
    )

    snapshot = build(
        [
            GreenhouseTarget(board_token=BOARD, job_id="333"),
            GreenhouseTarget(board_token=BOARD, job_id="111"),
            GreenhouseTarget(board_token=BOARD, job_id="222"),
        ]
    )

    assert [job.job_id for job in snapshot.jobs] == [
        "greenhouse:333",
        "greenhouse:111",
        "greenhouse:222",
    ]
    assert [entry.source_ref for entry in snapshot.source_manifest] == [
        endpoint("333"),
        endpoint("111"),
        endpoint("222"),
    ]


def test_document_registry_is_complete_and_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): shaped_payload("222"),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    expected_ids: set[str] = set()
    for job in snapshot.jobs:
        expected_ids.add(job.description.document_id)
        expected_ids.update(
            document.document_id for document in job.source_documents
        )

    assert set(snapshot.documents) == expected_ids
    for document_id, document in snapshot.documents.items():
        assert document.document_id == document_id

    for job in snapshot.jobs:
        assert snapshot.documents[job.description.document_id] == job.description
        for document in job.source_documents:
            assert snapshot.documents[document.document_id] == document


def test_manifest_entries_match_the_exact_posting_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            ("other board", "222"): shaped_payload("222"),
        },
    )

    snapshot = build([(BOARD, "111"), ("other board", "222")])

    assert [entry.source_ref for entry in snapshot.source_manifest] == [
        endpoint("111"),
        endpoint("222", board_token="other%20board"),
    ]
    for entry in snapshot.source_manifest:
        assert entry.source == "greenhouse"
        assert entry.retrieved_at == OBSERVED_AT
        assert entry.record_count == 1
        assert entry.redistribution_allowed is None


def test_unexpected_exception_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): UnexpectedBoundaryError("boom"),
        },
    )

    with pytest.raises(UnexpectedBoundaryError):
        build([(BOARD, "111"), (BOARD, "222")])


def test_conflicting_duplicate_document_ids_fail_visibly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            ("board-a", "111"): shaped_payload("111"),
            ("board-b", "111"): shaped_payload(
                "111", content="&lt;p&gt;Different content.&lt;/p&gt;"
            ),
        },
    )

    with pytest.raises(DocumentRegistryConflictError):
        build([("board-a", "111"), ("board-b", "111")])


def test_all_targets_failing_returns_a_contract_valid_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): GreenhouseFetchError("unreachable"),
            (BOARD, "222"): GreenhouseFetchError("http 404"),
        },
    )

    snapshot = build([(BOARD, "111"), (BOARD, "222")])

    assert snapshot.jobs == []
    assert snapshot.documents == {}
    assert snapshot.source_manifest == []
    assert [(entry.reason, entry.count) for entry in snapshot.quarantine] == [
        (FETCH_QUARANTINE_REASON, 2)
    ]
    assert JobSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot


def test_mixed_success_snapshot_round_trips_through_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fetch(
        monkeypatch,
        {
            (BOARD, "111"): shaped_payload("111"),
            (BOARD, "222"): GreenhouseFetchError("unreachable"),
            (BOARD, "333"): shaped_payload("333", content="   "),
            (BOARD, "444"): shaped_payload("444"),
        },
    )

    snapshot = build(
        [(BOARD, "111"), (BOARD, "222"), (BOARD, "333"), (BOARD, "444")]
    )

    assert [job.job_id for job in snapshot.jobs] == [
        "greenhouse:111",
        "greenhouse:444",
    ]
    assert {(entry.reason, entry.count) for entry in snapshot.quarantine} == {
        (FETCH_QUARANTINE_REASON, 1),
        (NORMALIZATION_QUARANTINE_REASON, 1),
    }

    reparsed = JobSnapshot.model_validate_json(snapshot.model_dump_json())

    assert reparsed == snapshot


def test_whitespace_equivalent_duplicate_targets_are_rejected_before_any_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    install_fetch(
        monkeypatch,
        {(BOARD, "111"): shaped_payload("111")},
        calls=calls,
    )

    with pytest.raises(DuplicateTargetError):
        build([(BOARD, "111"), (f"  {BOARD} ", " 111 ")])

    assert calls == []


@pytest.mark.parametrize(
    ("target", "message"),
    [
        (("", "111"), "board_token must be non-empty"),
        (("   ", "111"), "board_token must be non-empty"),
        ((BOARD, ""), "job_id must be non-empty"),
        ((BOARD, "   "), "job_id must be non-empty"),
    ],
)
def test_empty_target_identifiers_are_rejected_before_any_fetch(
    monkeypatch: pytest.MonkeyPatch,
    target: tuple[str, str],
    message: str,
) -> None:
    calls: list[tuple[str, str]] = []
    install_fetch(
        monkeypatch,
        {(BOARD, "111"): shaped_payload("111")},
        calls=calls,
    )

    with pytest.raises(ValueError, match=message):
        build([(BOARD, "111"), target])

    assert calls == []


def test_naive_observed_at_is_rejected_before_any_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    install_fetch(
        monkeypatch,
        {(BOARD, "111"): shaped_payload("111")},
        calls=calls,
    )

    with pytest.raises(ValueError, match="observed_at must be timezone-aware"):
        build(
            [(BOARD, "111")],
            observed_at=datetime(2026, 9, 22, 8, 0),
        )

    assert calls == []
