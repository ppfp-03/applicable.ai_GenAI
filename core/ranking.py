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
