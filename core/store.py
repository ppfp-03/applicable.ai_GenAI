"""Demo data, session state, and everything derived from the two.

`data/demo.json` stands in for the pipeline's output. What is stored there is
what the pipeline would read or measure (a posting's requirements, a factor
score); what the product concludes is never stored: every page asks this
module, which runs the eligibility checks and core/ranking.py against the
current answers. Change an answer and every screen follows.

Every criterion comes from the canonical eligibility engine: the demo state
is mapped onto its inputs by core/eligibility.py (structural adapter) and its
result is rendered into the screens' tiles by core/eligibility_view.py
(presentation adapter). Nothing in this module decides eligibility.

The one answer that moves the most roles is the UK question. The demo starts
where the dashboard mockup does -- the user finished onboarding and said
"yes" -- and the question screen lets them change it.

New postings arrive only through a controlled, labelled scenario (FR-10): the
roles tagged with the `simulated_event` id stay out of every view until the
user runs the "Simulated ingestion event". Nothing here monitors a real source
or measures detection latency; the event only makes predefined synthetic
postings available, and the same checks and ranking then run over them.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from core import eligibility, eligibility_view, ranking, rules
from oi.contracts import CandidateProfile

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
        self.weights: dict = raw["weights"]
        self.penalty: float = raw["verify_penalty"]
        self.roles: list[RoleDef] = [RoleDef(r) for r in raw["roles"]]
        self.applications: list[dict] = raw["applications"]
        self.week: list[dict] = raw["week"]
        self.timeline: dict = raw["timeline"]
        self.sections: list[dict] = raw["profile_sections"]
        self.value_options: dict = raw["value_options"]
        self.eligibility_copy: dict = raw["eligibility_copy"]
        self.simulated_event: dict = raw["simulated_event"]

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
    #: Requirements no supported rule checks; they never change `standing`.
    limitations: list[eligibility_view.Limitation] = field(default_factory=list)

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
CANDIDATE = "candidate_profile"
EXTRACTION_ERROR = "extraction_error"
SIMULATED = "simulated_event_ran"


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
    st.session_state.setdefault(CANDIDATE, None)
    st.session_state.setdefault(EXTRACTION_ERROR, None)
    st.session_state.setdefault(SIMULATED, False)


# ───────────────────────── Access (demo only) ─────────────────────────
#
# Sign-up and log-in are staged: nothing leaves the session and any input is
# accepted. `stage` says where a visitor is in the first-run flow:
# landing | signup | login → onboarding → tour → app.

STAGE = "stage"
USER = "user"

#: The pages each stage may open (app.py sends everything else to the first).
STAGE_PAGES = {
    "landing": ("welcome",),
    "signup": ("welcome",),
    "login": ("welcome",),
    "onboarding": ("onboarding",),
}


def stage() -> str:
    """Where the visitor is in the first-run flow."""
    return st.session_state.get(STAGE, "landing")


def set_stage(name: str) -> None:
    st.session_state[STAGE] = name


def user() -> dict:
    """The signed-in user: {"name", "email"}. The persona's until sign-up names one."""
    p = data().profile
    return st.session_state.get(USER) or {"name": p["name"], "email": ""}


def initials(name: str) -> str:
    """"Giulia Rossi" → "GR"."""
    return "".join(w[0] for w in name.split()[:2]).upper() or "?"


def _fresh() -> None:
    """Forget the whole session, then set the defaults again."""
    st.session_state.clear()
    init()


def sign_up(name: str, email: str) -> None:
    """A new account: no answers, no applications, straight into onboarding."""
    _fresh()
    st.session_state[USER] = {"name": name.strip(), "email": email.strip()}
    st.session_state[ANSWERS] = {"uk_work": None}
    st.session_state[APPS] = []
    set_stage("onboarding")


def log_in() -> None:
    """A returning user: the demo profile, already set up. No tour."""
    _fresh()
    set_stage("app")


def log_out() -> None:
    _fresh()
    set_stage("landing")


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


def candidate() -> Optional[CandidateProfile]:
    """The profile extracted from the uploaded CV, or None before one is."""
    return st.session_state.get(CANDIDATE)


def set_candidate(profile: CandidateProfile) -> None:
    """Record a freshly extracted profile. It replaces any earlier one and
    clears the last extraction error."""
    st.session_state[CANDIDATE] = profile
    st.session_state[EXTRACTION_ERROR] = None


def has_candidate_for(content_hash: str) -> bool:
    """Whether the stored profile was extracted from the CV with this hash,
    so uploading the same file again need not call the model again."""
    profile = candidate()
    return profile is not None and profile.provenance.extraction.input_hash == content_hash


def extraction_error() -> Optional[str]:
    """Why the last extraction failed, or None."""
    return st.session_state.get(EXTRACTION_ERROR)


def set_extraction_error(message: str) -> None:
    """Record a failed extraction. The stored profile is dropped: it came
    from a different CV, and showing it would pass it off as this one."""
    st.session_state[EXTRACTION_ERROR] = message
    st.session_state[CANDIDATE] = None


# ───────────────────────── Simulated ingestion event ─────────────────────────


def is_simulated(role: Any) -> bool:
    """Whether a role (RoleDef or RoleView) arrives with the simulated event."""
    return role.get("scenario") == data().simulated_event["id"]


def simulated_event_ran() -> bool:
    """Whether the user has run the simulated ingestion event this session."""
    return bool(st.session_state.get(SIMULATED, False))


def run_simulated_event() -> None:
    """The controlled refresh: make the scenario's synthetic postings available.

    Idempotent. The new postings are unreviewed until the user reviews them.
    """
    if not simulated_event_ran():
        st.session_state[SIMULATED] = True
        st.session_state[REVIEWED] = False


def available() -> list[RoleDef]:
    """The roles the product knows about right now: the baseline snapshot,
    plus the scenario's postings once the simulated event has run."""
    ran = simulated_event_ran()
    return [r for r in data().roles if ran or not is_simulated(r)]


# ───────────────────────── Derived views ─────────────────────────


def view(role: RoleDef, ans: Optional[dict] = None) -> RoleView:
    """Check and score one role under `ans` (default: the current answers)."""
    d = data()
    ans = answers() if ans is None else ans
    result = eligibility.assess(role.raw, d.profile, ans)
    crit = eligibility_view.criteria(result, role.raw, d.profile, ans)
    standing = eligibility_view.standing(result)
    raw = ranking.raw_score(role.factors, d.weights)
    return RoleView(role, crit, standing, raw, ranking.priority(raw, standing, d.penalty),
                    ranking.contributions(role.factors, d.weights),
                    eligibility_view.limitations(role.raw, d.profile, ans))


def views(ans: Optional[dict] = None, as_of: Optional[str] = None) -> list[RoleView]:
    """Every role, checked and scored.

    Args:
        ans: Answers to use instead of the current ones (for previews).
        as_of: Only roles found on or before this ISO date (the onboarding
            snapshot was taken before today's new matches arrived).
    """
    return [view(r, ans) for r in available() if as_of is None or r.found <= as_of]


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
    """The postings the simulated ingestion event added (none before it runs)."""
    return [v for v in views() if v.get("new")]


def excluded() -> list[RoleView]:
    """Roles a fixed rule removed before ranking."""
    return [v for v in views() if v.standing == "excluded"]


def counts(choice: Any = "current", as_of: Optional[str] = None) -> dict[str, int]:
    """Eligible / to verify / excluded among the roles available now.

    Counted from the same checks every screen shows, so the numbers always
    match the roles the user can see (the baseline, plus the simulated
    event's postings once it has run).

    Args:
        choice: A UK answer to count under ("yes", "no", "unsure" or None);
            "current" keeps the user's own answer.
        as_of: As in `views`.
    """
    ans = answers() if choice == "current" else {**answers(), "uk_work": choice}
    out = {"eligible": 0, "verify": 0, "excluded": 0}
    for v in views(ans, as_of):
        out[v.standing] += 1
    return out


def uk_roles() -> list[RoleView]:
    """The available roles in the UK, the ones the UK question can settle."""
    return [v for v in views() if v.country == "GB"]


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
