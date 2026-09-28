"""The one ranked Matches population: curated roles and synthetic postings together.

Every opportunity is checked by the canonical eligibility engine and scored by
the production ranking pipeline, in one `rank_with_eligibility` call, with the
D-051 configuration (core.normalized): profile fit 40%, preference fit 25%,
deadline urgency 20%, freshness 15%; profile fit 50/25/25 from facts. Where
an opportunity comes from never selects a formula.

The population (D-051 clarification): the curated demo roles plus the
normalized synthetic postings, each posting once. A curated role that copies a
normalized posting (same `source_job_id`) is represented by the normalized
posting; the curated fixture itself is untouched and still serves onboarding.

Curated roles get their ranking inputs from their own data, read the way the
rest of the app reads it:

- eligibility, experience months (one internship = one month), degree level
  and accepted fields: the eligibility bridge (core.eligibility);
- stated skills from the role description, topped up to 4-6 from the same
  role-family skill lists as the normalized postings when fewer than four are
  stated. Top-ups are ranking inputs only, never shown as posting facts;
- role family through the D-051 mapping, location from the role;
- deadline = `closes` (23:59 UTC), freshness = `found` as simulated
  first-seen. `posted_days_ago` is never used.

Ordering: a job to verify sorts 15 points below its raw Priority score; the
raw score and the four factors are never changed. Excluded jobs are not ordered.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from core import eligibility, normalized
from oi.contracts import CandidateProfile, JobRecord
from oi.intelligence.eligibility import EligibilityResult, assess_eligibility
from oi.intelligence.profile_fit import (
    JobProfile,
    ProfileFit,
    candidate_facts,
    load_skills_vocabulary,
    profile_fit,
    skill_named,
)
from oi.intelligence.ranking import PipelineEntry
from oi.intelligence.ranking_adapter import AdaptedRanking, rank_with_eligibility
from oi.io.normalized_catalogue import get_normalized_catalogue

_ROOT = Path(__file__).resolve().parents[1]

#: The approved weights (D-051), for the screens that show weighted points.
WEIGHTS = normalized.WEIGHTS
#: Points a job to verify sorts below its raw Priority score (ordering only).
VERIFY_ADJUSTMENT = 15.0

CURATED, SYNTHETIC = "curated", "synthetic"
#: The four factors, in display order, and their names.
FACTORS = ("profile_fit", "preference_fit", "deadline_urgency", "freshness")
FACTOR_NAMES = {"profile_fit": "Profile fit", "preference_fit": "Preference fit",
                "deadline_urgency": "Deadline urgency", "freshness": "Freshness"}


@lru_cache(maxsize=1)
def _rules() -> Mapping[str, Any]:
    return json.loads((_ROOT / "config" / "synthetic" / "oi50_normalization.json").read_text(encoding="utf-8"))


def _seed(name: str, key: str) -> int:
    return int(hashlib.sha256(f"{name}:{key}".encode()).hexdigest(), 16)


def stated_skills(role: Mapping[str, Any]) -> tuple[str, ...]:
    """The vocabulary skills the role's description states, in order."""
    vocab = load_skills_vocabulary()
    out: list[str] = []
    for q in (role.get("description") or {}).get("requirements", []):
        if q.get("kind") != "skill" or not q.get("value"):
            continue
        out += [s for s in vocab if skill_named(s, [q["value"]]) and s not in out]
    return tuple(out)


def ranking_skills(role: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(stated, topped up) ranking skills for a curated role.

    Stated skills come first. Fewer than four are topped up, deterministically
    by role ID, to 4-6 from the role family's skill list (the same lists the
    normalized postings use). The top-ups are ranking inputs, not posting facts.
    """
    stated = stated_skills(role)
    low, high = _rules()["skill_count"]["min"], _rules()["skill_count"]["max"]
    if len(stated) >= low:
        return stated[:high], ()
    family = normalized.role_family(role["role_family"])
    pool = list(_rules()["role_family_skills"][family])
    target = low + _seed("skill_count", role["id"]) % (high - low + 1)
    start = _seed("skill_pool", role["id"]) % len(pool)
    added: list[str] = []
    for skill in pool[start:] + pool[:start]:
        if len(stated) + len(added) >= target:
            break
        if skill not in stated and skill not in added:
            added.append(skill)
    return stated, tuple(added)


def curated_profile(role: Mapping[str, Any], profile: Mapping[str, Any]) -> JobProfile:
    """What profile fit reads about a curated role: the bridge's parameters
    for degree, fields and experience, and the ranking skills."""
    params = {e.constraint_id: e.parameters for e in eligibility.parameters(role, profile).entries}
    degree = params.get(eligibility.DEGREE)
    field = params.get(eligibility.FIELD)
    experience = params.get(eligibility.EXPERIENCE)
    stated, added = ranking_skills(role)
    return JobProfile(
        skills=stated + added,
        # Every curated role states a degree level; without one, any degree is compatible.
        degree_level=degree.min_level if degree else "bachelor",
        fields_of_study=tuple(field.accepted) if field else (),
        any_field=field is None,
        experience_months=experience.min_months if experience and experience.min_months else 0,
    )


def _day(value: str, at: time) -> datetime:
    return datetime.combine(date.fromisoformat(value), at, timezone.utc)


def curated_job(role: Mapping[str, Any]) -> JobRecord:
    """The bridge's JobRecord for a curated role, with the ranking inputs set:
    deadline from `closes`, simulated first-seen from `found`, role family."""
    data = eligibility.job(role).model_dump(mode="json")
    first_seen = _day(role["found"], time(0, 0))
    data.update(
        deadline_at=_day(role["closes"], time(23, 59)).isoformat(),
        first_seen_at=first_seen.isoformat(),
        last_seen_at=first_seen.isoformat(),
        source_published_at=None,
        discovery_kind="synthetic_scenario",
    )
    family = normalized.role_family(role["role_family"])
    data["facts"]["role_family"] = {"value": family, "evidence_ids": []} if family else None
    return JobRecord.model_validate(data)


@dataclass(frozen=True)
class Opportunity:
    """One opportunity in the Matches population."""

    job_id: str
    #: The id the role page opens: a curated role id or a synthetic job id.
    role_id: str
    #: Internal only, never shown: "curated" or "synthetic".
    kind: str
    #: The posting's identity: one opportunity per posting.
    posting: str
    title: str
    company: str
    city: str
    closes: str
    #: The role family ranking compares (one of the ten normalized families).
    role_family: Optional[str]
    #: "eligible", "uncertain" or "ineligible" (canonical engine).
    status: str
    result: EligibilityResult
    profile: ProfileFit
    job_profile: JobProfile
    #: The JobRecord ranked (the bridge's, for a curated role).
    job: JobRecord
    #: Curated top-up skills (ranking inputs only); empty for synthetic postings.
    topped_up_skills: tuple[str, ...]
    entry: Optional[PipelineEntry]

    @property
    def raw(self) -> Optional[float]:
        """The raw Priority score, 0-100, or None when not ranked."""
        score = self.entry.breakdown.score if self.entry else None
        return None if score is None else 100 * score

    @property
    def adjustment(self) -> float:
        return -VERIFY_ADJUSTMENT if self.status == "uncertain" else 0.0

    @property
    def ordering(self) -> Optional[float]:
        return None if self.raw is None else self.raw + self.adjustment

    @property
    def shown(self) -> Optional[int]:
        """The raw Priority score as displayed (half up), or None."""
        return None if self.raw is None else int(self.raw + 0.5)

    @property
    def standing(self) -> str:
        """The status in the words the screens use: eligible, verify, excluded."""
        return {"eligible": "eligible", "uncertain": "verify", "ineligible": "excluded"}[self.status]

    @property
    def parts(self) -> list[float]:
        """Each factor's weighted points (0-100 scale), in FACTOR order."""
        return [WEIGHTS[k] * (self.factor(k) or 0.0) for k in FACTORS]

    def factor(self, name: str) -> Optional[float]:
        """One factor, 0-100."""
        value = self.entry.breakdown.factors[name] if self.entry else None
        return None if value is None else 100 * value


@dataclass(frozen=True)
class Matches:
    """The whole population, the ranked order and the excluded jobs."""

    population: tuple[Opportunity, ...]
    ordered: tuple[Opportunity, ...]
    excluded: tuple[Opportunity, ...]
    ranked: AdaptedRanking
    #: Curated role ids represented by a synthetic posting (same source_job_id).
    represented_by: Mapping[str, str]

    def get(self, role_id: str) -> Optional[Opportunity]:
        """The opportunity a role id opens, following a curated copy to its posting."""
        role_id = self.represented_by.get(role_id, role_id)
        return next((o for o in self.population if o.role_id == role_id), None)


def build(roles: Sequence[Mapping[str, Any]], profile: Mapping[str, Any], answers: Mapping[str, Any],
          confirmed: Optional[Sequence[Mapping]], cv: Optional[CandidateProfile], now: datetime) -> Matches:
    """Check, score and order the whole Matches population.

    Args:
        roles: The curated demo roles available now (data/demo.json).
        profile: The demo profile.
        answers: The user's current answers.
        confirmed: The Fine-tune rows the user confirmed, or None.
        cv: The extracted CV, or None (the persona's own skills apply).
        now: A timezone-aware time (the demo clock).
    """
    cat = get_normalized_catalogue()
    postings = {job.source_job_id: job for job in cat.snapshot.jobs}
    represented = {r["id"]: postings[r["source_job_id"]].job_id for r in roles
                   if r.get("source_job_id") in postings}
    originals = [r for r in roles if r["id"] not in represented]

    candidate = normalized.demo_candidate(profile, answers, confirmed)
    facts = candidate_facts(candidate, load_skills_vocabulary(), normalized.demo_persona_skills(cv).texts)

    items: list[dict] = []
    for role in originals:
        job_profile = curated_profile(role, profile)
        items.append(dict(job=curated_job(role), result=eligibility.assess(role, profile, answers),
                          role_id=role["id"], kind=CURATED, posting=f"demo:{role['id']}",
                          title=role["title"], company=role["company"], city=role["city"],
                          closes=role["closes"], job_profile=job_profile,
                          topped_up=ranking_skills(role)[1]))
    for job in cat.snapshot.jobs:
        items.append(dict(job=job, result=assess_eligibility(candidate, job, cat.rule_catalogue,
                                                             job_parameters=cat.parameters),
                          role_id=job.job_id, kind=SYNTHETIC, posting=job.source_job_id,
                          title=job.title, company=job.company, city=job.locations[0].city or "",
                          closes=job.deadline_at.date().isoformat(), job_profile=normalized.job_profile(cat, job.job_id),
                          topped_up=()))

    fits = {item["job"].job_id: profile_fit(facts, item["job_profile"]) for item in items}
    ranked = rank_with_eligibility(
        candidate, [item["job"] for item in items], [item["result"] for item in items],
        weights=normalized.WEIGHTS,
        now=now,
        deadline_horizon_days=normalized.DEADLINE_HORIZON_DAYS,
        freshness_horizon_days=normalized.FRESHNESS_HORIZON_DAYS,
        profile_fit={job_id: None if fit.score is None else fit.score / 100 for job_id, fit in fits.items()},
    )
    p = ranked.pipeline
    entries = {e.job_id: e for g in (p.eligible, p.uncertain) for e in (*g.top, *g.rest, *g.unscored)}
    population = tuple(
        Opportunity(
            job_id=item["job"].job_id, role_id=item["role_id"], kind=item["kind"], posting=item["posting"],
            title=item["title"], company=item["company"], city=item["city"], closes=item["closes"],
            role_family=(item["job"].facts.role_family.value
                         if item["job"].facts and item["job"].facts.role_family else None),
            status=item["result"].status.value, result=item["result"], profile=fits[item["job"].job_id],
            job_profile=item["job_profile"], job=item["job"], topped_up_skills=item["topped_up"],
            entry=entries.get(item["job"].job_id),
        )
        for item in items
    )
    rankable = [o for o in population if o.status != "ineligible" and o.raw is not None]
    ordered = tuple(sorted(rankable, key=lambda o: (-o.ordering, -o.raw, o.job_id)))
    excluded = tuple(o for o in population if o.status == "ineligible")
    return Matches(population, ordered, excluded, ranked, represented)
