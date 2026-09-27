"""Provide the committed OI-50 synthetic job catalogue behind one call.

Loading only: delegates to `load_snapshot` with no transformation. The
catalogue is produced by `oi.io.synthetic_workbook` and reads nothing else.
"""

from __future__ import annotations

from pathlib import Path

from oi.contracts import JobSnapshot
from oi.io.snapshot import load_snapshot

_CATALOGUE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "snapshots"
    / "synthetic_oi50.json"
)


def get_synthetic_catalogue() -> JobSnapshot:
    """Load and validate the committed OI-50 synthetic job catalogue.

    Returns:
        The validated JobSnapshot of 50 synthetic jobs.

    Raises:
        OSError: If the catalogue file cannot be read.
        UnicodeDecodeError: If the file is not valid UTF-8.
        pydantic.ValidationError: If the file does not satisfy the snapshot
            contract.
    """
    return load_snapshot(_CATALOGUE_PATH)
