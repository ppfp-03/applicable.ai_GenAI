"""Onboarding Explore step: what a run of story swipes says about the candidate.

Every value in the "What we're learning about you" panel is derived here,
deterministically, from the stories (data/stories.json) and the verdicts
given so far. Nothing here feeds the ranking: the panel is for the candidate.

A verdict is "r" (I'd enjoy this), "l" (Not for me) or "u" (Not sure);
verdict i is the one given to story i.
"""

from __future__ import annotations

LIKE, PASS, UNSURE = "r", "l", "u"
VERDICTS = (LIKE, PASS, UNSURE)

RIASEC = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]

#: Where every work-design slider starts, in % of its track, and its bounds.
SLIDER_START, SLIDER_MIN, SLIDER_MAX = 50.0, 8.0, 92.0
#: How far one point of a story's lean moves a slider, in % of the track.
SLIDER_STEP = 2.5
#: A slider this far from the centre names the side it leans to.
SLIDER_LEAN = 10.0

#: Every interest starts here, as a share of the radar's radius, and stays within bounds.
INTEREST_START, INTEREST_MIN, INTEREST_MAX = 0.3, 0.08, 1.0
#: How far one point of a story's RIASEC weight moves an interest when liked.
INTEREST_STEP = 0.05
#: A pass counts for this share of a like, the other way.
PASS_WEIGHT = 0.5


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sign(verdict: str) -> float:
    return {LIKE: 1.0, PASS: -1.0}.get(verdict, 0.0)


def sliders(stories: list[dict], verdicts: list[str]) -> list[float]:
    """Each work-design slider's position, in % from its left end."""
    pos = [SLIDER_START] * len(stories[0]["lean"])
    for story, verdict in zip(stories, verdicts):
        pos = [p + _sign(verdict) * SLIDER_STEP * lean for p, lean in zip(pos, story["lean"])]
    return [_clamp(p, SLIDER_MIN, SLIDER_MAX) for p in pos]


def leaning(position: float) -> str:
    """Which side a slider leans to: "l", "r", or "" while near the centre."""
    if position <= SLIDER_START - SLIDER_LEAN:
        return "l"
    if position >= SLIDER_START + SLIDER_LEAN:
        return "r"
    return ""


def interests(stories: list[dict], verdicts: list[str]) -> list[float]:
    """Each RIASEC interest as a share of the radar radius, in RIASEC order."""
    score = [0.0] * len(RIASEC)
    for story, verdict in zip(stories, verdicts):
        k = 1.0 if verdict == LIKE else -PASS_WEIGHT if verdict == PASS else 0.0
        score = [s + k * w for s, w in zip(score, story["riasec"])]
    return [_clamp(INTEREST_START + INTEREST_STEP * s, INTEREST_MIN, INTEREST_MAX) for s in score]


def top_interests(values: list[float], n: int = 2) -> list[int]:
    """The strongest interests above their starting point, strongest first."""
    above = [i for i, v in enumerate(values) if v > INTEREST_START]
    return sorted(above, key=lambda i: -values[i])[:n]


def direction(stories: list[dict], verdicts: list[str]) -> tuple[list[str], dict | None]:
    """The directions the likes point to (up to two) and the role type to consider.

    A direction scores one per story liked and minus one per story passed;
    only directions with a positive score count. Ties go to the direction
    liked first. The role type is that of the latest liked story in the
    leading direction.
    """
    score: dict[str, int] = {}
    for story, verdict in zip(stories, verdicts):
        if verdict in (LIKE, PASS):
            score[story["direction"]] = score.get(story["direction"], 0) + (1 if verdict == LIKE else -1)
    ranked = sorted((d for d, s in score.items() if s > 0), key=lambda d: -score[d])
    if not ranked:
        return [], None
    lead = ranked[0]
    role = [s for s, v in zip(stories, verdicts) if v == LIKE and s["direction"] == lead][-1]
    return ranked[:2], role


def history(stories: list[dict], verdicts: list[str], n: int = 5) -> list[tuple[str, str]]:
    """The latest liked or passed stories, newest first: ("y" | "n", title)."""
    seen = [("y" if v == LIKE else "n", s["title"]) for s, v in zip(stories, verdicts) if v in (LIKE, PASS)]
    return seen[::-1][:n]


def cv_overlap(story: dict, skills: list[str]) -> list[str]:
    """The story's skills the CV also names, compared without case."""
    have = [s.lower() for s in skills]

    def named(k: str) -> bool:
        k = k.lower()
        return any(k == s or (len(s) > 2 and s in k) or (len(k) > 2 and k in s) for s in have)

    return [k for k in story["sk"] if named(k)]
