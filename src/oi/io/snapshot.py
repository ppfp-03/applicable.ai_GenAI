"""Load a persisted job snapshot from disk.

Reading only: no fetching, no caching, no normalization and no mutation of
the stored snapshot.
"""

from __future__ import annotations

from pathlib import Path

from oi.contracts import JobSnapshot


def load_snapshot(path: Path) -> JobSnapshot:
    """Read one UTF-8 JSON snapshot file and validate it as a JobSnapshot.

    Args:
        path: Path to a file holding exactly one UTF-8 JSON snapshot object.

    Returns:
        The validated JobSnapshot.

    Raises:
        OSError: If the path cannot be read, including FileNotFoundError.
        UnicodeDecodeError: If the file is not valid UTF-8.
        pydantic.ValidationError: If the content is not valid JSON or does
            not satisfy the snapshot contract. Nothing is defaulted or
            repaired on the way through.
    """
    return JobSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
