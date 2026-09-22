"""Session state, and the one interaction that changes it.

The product's key moment is small: a question is answered, and the list
visibly rearranges itself. Everything needed for that lives here so the
pages stay about layout.

Two properties matter more than convenience, and both are the reason this is
not done inline in a page:

Deterministic
    Answering runs the rules and the arithmetic, never a model. The same
    answer always produces the same rearrangement, and every step of it can
    be printed.
Explained
    The before state is captured before anything moves, so the screen can
    show what changed rather than merely showing a new number. A ranking that
    changes without saying why is the thing this product is against.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from oi.contracts import Delta, Fact, Opportunity, Question

from core import ranking

#: Session keys, in one place so a typo cannot quietly create a second store.
FACTS = "facts"
ANSWERS = "answers"
WEEK = "week_plan"
LAST_DELTA = "last_delta"
SELECTED = "selected_opportunity"
COMPARE = "compare_ids"
SHOW_SOURCES = "show_sources"


def init(data: Any) -> None:
    """Create every session key once, so pages never test for absence.

    Args:
        data: The loaded dataset, used for the default selection.
    """
    st.session_state.setdefault(FACTS, [])
    st.session_state.setdefault(ANSWERS, {})
    st.session_state.setdefault(WEEK, [])
    st.session_state.setdefault(LAST_DELTA, [])
    st.session_state.setdefault(COMPARE, [])
    st.session_state.setdefault(SHOW_SOURCES, False)
    ranked = ranking.rank(data.opportunities)
    st.session_state.setdefault(SELECTED, ranked[0].id if ranked else None)


def ranks(data: Any) -> dict[str, int]:
    """Map every opportunity id to its 1-based position in the list.

    Args:
        data: The loaded dataset.

    Returns:
        id -> rank.
    """
    return {o.id: i for i, o in enumerate(ranking.rank(data.opportunities), start=1)}


def open_questions(data: Any) -> list[Question]:
    """The questions still worth asking.

    A question that has been answered is gone for good: the answer is kept as
    a fact and reused, which is the promise made when it was asked.

    Args:
        data: The loaded dataset.

    Returns:
        The unanswered questions, most unlocking first.
    """
    answered = st.session_state.get(ANSWERS, {})
    pending = [q for q in data.questions if q.id not in answered]
    return sorted(pending, key=lambda q: -len(q.unlocks))


def _apply_answer(question: Question, choice: str, opp: Opportunity) -> list[str]:
    """Settle the requirements this question was asked for.

    Args:
        question: The question that was answered.
        choice: The option the user picked.
        opp: One opportunity the answer unlocks.

    Returns:
        A readable line per requirement that moved.
    """
    if choice in question.resolution.get("met", []):
        new_status = "met"
    elif choice in question.resolution.get("conflict", []):
        new_status = "conflict"
    else:
        # "Not sure" and anything unlisted: the requirement stays open. We
        # record that we asked, and never turn a shrug into a fact.
        return []

    moved = []
    for req in opp.requirements:
        if req.question_id != question.id or req.status == new_status:
            continue
        was = "To confirm" if req.status == "confirm" else req.status.title()
        req.status = new_status  # type: ignore[assignment]
        moved.append(f"“{req.ask}” · {was} → {new_status.title()}")
    return moved


def answer(data: Any, question: Question, choice: str) -> None:
    """Record an answer, recompute everything it touches, and keep the delta.

    Args:
        data: The loaded dataset.
        question: The question that was answered.
        choice: The option the user picked.
    """
    before_ranks = ranks(data)
    before: dict[str, tuple[str, int, int]] = {
        oid: (o.verdict, o.priority, before_ranks[oid])
        for oid in question.unlocks
        for o in [data.opportunity(oid)]
    }

    changes: dict[str, list[str]] = {}
    for oid in question.unlocks:
        opp = data.opportunity(oid)
        moved = _apply_answer(question, choice, opp)
        if moved:
            ranking.rescore(opp)
            changes[oid] = moved

    st.session_state[ANSWERS][question.id] = choice
    st.session_state[FACTS].append(
        Fact(key=question.id, value=choice, date=data.today).model_dump()
    )

    after_ranks = ranks(data)
    deltas = []
    for oid, lines in changes.items():
        opp = data.opportunity(oid)
        deltas.append(
            Delta(
                opportunity_id=oid,
                before=before[oid],  # type: ignore[arg-type]
                after=(opp.verdict, opp.priority, after_ranks[oid]),
                changes=[tuple(line.split(" · ", 1)) for line in lines],  # type: ignore[misc]
            ).model_dump()
        )
    st.session_state[LAST_DELTA] = deltas


def dismiss_delta() -> None:
    """Clear the recompute card once the user has seen it."""
    st.session_state[LAST_DELTA] = []


def in_week(opportunity_id: str) -> bool:
    """Whether an opportunity is already planned for this week."""
    return opportunity_id in st.session_state.get(WEEK, [])


def add_to_week(opportunity_id: str) -> None:
    """Plan an opportunity for this week, once."""
    if not in_week(opportunity_id):
        st.session_state[WEEK].append(opportunity_id)


def hours_planned(data: Any) -> float:
    """Hours the planned applications will take, from their own checklists.

    Args:
        data: The loaded dataset.

    Returns:
        The dataset's baseline plus whatever this session added.
    """
    added = sum(
        hours
        for oid in st.session_state.get(WEEK, [])
        for _, hours in data.opportunity(oid).before_you_apply
    )
    return data.hours_planned + added


def select(opportunity_id: str) -> None:
    """Point the detail pane at one opportunity."""
    st.session_state[SELECTED] = opportunity_id


def selected(data: Any) -> Optional[Opportunity]:
    """The opportunity the detail pane is showing, if it still exists."""
    oid = st.session_state.get(SELECTED)
    try:
        return data.opportunity(oid) if oid else None
    except KeyError:
        return None
