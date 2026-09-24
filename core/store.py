"""Demo data, session state, and everything derived from the two.

`data/demo.json` stands in for the pipeline's output. What is stored there is
what the pipeline would read or measure (a posting's requirements, a factor
score); what the product concludes is never stored: every page asks this
module, which runs core/rules.py and core/ranking.py against the current
answers. Change an answer and every screen follows.

The one answer that moves the most roles is the UK question. The demo starts
where the dashboard mockup does -- the user finished onboarding and said
"yes" -- and the question screen lets them change it.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from core import ranking, rules

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "demo.json"

#: The UK answers, and how the screens name them.
UK_CHOICES = ("yes", "no", "unsure")
UK_LABELS = {"yes": "Yes", "no": "No · needs sponsorship", "unsure": "Not sure", None: "Unknown"}


class Data:
    """The demo dataset, read once per process. Treat it as read-only."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.today: str = raw["today"]
        self.now: str = raw["now"]
        self.updated: str = raw["ranking_updated"]
        self.profile: dict = raw["profile"]
        self.catalog: dict = raw["catalog"]
        self.weights: dict = raw["weights"]
        self.penalty: float = raw["verify_penalty"]
        self.roles: list[RoleDef] = [RoleDef(r) for r in raw["roles"]]
        self.applications: list[dict] = raw["applications"]
        self.week: list[dict] = raw["week"]
        self.timeline: dict = raw["timeline"]
        self.sections: list[dict] = raw["profile_sections"]
        self.value_options: dict = raw["value_options"]
        self.eligibility_copy: dict = raw["eligibility_copy"]

    def role(self, role_id: str) -> "RoleDef":
        """One role by id.

        Raises:
            KeyError: If no role has that id.
        """
        for r in self.roles:
            if r.id == role_id:
                return r
        raise KeyError(f"No role with id {role_id!r}.")


class RoleDef:
    """A role as the pipeline delivered it. Attribute access to its fields."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    def __getattr__(self, name: str) -> Any:
        try:
            return self.raw[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def get(self, name: str, default: Any = None) -> Any:
        return self.raw.get(name, default)


@dataclass
class RoleView:
    """A role as the product sees it right now: checked and scored."""

    role: RoleDef
    criteria: list[rules.Criterion]
    standing: str  # eligible | verify | excluded
    raw: float
    score: float
    parts: list[float] = field(default_factory=list)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.role, name)

    @property
    def shown(self) -> int:
        """The priority score as displayed."""
        return ranking.shown(self.score)

    @property
    def raw_shown(self) -> int:
        """The score before the verification penalty, as displayed."""
        return ranking.shown(self.raw)

    @property
    def met(self) -> int:
        return sum(c.status == "met" for c in self.criteria)

    def criterion(self, cid: str) -> rules.Criterion:
        return next(c for c in self.criteria if c.id == cid)


@lru_cache(maxsize=1)
def _load() -> Data:
    return Data(json.loads(_DATA_PATH.read_text(encoding="utf-8")))


def data() -> Data:
    """The dataset."""
    return _load()


# ───────────────────────── Session state ─────────────────────────

ANSWERS = "answers"
SECTIONS = "section_status"
VALUES = "section_values"
NOTES = "section_notes"
APPS = "applications"
EXTRA = "extra_answers"
REVIEWED = "new_reviewed"


def init() -> None:
    """Create every session key once, so pages never test for absence."""
    d = data()
    st.session_state.setdefault(ANSWERS, {"uk_work": "yes"})
    st.session_state.setdefault(EXTRA, {})
    st.session_state.setdefault(SECTIONS, {s["id"]: s["status"] for s in d.sections})
    st.session_state.setdefault(VALUES, {s["id"]: dict(s["vals"]) for s in d.sections})
    st.session_state.setdefault(NOTES, {})
    st.session_state.setdefault(APPS, copy.deepcopy(d.applications))
    st.session_state.setdefault(REVIEWED, False)


def answers() -> dict:
    """The user's current answers to our questions."""
    return st.session_state.get(ANSWERS, {"uk_work": "yes"})


def uk() -> Optional[str]:
    """The current UK answer: "yes", "no", "unsure" or None."""
    return answers().get("uk_work")


def set_uk(choice: Optional[str]) -> None:
    """Record the UK answer. Everything downstream recomputes from it."""
    st.session_state[ANSWERS] = {**answers(), "uk_work": choice}


def set_answer(key: str, value: Any) -> None:
    """Record any other answer (e.g. the Fudan letter was uploaded)."""
    st.session_state[ANSWERS] = {**answers(), key: value}


# ───────────────────────── Derived views ─────────────────────────


def view(role: RoleDef, ans: Optional[dict] = None) -> RoleView:
    """Check and score one role under `ans` (default: the current answers)."""
    d = data()
    ans = answers() if ans is None else ans
    crit = rules.evaluate(d.profile, ans, role.raw)
    standing = rules.verdict(crit)
    raw = ranking.raw_score(role.factors, d.weights)
    return RoleView(role, crit, standing, raw, ranking.priority(raw, standing, d.penalty),
                    ranking.contributions(role.factors, d.weights))


def views(ans: Optional[dict] = None, as_of: Optional[str] = None) -> list[RoleView]:
    """Every role, checked and scored.

    Args:
        ans: Answers to use instead of the current ones (for previews).
        as_of: Only roles found on or before this ISO date (the onboarding
            snapshot was taken before today's new matches arrived).
    """
    return [view(r, ans) for r in data().roles if as_of is None or r.found <= as_of]


def reviewed() -> bool:
    """Whether the user has reviewed today's new matches."""
    return bool(st.session_state.get(REVIEWED, False))


def ranked(
    ans: Optional[dict] = None, as_of: Optional[str] = None, include_new: Optional[bool] = None
) -> list[RoleView]:
    """Eligible and to-verify roles, highest priority first.

    Args:
        ans: Answers to use instead of the current ones.
        as_of: Snapshot date; see `views`.
        include_new: Whether today's unreviewed matches join the list. By
            default they do once the user has reviewed them.
    """
    if include_new is None:
        include_new = _reviewed_safe()
    pool = [v for v in views(ans, as_of) if v.standing != "excluded"]
    if not include_new:
        pool = [v for v in pool if not v.get("new")]
    return ranking.order(pool, lambda v: v.score)


def _reviewed_safe() -> bool:
    try:
        return reviewed()
    except Exception:  # outside a Streamlit session (tests)
        return False


def top_matches() -> list[RoleView]:
    """The dashboard strip: ranked roles in the cities the user asked for,
    today's new ones included, so nothing good hides behind a review step."""
    cities = set(data().profile["preferred_cities"])
    return [v for v in ranked(include_new=True) if v.city in cities]


def new_matches() -> list[RoleView]:
    """Roles found today, not yet reviewed."""
    return [v for v in views() if v.get("new")]


def excluded() -> list[RoleView]:
    """Roles a fixed rule removed before ranking."""
    return [v for v in views() if v.standing == "excluded"]


def counts(choice: Any = "current") -> dict[str, int]:
    """Catalogue-level eligible / to verify / excluded for a UK answer."""
    key = uk() if choice == "current" else choice
    return data().catalog["by_uk_answer"][key or "none"]


def movement(before: dict, after: dict, n: int = 5, as_of: Optional[str] = None) -> dict[str, str]:
    """How each of the top `n` moved between two sets of answers.

    Returns:
        role id -> "↑ 2", "↓ 4", "New" or "—".
    """
    old = [v.id for v in ranked(before, as_of)]
    moves = {}
    for i, v in enumerate(ranked(after, as_of)[:n]):
        if v.id not in old[:n]:
            moves[v.id] = "New"
        else:
            d = old.index(v.id) - i
            moves[v.id] = f"↑ {d}" if d > 0 else f"↓ {-d}" if d < 0 else "—"
    return moves


def applications() -> list[dict]:
    """The user's applications, joined to their roles."""
    d = data()
    return [{**a, "r": d.role(a["role"])} for a in st.session_state.get(APPS, d.applications)]


def stage_counts() -> dict[str, int]:
    out = {"saved": 0, "progress": 0, "applied": 0, "interview": 0}
    for a in st.session_state.get(APPS, data().applications):
        out[a["stage"]] += 1
    return out


def save_application(role_id: str, stage: str = "progress") -> None:
    """Start (or move) an application for a role."""
    apps = st.session_state[APPS]
    for a in apps:
        if a["role"] == role_id:
            a["stage"] = stage
            return
    r = data().role(role_id)
    apps.append({"role": role_id, "stage": stage, "progress": [0, 3],
                 "note": f"Started today · closes {r.closes_label}", "actions": ["Continue", "Preview"]})


def nav_counts() -> dict[str, int]:
    """Badges for the top bar."""
    return {"matches": counts()["eligible"], "applications": len(st.session_state.get(APPS, []))}
