"""The job snapshot the app runs on, in one explicitly named job mode.

This module wires existing pieces together and decides nothing itself:
loading is `oi.io.snapshot`, extraction is `oi.intelligence.job_extraction`,
and eligibility/ranking consume the returned `JobRecord`s unchanged. It reads
no environment and builds no provider client; `oi.runtime.app_adapter` does
that for the app.

`JobMode` says where the jobs come from. It is not the contract's
`ExtractionMode`, which labels how one extraction result was produced and
reserves ``fixture`` for handcrafted synthetic data (PROJECT_CONTEXT, "Three
explicitly labeled execution modes"):

- ``snapshot``: the committed demo snapshot as ingested. No model output of
  any kind, so jobs carry no `facts` and nothing can pass for extraction.
- ``cache``: the committed enriched snapshot, reused only when every job's
  receipt matches its cache key -- the source description's content hash,
  the expected provider and model, the current job prompt version and the
  contract schema version. A stale entry raises; it is never served, and never
  replaced by another mode.
- ``live``: the source snapshot enriched by a model during this call.

The mode is always the caller's choice. A model client is required in
``live`` and refused otherwise, and the expected model is required in
``cache`` and refused otherwise, so no mode can call a model, or skip one,
behind the caller's back.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from oi.contracts import CONTRACT_VERSION, JobRecord, JobSnapshot
from oi.intelligence.job_extraction import enrich_snapshot
from oi.io.snapshot import load_snapshot
from oi.providers.model_client import ModelClient, load_job_prompt

_SNAPSHOTS = Path(__file__).resolve().parents[3] / "data" / "snapshots"
#: The committed Batch 01 snapshot, as ingested.
SOURCE_PATH = _SNAPSHOTS / "greenhouse_batch01.json"
#: Its enrichment, produced once by `python -m oi.intelligence.job_extraction`.
CACHE_PATH = _SNAPSHOTS / "greenhouse_batch01_enriched.json"


class JobMode(str, Enum):
    """Where the app's jobs come from; see the module docstring."""

    SNAPSHOT = "snapshot"
    CACHE = "cache"
    LIVE = "live"


class StaleCacheError(ValueError):
    """The cached enrichment does not match the source or the current key."""


@dataclass(frozen=True)
class ModelIdentity:
    """The provider and model a cached extraction must have been made with."""

    provider: str
    model_id: str


@dataclass(frozen=True)
class JobRuntime:
    """A job snapshot and the mode that produced it."""

    mode: JobMode
    snapshot: JobSnapshot

    @property
    def jobs(self) -> list[JobRecord]:
        """The jobs, in snapshot order, for eligibility and ranking."""
        return list(self.snapshot.jobs)


def parse_mode(value: str) -> JobMode:
    """The mode named by `value` ("snapshot", "cache" or "live").

    Raises:
        ValueError: If `value` names no mode.
    """
    try:
        return JobMode(value.strip().lower())
    except ValueError:
        names = ", ".join(m.value for m in JobMode)
        raise ValueError(f"Unknown job mode {value!r}; expected one of: {names}.") from None


def load_jobs(
    mode: JobMode,
    model_client: ModelClient | None = None,
    *,
    cache_model: ModelIdentity | None = None,
    source_path: Path = SOURCE_PATH,
    cache_path: Path = CACHE_PATH,
) -> JobRuntime:
    """Load the job snapshot in `mode`.

    Args:
        mode: The job mode; see the module docstring.
        model_client: The client for ``live`` mode. Required there, refused
            in the other modes.
        cache_model: The provider and model the cache must come from.
            Required in ``cache`` mode, refused in the other modes.
        source_path: The snapshot as ingested.
        cache_path: Its cached enrichment, read in ``cache`` mode only.

    Raises:
        ValueError: If `model_client` or `cache_model` is missing in the mode
            that needs it, or given in a mode that does not.
        StaleCacheError: In ``cache`` mode, if the cache does not match.
        ExtractionError: In ``live`` mode, propagated from the provider.
        OSError, pydantic.ValidationError: As for `load_snapshot`.
    """
    mode = JobMode(mode)
    if (model_client is None) == (mode is JobMode.LIVE):
        raise ValueError(
            "Live job mode needs a model client."
            if mode is JobMode.LIVE
            else f"{mode.value.capitalize()} job mode calls no model; got a model client."
        )
    if (cache_model is None) == (mode is JobMode.CACHE):
        raise ValueError(
            "Cache job mode needs the expected provider and model."
            if mode is JobMode.CACHE
            else f"{mode.value.capitalize()} job mode reads no cache; got a cache model."
        )

    source = load_snapshot(source_path)
    if mode is JobMode.SNAPSHOT:
        snapshot = source
    elif mode is JobMode.CACHE:
        snapshot = load_snapshot(cache_path)
        check_cache(source, snapshot, cache_model)
    else:
        snapshot = enrich_snapshot(source, model_client)
    return JobRuntime(mode=mode, snapshot=snapshot)


def check_cache(source: JobSnapshot, cached: JobSnapshot, model: ModelIdentity) -> None:
    """Check that `cached` is a current enrichment of `source` by `model`.

    Raises:
        StaleCacheError: If the snapshot or its jobs do not match `source`,
            or any job's receipt is missing or fails its cache key.
    """
    if cached.snapshot_id != f"{source.snapshot_id}-enriched":
        raise StaleCacheError(
            f"Cache '{cached.snapshot_id}' is not an enrichment of '{source.snapshot_id}'."
        )
    source_ids = [job.job_id for job in source.jobs]
    cached_ids = [job.job_id for job in cached.jobs]
    if cached_ids != source_ids:
        raise StaleCacheError(
            f"Cache '{cached.snapshot_id}' holds jobs {cached_ids}, source holds {source_ids}."
        )

    prompt_version = load_job_prompt().version
    for original, job in zip(source.jobs, cached.jobs):
        receipt = job.extraction
        if job.facts is None or receipt is None:
            raise StaleCacheError(f"Cached job '{job.job_id}' is not enriched.")
        key = {
            "input hash": (receipt.input_hash, original.description.content_hash),
            "provider": (receipt.provider, model.provider),
            "model id": (receipt.model_id, model.model_id),
            "prompt version": (receipt.prompt_version, prompt_version),
            "schema version": (receipt.schema_version, CONTRACT_VERSION),
        }
        for name, (cached_value, current) in key.items():
            if cached_value != current:
                raise StaleCacheError(
                    f"Cached job '{job.job_id}' has {name} {cached_value!r}, "
                    f"expected {current!r}."
                )
