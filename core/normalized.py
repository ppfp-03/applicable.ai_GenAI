"""The normalized synthetic demo jobs, checked and scored for one candidate.

An adapter that decides nothing itself: eligibility is the canonical engine
with the normalized parameter layer, profile fit is
``oi.intelligence.profile_fit``, and ranking is the production pipeline
(``rank_with_eligibility``) with the normalized-demo configuration passed
explicitly. Production defaults are not changed.

Preferences come only from what the candidate stated: the profile's
``preferred_cities`` (mapped to country codes) and the role families they
confirmed in Fine-tune (mapped to the ten normalized role families).
Industry is never used. What cannot be mapped is dropped, never guessed.

No UI groups jobs by catalogue: this module returns the ranking and each
job's factor breakdown, and the screens decide how to show them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence

from core import eligibility
from oi.contracts import CandidatePreferences, CandidateProfile
from oi.intelligence.eligibility import EligibilityResult, assess_eligibility
from oi.intelligence.profile_fit import (
    CandidateFacts,
    JobProfile,
    ProfileFit,
    candidate_facts,
    load_skills_vocabulary,
    profile_fit,
)
from oi.intelligence.ranking import PipelineEntry
from oi.intelligence.ranking_adapter import AdaptedRanking, rank_with_eligibility
from oi.io.normalized_catalogue import NormalizedCatalogue, get_normalized_catalogue

_ROOT = Path(__file__).resolve().parents[1]

#: Approved normalized-demo configuration (not production defaults).
WEIGHTS = MappingProxyType({"profile_fit": 0.40, "preference_fit": 0.25,
                            "deadline_urgency": 0.20, "freshness": 0.15})
DEADLINE_HORIZON_DAYS = 240
FRESHNESS_HORIZON_DAYS = 30

#: Approved mapping of the demo's role-family labels to the normalized ones.
#: A label that is itself a normalized family maps to itself.
ROLE_FAMILY_MAP = MappingProxyType({
    "Consulting": "Strategy & Consulting",
    "Strategy": "Strategy & Consulting",
    "Product management": "Product",
    "Product analytics": "Data & Analytics",
    "Growth": "Sales & Business Development",
    "Finance": "Finance & Investment",
    "Marketing": "Marketing & Communications",
    "Operations": "Operations & Supply Chain",
    "Sales": "Sales & Business Development",
    "Audit": "Risk & Compliance",
    "User research": "Product",
})
#: Fine-tune levels that express a preference; "none" does not.
PREFERRING_LEVELS = ("must", "important", "nice")


@lru_cache(maxsize=1)
def _rules() -> Mapping[str, Any]:
    return json.loads((_ROOT / "config" / "synthetic" / "oi50_normalization.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def city_countries() -> Mapping[str, str]:
    """City -> country code, from the demo's own roles (each city has one
    country there), restricted to the approved markets."""
    markets = {m["code"] for m in json.loads((_ROOT / "config" / "markets.json").read_text(encoding="utf-8"))["countries"]}
    pairs: dict[str, set[str]] = {}
    for role in json.loads((_ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["roles"]:
        pairs.setdefault(role["city"], set()).add(role["country"])
    return MappingProxyType({city: next(iter(codes)) for city, codes in pairs.items()
                             if len(codes) == 1 and next(iter(codes)) in markets})


#: Where the demo persona's own skills are defined (data/demo.json).
PERSONA_SKILLS_SECTION = "skills"


@lru_cache(maxsize=1)
def persona_skills() -> tuple[str, ...]:
    """The skills data/demo.json defines for the demo persona (its "Skills"
    profile section), in order. Demo data: never a default for anyone else."""
    sections = json.loads((_ROOT / "data" / "demo.json").read_text(encoding="utf-8"))["profile_sections"]
    (section,) = [s for s in sections if s["id"] == PERSONA_SKILLS_SECTION]
    return tuple(part.strip() for part in section["v1"].split(",") if part.strip())


@dataclass(frozen=True)
class SkillRecords:
    """The skill records profile fit reads for the demo persona, and their source."""

    texts: tuple[str, ...]
    source: str  # "cv" or "demo_persona"


def demo_persona_skills(cv: Optional[CandidateProfile]) -> SkillRecords:
    """The demo persona's skill records: the extracted CV's when it states any,
    else the persona's own skills from data/demo.json. The two are never
    merged. Demo persona only: for any other candidate, pass its own skill
    records to `rank` and nothing else.
    """
    if cv is not None and cv.skills:
        return SkillRecords(tuple(s.value for s in cv.skills), "cv")
    return SkillRecords(persona_skills(), "demo_persona")


def role_family(label: str) -> Optional[str]:
    """The normalized role family for a demo label, or None if none is approved."""
    if label in _rules()["role_families"]:
        return label
    return ROLE_FAMILY_MAP.get(label)


@dataclass(frozen=True)
class MappedPreferences:
    """The candidate's preferences as the ranking reads them, and what was dropped."""

    preferences: CandidatePreferences
    unmapped_cities: tuple[str, ...]
    unmapped_role_families: tuple[str, ...]


def map_preferences(preferred_cities: Sequence[str], confirmed: Optional[Sequence[Mapping]]) -> MappedPreferences:
    """Explicit preferences only: cities as country codes, confirmed role
    families as normalized ones. Industry and work-mode rows are ignored.

    Args:
        preferred_cities: The cities the candidate asked for.
        confirmed: The Fine-tune rows the candidate confirmed ({"field",
            "values", "level"}), or None before they confirm any.
    """
    countries: list[str] = []
    unmapped_cities: list[str] = []
    for city in preferred_cities:
        code = city_countries().get(city)
        if code is None:
            unmapped_cities.append(city)
        elif code not in countries:
            countries.append(code)
    families: list[str] = []
    unmapped_families: list[str] = []
    for row in confirmed or ():
        if row.get("field") != "role_family" or row.get("level") not in PREFERRING_LEVELS:
            continue
        for label in row["values"]:
            family = role_family(label)
            if family is None:
                unmapped_families.append(label)
            elif family not in families:
                families.append(family)
    prefs = CandidatePreferences(allowed_country_codes=None, preferred_country_codes=countries,
                                 preferred_role_families=families, preferred_industries=[])
    return MappedPreferences(prefs, tuple(unmapped_cities), tuple(unmapped_families))


def with_preferences(candidate: CandidateProfile, preferences: CandidatePreferences) -> CandidateProfile:
    """`candidate` with its preferences replaced; nothing else changes."""
    data = candidate.model_dump(mode="json")
    data["preferences"] = preferences.model_dump(mode="json")
    return CandidateProfile.model_validate(data)


def job_profile(catalogue: NormalizedCatalogue, job_id: str) -> JobProfile:
    inputs = catalogue.profile_inputs(job_id)
    return JobProfile(inputs.skills, inputs.degree_level, inputs.fields_of_study,
                      inputs.any_field, inputs.experience_months)


@dataclass(frozen=True)
class NormalizedRanking:
    """One run over the normalized jobs: eligibility, profile fit and ranking."""

    ranked: AdaptedRanking
    profile_fits: Mapping[str, ProfileFit]
    facts: CandidateFacts

    def result(self, job_id: str) -> EligibilityResult:
        return self.ranked.eligibility[job_id]

    def entries(self) -> list[PipelineEntry]:
        """Every scored or unscored (not excluded) job, eligible then uncertain."""
        p = self.ranked.pipeline
        return [e for g in (p.eligible, p.uncertain) for e in (*g.top, *g.rest, *g.unscored)]


def rank(candidate: CandidateProfile, now: datetime, skill_texts: Optional[Sequence[str]] = None,
         catalogue: Optional[NormalizedCatalogue] = None) -> NormalizedRanking:
    """Check and rank every normalized job for `candidate`.

    Args:
        candidate: The canonical candidate, preferences included.
        now: A timezone-aware time (the demo clock).
        skill_texts: The candidate's skill records when they are held outside
            `candidate` (the extracted CV's); default ``candidate.skills``.
        catalogue: The normalized catalogue; default the committed one.
    """
    cat = catalogue or get_normalized_catalogue()
    facts = candidate_facts(candidate, load_skills_vocabulary(), skill_texts)
    jobs = list(cat.snapshot.jobs)
    results = [assess_eligibility(candidate, job, cat.rule_catalogue, job_parameters=cat.parameters)
               for job in jobs]
    fits = {job.job_id: profile_fit(facts, job_profile(cat, job.job_id)) for job in jobs}
    ranked = rank_with_eligibility(
        candidate, jobs, results,
        weights=WEIGHTS,
        now=now,
        deadline_horizon_days=DEADLINE_HORIZON_DAYS,
        freshness_horizon_days=FRESHNESS_HORIZON_DAYS,
        profile_fit={job_id: None if fit.score is None else fit.score / 100 for job_id, fit in fits.items()},
    )
    return NormalizedRanking(ranked, MappingProxyType(fits), facts)


def demo_candidate(profile: Mapping[str, Any], answers: Mapping[str, Any],
                   confirmed: Optional[Sequence[Mapping]]) -> CandidateProfile:
    """The demo candidate (``core.eligibility.candidate``) with its explicit
    preferences: the profile's preferred cities and the confirmed role families."""
    mapped = map_preferences(profile.get("preferred_cities", []), confirmed)
    return with_preferences(eligibility.candidate(profile, answers), mapped.preferences)
