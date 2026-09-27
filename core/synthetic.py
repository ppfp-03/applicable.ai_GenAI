"""The OI-50 synthetic catalogue, checked and ranked for the screens.

A presentation adapter, deciding nothing: the 50 canonical jobs
(``oi.io.synthetic_catalogue``) go through the canonical eligibility engine
with the committed parameter layer, then through the production ranking
pipeline (``oi.intelligence.ranking_adapter``). The screens only read the
result.

The catalogue is kept apart from the curated demo roles in
``data/demo.json``: those carry hand-authored factor scores and a
verification penalty, these carry none, so the two are never merged into one
list or compared score for score.

The candidate is the one every other screen checks: the demo profile plus
the user's current answers, as ``core.eligibility.candidate`` builds it.
Ranking factors the data does not support stay missing; nothing is filled in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Mapping, Optional

from core import eligibility
from oi.contracts import JobRecord
from oi.intelligence.eligibility import EligibilityResult, assess_eligibility, load_job_parameters
from oi.intelligence.ranking import FACTOR_NAMES, PipelineEntry, PipelineExclusion
from oi.intelligence.ranking_adapter import AdaptedRanking, rank_with_eligibility
from oi.io.synthetic_catalogue import get_synthetic_catalogue

#: Development ranking configuration (PROJECT_CONTEXT: not frozen, Q-05).
WEIGHTS = {"profile_fit": 0.40, "preference_fit": 0.25, "deadline_urgency": 0.20, "freshness": 0.15}
DEADLINE_HORIZON_DAYS = 30
FRESHNESS_HORIZON_DAYS = 30
#: How many ranked roles each group shows before "more".
TOP_N = 5

FACTOR_LABELS = {
    "profile_fit": "Profile fit",
    "preference_fit": "Preference fit",
    "deadline_urgency": "Deadline urgency",
    "freshness": "Freshness",
}
STATUS_LABELS = {
    "eligible": "Eligible under checked rules",
    "uncertain": "Needs verification",
    "ineligible": "Explicit conflict",
}
EXCLUSION_LABELS = {"ineligible": "Explicit conflict", "closed": "Closed", "expired": "Expired"}


@lru_cache(maxsize=1)
def jobs() -> tuple[JobRecord, ...]:
    """The 50 catalogue jobs, in catalogue order."""
    return tuple(get_synthetic_catalogue().jobs)


@lru_cache(maxsize=1)
def _layer():
    return load_job_parameters()


def is_synthetic(job_id: Optional[str]) -> bool:
    return bool(job_id) and job_id.startswith("synthetic:")


def aware(moment: datetime) -> datetime:
    """The demo clock is naive; ranking needs a zone. It is read as UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Catalogue:
    """One ranking run over the catalogue, plus lookups the screens need."""

    ranked: AdaptedRanking

    @property
    def pipeline(self):
        return self.ranked.pipeline

    def result(self, job_id: str) -> EligibilityResult:
        return self.ranked.eligibility[job_id]

    def entry(self, job_id: str) -> Optional[PipelineEntry]:
        """The job's ranking entry, or None if it was excluded."""
        for group in (self.pipeline.eligible, self.pipeline.uncertain):
            for item in (*group.top, *group.rest, *group.unscored):
                if item.job_id == job_id:
                    return item
        return None

    def exclusion(self, job_id: str) -> Optional[PipelineExclusion]:
        return next((x for x in self.pipeline.excluded if x.job_id == job_id), None)

    def counts(self) -> dict[str, int]:
        p = self.pipeline
        scored = sum(len(g.top) + len(g.rest) for g in (p.eligible, p.uncertain))
        unscored = sum(len(g.unscored) for g in (p.eligible, p.uncertain))
        return {
            "total": len(self.ranked.eligibility),
            "eligible": sum(len(x) for x in (p.eligible.top, p.eligible.rest, p.eligible.unscored)),
            "uncertain": sum(len(x) for x in (p.uncertain.top, p.uncertain.rest, p.uncertain.unscored)),
            "excluded": len(p.excluded),
            "scored": scored,
            "unscored": unscored,
        }


#: Recent runs, keyed by (candidate key, time); oldest dropped first.
_RUNS: dict[tuple[str, str], Catalogue] = {}
_MAX_RUNS = 16


def run(profile: Mapping[str, Any], answers: Mapping[str, Any], now: datetime) -> Catalogue:
    """Check and rank the catalogue for the demo candidate under `answers`.

    Uses only the bridge's public candidate boundary: `candidate` builds the
    profile, `candidate_key` says when two runs would build the same one.
    """
    moment = aware(now)
    key = (eligibility.candidate_key(profile, answers), moment.isoformat())
    if key not in _RUNS:
        if len(_RUNS) >= _MAX_RUNS:
            _RUNS.pop(next(iter(_RUNS)))
        _RUNS[key] = _rank(eligibility.candidate(profile, answers), moment)
    return _RUNS[key]


def _rank(candidate, now: datetime) -> Catalogue:
    catalogue, layer = eligibility.catalogue(), _layer()
    records = list(jobs())
    results = [assess_eligibility(candidate, job, catalogue, job_parameters=layer) for job in records]
    ranked = rank_with_eligibility(
        candidate, records, results,
        weights=WEIGHTS,
        now=now,
        deadline_horizon_days=DEADLINE_HORIZON_DAYS,
        freshness_horizon_days=FRESHNESS_HORIZON_DAYS,
        limit=TOP_N,
    )
    return Catalogue(ranked)


def current() -> Catalogue:
    """The catalogue under the demo profile and the user's current answers."""
    from core import clock, store

    return run(store.data().profile, store.answers(), clock.now())


def shown(score: Optional[float]) -> Optional[int]:
    """A 0-1 priority score on the screens' 0-100 scale; None stays None."""
    return None if score is None else int(score * 100 + 0.5)


def factors(entry: PipelineEntry) -> list[tuple[str, Optional[int], Optional[float]]]:
    """(label, value 0-100 or None, effective weight or None) for each factor."""
    b = entry.breakdown
    return [
        (FACTOR_LABELS[name], shown(b.factors[name]), b.effective_weights.get(name))
        for name in FACTOR_NAMES
    ]


def basis(entry: PipelineEntry) -> tuple[list[str], int]:
    """The factor families a score rests on (lower-case labels), and how many
    had no data. Read from the breakdown; nothing is recomputed."""
    b = entry.breakdown
    used = [FACTOR_LABELS[name].lower() for name in FACTOR_NAMES if b.factors[name] is not None]
    return used, len(b.missing)


def limited(entry: PipelineEntry) -> bool:
    """Whether a score exists but some factor families had no data."""
    return entry.score is not None and len(entry.breakdown.missing) > 0


def basis_text(entry: PipelineEntry) -> str:
    """"Based on deadline urgency only · 3 factors unavailable", and the like."""
    used, missing = basis(entry)
    if len(used) == 1:
        on = f"{used[0]} only"
    else:
        on = ", ".join(used[:-1]) + f" and {used[-1]}"
    unavailable = f"{missing} factor{'s' if missing != 1 else ''} unavailable"
    return f"Based on {on} · {unavailable}"


#: Readable names for the engine's answer keys, for reasons shown on screen.
ANSWER_LABELS = {
    "current_status": "student status",
    "expected_graduation_date": "expected graduation date",
    "degree_level": "degree level",
    "degree_status": "degree status",
    "field_of_study": "field of study",
    "prior_experience_months": "months of experience",
    "has_corporate_finance_experience": "Corporate Finance experience",
}
_LEVEL_KEY = re.compile(r"\blevel_([a-z]{2})\b")
_RULE_ID = re.compile(r"\bHC_[A-Z_]+\b")
_VERSION = re.compile(r"\s*\bv\d+(?:\.\d+)+\b")
_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")


@lru_cache(maxsize=1)
def _language_names() -> dict[str, str]:
    """ISO code -> language name, from the catalogue's own answer-key text."""
    spec = eligibility.catalogue().get("HC_LANGUAGE")
    names = {}
    for key in spec.answer_keys if spec else ():
        code = key.answer_key.removeprefix("level_")
        names[code] = (key.description or code).split(" proficiency")[0]
    return names


def readable(reason: str, rule_id: str) -> str:
    """An engine reason with no internal identifier left in it.

    Presentation only: the RuleOutcome keeps its own text. Answer keys become
    their names, language codes become language names, rule IDs become rule
    labels, versions are dropped, and any other snake_case value is spelled
    with spaces.
    """
    names = _language_names()
    text = _RULE_ID.sub(lambda m: rule_label(m.group(0)), reason)
    text = _VERSION.sub("", text)
    text = _LEVEL_KEY.sub(lambda m: f"{names.get(m.group(1), m.group(1).upper())} level", text)
    for key, label in ANSWER_LABELS.items():
        text = re.sub(rf"\b{key}\b", label, text)
    if rule_id == "HC_LANGUAGE":
        text = re.sub(r"\b([A-Z]{2})\b", lambda m: names.get(m.group(1).lower(), m.group(1)), text)
    return _SNAKE.sub(lambda m: m.group(0).replace("_", " "), text)


def rule_label(rule_id: str) -> str:
    """The catalogue's display name for a rule, never its ID."""
    spec = eligibility.catalogue().get(rule_id)
    return spec.label if spec else "Requirement"


def place(job: JobRecord) -> str:
    """The job's current locations as written, "·"-joined."""
    return " · ".join(loc.city or "" for loc in job.locations if loc.city) or "Location not stated"
