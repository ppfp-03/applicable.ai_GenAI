"""The hard constraints, decided before anything is ranked.

Three questions can stop an application outright, and none of them is a
matter of degree: may you work there, are you graduating in the window they
ask for, is the role somewhere you said you would go. They are answered here,
by comparison and table lookup, and the answers carry the constraint id from
`config/hard_constraints.json` so an outcome on screen can be traced back.

Why this is a module of its own rather than more requirements: a requirement
is how well you fit, and fit is weighed against other fit. An eligibility
check is a gate. Mixing them would let a high score paper over a closed door,
which is exactly the failure this product exists to avoid.
"""

from __future__ import annotations

from typing import Any, Optional

from oi.contracts import EligibilityCheck, Opportunity, Source

from core import rules

#: The user's own preferences are a deterministic filter too, but they are
#: the user's, not a rule: the source line says so.
_YOU = "Preferences"


def _check(
    constraint_id: str,
    label: str,
    status: str,
    explanation: str,
    source: Source,
) -> EligibilityCheck:
    return EligibilityCheck(
        constraint_id=constraint_id,
        label=label,
        status=status,  # type: ignore[arg-type]
        explanation=explanation,
        source=source,
    )


def work_authorisation(profile: dict[str, Any], opp: Opportunity) -> EligibilityCheck:
    """Decide the right to work, deferring entirely to `core.rules`.

    Args:
        profile: The candidate profile; `citizenship` is read from it.
        opp: The opportunity, for its country and contract length.

    Returns:
        The check, carrying the rule's own explanation verbatim.
    """
    outcome = rules.work_authorisation(
        profile.get("citizenship"), opp.country or "", opp.contract_months
    )
    where = (
        outcome.evidence.source.where
        if outcome.evidence is not None
        else f"{opp.country} · no rule yet"
    )
    return _check(
        "HC_WORK_AUTH",
        "Work authorisation",
        outcome.status,
        outcome.explanation,
        Source(kind="RULE", where=where),
    )


def graduation_window(
    profile: dict[str, Any], window: Optional[list[int]]
) -> EligibilityCheck:
    """Compare the candidate's graduation year with the posting's window.

    Args:
        profile: The candidate profile; `graduation_year` is read from it.
        window: The [first, last] years the posting accepts, or None when the
            posting does not say.

    Returns:
        A met check when the year falls inside, a conflict when it does not,
        and a confirm when either side is silent. A missing window is not an
        open door: it is an unanswered question.
    """
    year = profile.get("graduation_year")
    if window is None or year is None:
        return _check(
            "HC_GRAD_WINDOW",
            "Graduation window",
            "confirm",
            "This posting does not state which cohort it is open to."
            if year is not None
            else "Your graduation date is not settled yet.",
            Source(kind="JOB", where="§Requirements"),
        )

    first, last = window[0], window[-1]
    if first <= year <= last:
        return _check(
            "HC_GRAD_WINDOW",
            "Graduation window",
            "met",
            f"You graduate in {year}, inside the {first}–{last} window they ask for.",
            Source(kind="CV", where="p.1 · Education"),
        )
    return _check(
        "HC_GRAD_WINDOW",
        "Graduation window",
        "conflict",
        f"They are open to {first}–{last} graduates. You graduate in {year}.",
        Source(kind="JOB", where="§Requirements, l.1"),
    )


def location(preferences: dict[str, Any], opp: Opportunity) -> EligibilityCheck:
    """Check the role's country against the countries the user selected.

    This one is a filter the user set, not a rule of the world, and the source
    line says `YOU` so the difference is never blurred.

    Args:
        preferences: The user's preferences; `countries` is read from it.
        opp: The opportunity, for its country and city.

    Returns:
        A met check when the country was selected, a conflict when it was not.
    """
    countries = preferences.get("countries") or []
    if not countries:
        return _check(
            "HC_LOCATION",
            "Location",
            "confirm",
            "You have not chosen any countries yet.",
            Source(kind="YOU", where=_YOU),
        )
    if opp.country in countries:
        return _check(
            "HC_LOCATION",
            "Location",
            "met",
            f"{opp.city} is in one of the countries you selected.",
            Source(kind="YOU", where=f"{_YOU} · {', '.join(countries)}"),
        )
    return _check(
        "HC_LOCATION",
        "Location",
        "conflict",
        f"{opp.city} is outside the countries you selected.",
        Source(kind="YOU", where=f"{_YOU} · {', '.join(countries)}"),
    )


def evaluate(
    profile: dict[str, Any],
    preferences: dict[str, Any],
    opp: Opportunity,
    window: Optional[list[int]] = None,
) -> list[EligibilityCheck]:
    """Run every hard constraint for one opportunity, in display order.

    Args:
        profile: The candidate profile.
        preferences: The user's preferences.
        opp: The opportunity to check.
        window: The posting's graduation window, when it states one.

    Returns:
        The three checks, always in the same order so the section reads the
        same way on every opportunity.
    """
    return [
        work_authorisation(profile, opp),
        graduation_window(profile, window),
        location(preferences, opp),
    ]
