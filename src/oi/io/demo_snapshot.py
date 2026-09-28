"""Provide the committed Greenhouse Batch 01 demo snapshot behind one call.

Loading only: delegates to `load_snapshot` with no transformation.
"""

from __future__ import annotations

from pathlib import Path

from oi.contracts import JobSnapshot
from oi.io.snapshot import load_snapshot

_DEMO_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "snapshots"
    / "greenhouse_batch01.json"
)


def get_demo_snapshot() -> JobSnapshot:
    """Load and validate the committed Greenhouse Batch 01 demo snapshot.

    Returns:
        The validated JobSnapshot.

    Raises:
        OSError: If the demo snapshot file cannot be read.
        UnicodeDecodeError: If the file is not valid UTF-8.
        pydantic.ValidationError: If the file does not satisfy the snapshot
            contract.
    """
    return load_snapshot(_DEMO_SNAPSHOT_PATH)
