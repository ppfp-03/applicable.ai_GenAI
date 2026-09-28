"""The priority score: four factors, fixed weights, simple arithmetic.

score = 0.40 × profile fit + 0.25 × preference fit
      + 0.20 × deadline urgency + 0.15 × freshness

The weights are the same for every role. A role still "to verify" loses a
fixed penalty until the missing fact is known, so a verified role outranks an
unverified one of similar fit. Ranking orders eligible roles; it never
decides eligibility -- that is core/rules.py, and an excluded role is never
ranked however high it would score.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

#: Factor keys, in display order.
FACTORS = ("profile", "preference", "urgency", "freshness")

#: Factor display names.
FACTOR_NAMES = {
    "profile": "Profile fit",
    "preference": "Preference fit",
    "urgency": "Deadline urgency",
    "freshness": "Freshness",
}


def contributions(factors: Mapping[str, Sequence], weights: Mapping[str, float]) -> list[float]:
    """Each factor's weighted points, in FACTORS order.

    Args:
        factors: factor -> (score 0-100, note).
        weights: factor -> weight; the four weights sum to 1.
    """
    return [factors[k][0] * weights[k] for k in FACTORS]


def raw_score(factors: Mapping[str, Sequence], weights: Mapping[str, float]) -> float:
    """The weighted sum, before any verification penalty."""
    return sum(contributions(factors, weights))


def priority(raw: float, standing: str, penalty: float) -> float:
    """The score the list is ordered by.

    Args:
        raw: The weighted sum.
        standing: "eligible", "verify" or "excluded".
        penalty: Points a "verify" role loses until verified.
    """
    return raw - penalty if standing == "verify" else raw


def shown(score: float) -> int:
    """Round half up for display. Python's round() would round 74.5 to 74."""
    return int(math.floor(score + 0.5))


def order(items: Iterable, key) -> list:
    """Highest priority first; ties keep their input order (stable sort)."""
    return sorted(items, key=lambda x: -key(x))
