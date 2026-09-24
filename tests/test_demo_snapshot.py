"""A-04: the demo snapshot provider boundary."""

from __future__ import annotations

from pathlib import Path

from oi.contracts import JobSnapshot
from oi.io.demo_snapshot import get_demo_snapshot
from oi.io.snapshot import load_snapshot

ROOT = Path(__file__).resolve().parents[1]
BATCH01_SNAPSHOT = ROOT / "data" / "snapshots" / "greenhouse_batch01.json"


def test_get_demo_snapshot_returns_greenhouse_batch01() -> None:
    snapshot = get_demo_snapshot()

    assert isinstance(snapshot, JobSnapshot)
    assert snapshot.snapshot_id == "greenhouse-batch01"
    assert len(snapshot.jobs) == 8


def test_get_demo_snapshot_matches_direct_load_snapshot() -> None:
    assert get_demo_snapshot() == load_snapshot(BATCH01_SNAPSHOT)
