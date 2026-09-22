"""Priority scoring and verdicts.

Both are arithmetic over facts the rules layer has already settled. No model
output is added to a score and none decides a verdict: `core.llm` may phrase
why a decision was reached, never reach it.

Priority is deliberately secondary in the interface -- the verdict leads, the
number explains. It is kept decomposable so every point can be traced back to
a factor in "How we know".
"""

from __future__ import annotations

from typing import Iterable, Sequence

from oi.contracts import Opportunity, Requirement, Verdict

#: Verdict order in a list: decisions the user can act on come first.
_VERDICT_ORDER: dict[Verdict, int] = {
    "apply": 0,
    "clarify": 1,
    "skip": 2,
    "closed": 3,
}

#: Priority is presented to the user as a 0-100 scale.
_MIN_PRIORITY = 0
_MAX_PRIORITY = 100


def score(opportunity: Opportunity) -> int:
    """Compute an opportunity's priority from its factors.

    The score is the sum of the weighted factors, penalties included as
    negative terms, clamped to 0-100 so the meter never misrepresents its own
    scale.

    Args:
        opportunity: The opportunity whose `factors` to sum.

    Returns:
        An integer in 0-100.
    """
    total = sum(opportunity.factors.values())
    return int(max(_MIN_PRIORITY, min(_MAX_PRIORITY, round(total))))


def verdict_for(
    requirements: Sequence[Requirement],
    deadline_days: int = 1,
) -> Verdict:
    """Decide a verdict from settled requirements.

    Precedence, strictest first:

    1. A passed deadline is "closed" regardless of fit.
    2. Any conflicting must-have is "skip" -- a real blocker, shown in slate
       rather than red, and never hidden.
    3. Any must-have still to confirm is "clarify".
    4. Otherwise "apply".

    Only must-haves can block. An unmet nice-to-have is worth mentioning on
    the opportunity page, not worth stopping an application for.

    Args:
        requirements: The requirements, already evaluated by `core.rules`.
        deadline_days: Days until the posting closes; negative means passed.

    Returns:
        One of "apply", "clarify", "skip", "closed".
    """
    if deadline_days < 0:
        return "closed"

    musts = [r for r in requirements if r.kind == "must"]

    # An empty list means we have not checked anything, which is not the same
    # as everything being fine. Ask rather than wave it through.
    if not musts:
        return "clarify"

    if any(r.status == "conflict" for r in musts):
        return "skip"
    if any(r.status == "confirm" for r in musts):
        return "clarify"
    return "apply"


def rank(opportunities: Iterable[Opportunity]) -> list[Opportunity]:
    """Order opportunities the way the product presents them.

    Verdict first, then priority descending. An actionable opportunity always
    precedes one that is merely high-scoring: the list is a queue of decisions,
    not a leaderboard.

    Sorting is stable, so opportunities with the same verdict and priority keep
    their incoming order.

    Args:
        opportunities: The opportunities to order.

    Returns:
        A new list. The input is not modified.
    """
    return sorted(
        opportunities,
        key=lambda o: (_VERDICT_ORDER.get(o.verdict, len(_VERDICT_ORDER)), -o.priority),
    )


#: Every factor in `config/ranking.json` carries an equal share of the 100.
FACTOR_MAX = 25.0


def profile_fit(requirements: Sequence[Requirement]) -> float:
    """Score how much of what a posting asks for the candidate can evidence.

    This is the one factor an answer can move, and it moves by arithmetic the
    user can check: the share of requirements backed by a quote, out of the
    factor's maximum. Nothing here is a judgement -- a requirement either has
    evidence or it does not.

    Args:
        requirements: The posting's requirements, as the rules layer left them.

    Returns:
        A value between 0 and FACTOR_MAX.
    """
    if not requirements:
        return 0.0
    met = sum(1 for r in requirements if r.status == "met")
    return round(FACTOR_MAX * met / len(requirements), 1)


def verdict_for_opportunity(opportunity: Opportunity) -> Verdict:
    """Decide the verdict the way the approved direction requires.

    Hard constraints decide; soft requirements do not. An unanswered question
    about PowerPoint is a gap in a strong application, not a closed door, and
    showing it as "Answer first" was the confusion this split exists to end.
    What still blocks is a must-have the posting itself rules out, and a rule
    we could not settle -- because an unchecked gate is not an open one.

    Args:
        opportunity: The opportunity, with its eligibility already evaluated.

    Returns:
        One of "apply", "clarify", "skip", "closed".
    """
    if opportunity.deadline_days < 0:
        return "closed"

    status = opportunity.eligibility_status
    if status == "conflict":
        return "skip"

    # A must-have the posting explicitly rules out blocks whatever the rules
    # say: being allowed to work somewhere does not make you eligible for a
    # role that asks for something you do not have.
    if verdict_for(opportunity.requirements, opportunity.deadline_days) == "skip":
        return "skip"

    if status == "confirm":
        return "clarify"
    return "apply"


def rescore(opportunity: Opportunity) -> None:
    """Recompute an opportunity's fit, priority and verdict in place.

    Called after an answer settles a requirement. The other three factors are
    properties of the posting, not of the candidate, so they do not move.

    Args:
        opportunity: The opportunity to bring up to date.
    """
    opportunity.factors["profile_fit"] = profile_fit(opportunity.requirements)
    opportunity.priority = score(opportunity)
    opportunity.verdict = verdict_for_opportunity(opportunity)


def score_with(opportunity: Opportunity, weights: dict[str, float]) -> int:
    """Score an opportunity under weights other than the stored ones.

    Each factor is held as its contribution under the balanced default, so a
    weight of 0.4 where the default was 0.25 scales that contribution by
    1.6. This is what lets Preferences show the effect of a change before it
    is saved, with the same arithmetic that would produce it afterwards.

    Args:
        opportunity: The opportunity to score.
        weights: Factor name -> weight, as `config/ranking.json` holds them.

    Returns:
        An integer in 0-100.
    """
    default = 1 / max(len(opportunity.factors), 1)
    total = sum(
        value * (weights.get(key, default) / default)
        for key, value in opportunity.factors.items()
    )
    return int(max(_MIN_PRIORITY, min(_MAX_PRIORITY, round(total))))
