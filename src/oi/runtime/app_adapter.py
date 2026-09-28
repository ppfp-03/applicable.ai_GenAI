"""The one place the app gets its jobs from `oi.runtime.jobs`.

Everything app-specific about running the job runtime lives here and nowhere
else: which mode the process runs in (APPLICABLE_JOB_MODE), which provider
and model a cache must come from, building the live client, and loading once
per process. `oi.runtime.jobs` stays free of environment and provider
details, and nothing in the UI or the demo store imports it.

KimiClient reads its credentials and model from the environment; load any
.env file before the first call.
"""

from __future__ import annotations

import os
from functools import lru_cache

from oi.runtime.jobs import JobMode, JobRuntime, ModelIdentity, load_jobs, parse_mode

#: Environment variable naming the job mode the app runs in.
MODE_ENV = "APPLICABLE_JOB_MODE"
#: The mode used when MODE_ENV is unset: the demo snapshot, no model involved.
DEFAULT_MODE = JobMode.SNAPSHOT


def configured_mode() -> JobMode:
    """The mode MODE_ENV names, or DEFAULT_MODE when it is unset.

    Raises:
        ValueError: If MODE_ENV is set to something that names no mode.
    """
    value = os.environ.get(MODE_ENV)
    return DEFAULT_MODE if value is None else parse_mode(value)


def kimi_identity() -> ModelIdentity:
    """The provider and model KimiClient would call, without building one
    (which needs an API key a cache read does not)."""
    from oi.providers.kimi import DEFAULT_MODEL, KimiClient

    return ModelIdentity(KimiClient.provider_name, os.environ.get("KIMI_MODEL") or DEFAULT_MODEL)


@lru_cache(maxsize=1)
def app_jobs() -> JobRuntime:
    """The app's jobs and their mode, loaded once per process.

    Loading is lazy: ``live`` mode calls the model here, on first use, not at
    start-up.

    Raises:
        ValueError: If MODE_ENV names no mode.
        RuntimeError: In ``live`` mode, if KimiClient cannot be built.
        And anything `load_jobs` raises; nothing falls back to another mode.
    """
    mode = configured_mode()
    if mode is JobMode.LIVE:
        from oi.providers.kimi import KimiClient

        return load_jobs(mode, KimiClient())
    if mode is JobMode.CACHE:
        return load_jobs(mode, cache_model=kimi_identity())
    return load_jobs(mode)
