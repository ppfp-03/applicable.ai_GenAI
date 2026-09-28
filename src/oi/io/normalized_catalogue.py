"""Provide the normalized synthetic demo catalogue behind one call.

Loading only: the files are produced by ``oi.io.synthetic_normalized`` from
the faithful OI-50 catalogue, which stays available, unchanged, through
``oi.io.synthetic_catalogue.get_synthetic_catalogue``. The two are separate
boundaries: nothing here reads or aliases the faithful loader.

The normalized catalogue is controlled synthetic demo data. It is complete
and comparable by construction, so it must never be used as held-out
evaluation data (``EVALUATION_USE``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from oi.contracts import JobSnapshot
from oi.intelligence.eligibility import JobParameterSet, RuleCatalogue, load_job_parameters, load_rule_catalogue
from oi.io.snapshot import load_snapshot

_ROOT = Path(__file__).resolve().parents[3]
_SNAPSHOT_PATH = _ROOT / "data" / "snapshots" / "synthetic_oi50_normalized.json"
_PROVENANCE_PATH = _ROOT / "data" / "snapshots" / "synthetic_oi50_normalized_provenance.json"
_PARAMETERS_PATH = _ROOT / "config" / "eligibility" / "job_parameters_normalized.json"
_RULES_PATH = _ROOT / "config" / "synthetic" / "oi50_normalization.json"

#: This catalogue's only permitted use: demo and development, never evaluation.
EVALUATION_USE = "excluded"
#: The provenance classes every normalized value carries.
CLASSES = ("SOURCE", "NORMALIZED", "SYNTHETIC_FILL")


@dataclass(frozen=True)
class ProfileInputs:
    """What profile fit may compare for one normalized job."""

    role_family: str
    skills: tuple[str, ...]
    degree_level: str
    #: Accepted fields of study; empty when any field is accepted.
    fields_of_study: tuple[str, ...]
    any_field: bool
    experience_months: int


@dataclass(frozen=True)
class NormalizedCatalogue:
    """The normalized jobs, their parameter layer and their provenance."""

    snapshot: JobSnapshot
    parameters: JobParameterSet
    rule_catalogue: RuleCatalogue
    provenance: Mapping[str, Any]

    def values(self, job_id: str) -> Mapping[str, Any]:
        """Every normalized value of one job, each with its class and rule."""
        return self.provenance["jobs"][job_id]["values"]

    def profile_inputs(self, job_id: str) -> ProfileInputs:
        values = self.values(job_id)
        fields = values["fields_of_study"]["value"]
        return ProfileInputs(
            role_family=values["role_family"]["value"],
            skills=tuple(item["value"] for item in values["skills"]),
            degree_level=values["degree_level"]["value"],
            fields_of_study=tuple(fields["fields"]),
            any_field=fields["any"],
            experience_months=values["experience_months"]["value"],
        )


def normalized_rule_catalogue() -> RuleCatalogue:
    """The canonical rule catalogue with the normalized layer's approved
    field-of-study additions. The canonical catalogue itself is unchanged."""
    additions = json.loads(_RULES_PATH.read_text(encoding="utf-8"))["field_of_study_additions"]
    data = load_rule_catalogue().model_dump(mode="json")
    for spec in data["constraints"]:
        for key in spec["answer_keys"]:
            if spec["constraint_id"] == "HC_FIELD_OF_STUDY" and key["answer_key"] == "field_of_study":
                key["allowed_values"] += [f for f in additions if f not in key["allowed_values"]]
    return RuleCatalogue.model_validate(data)


@lru_cache(maxsize=1)
def get_normalized_catalogue() -> NormalizedCatalogue:
    """Load and validate the committed normalized synthetic demo catalogue.

    Raises:
        OSError: If a file cannot be read.
        pydantic.ValidationError: If a file does not satisfy its contract.
        ValueError: If the files disagree on which jobs exist.
    """
    snapshot = load_snapshot(_SNAPSHOT_PATH)
    parameters = load_job_parameters(_PARAMETERS_PATH)
    provenance = json.loads(_PROVENANCE_PATH.read_text(encoding="utf-8"))
    ids = {job.job_id for job in snapshot.jobs}
    if set(provenance["jobs"]) != ids or not {e.job_id for e in parameters.entries} <= ids:
        raise ValueError("normalized snapshot, parameters and provenance name different jobs")
    if provenance["evaluation_use"] != EVALUATION_USE:
        raise ValueError("the normalized catalogue is never evaluation data")
    return NormalizedCatalogue(snapshot, parameters, normalized_rule_catalogue(),
                               MappingProxyType(provenance))
