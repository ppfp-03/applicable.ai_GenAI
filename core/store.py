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
import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from core import eligibility, eligibility_view, ranking, rules
from oi.contracts import AnswerState, AnswerType, CandidateProfile
from oi.intelligence.eligibility.catalogue import LANGUAGE_CONSTRAINT_ID, language_level_key

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
    #: factor -> (score, note), as scored now: the role's own, except for
    #: preference fit once the candidate has confirmed preferences.
    factors: dict = field(default_factory=dict)
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
PREFERENCES = "confirmed_preferences"


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
    st.session_state.setdefault(WORK_AUTH, None)
    st.session_state.setdefault(CONSENT, False)


# ───────────────────────── Data processing consent ─────────────────────────
#
# Given by uploading a CV in onboarding step 1, or in the Profile's consent
# section. Nothing is matched, and no other profile section opens, before it.

CONSENT = "data_consent"
#: The profile section that holds the consent, and its one value.
CONSENT_SECTION = "decl"
CONSENT_LABEL = "Data processing consent"


def consent_given() -> bool:
    """Whether the user has given their data processing consent."""
    return st.session_state.get(CONSENT, False)


def give_consent() -> None:
    """Record the consent, and show it as given in the Profile's section."""
    st.session_state[CONSENT] = True
    if SECTIONS in st.session_state:  # the onboarding page alone does not run init()
        st.session_state[SECTIONS][CONSENT_SECTION] = "ok"
        st.session_state[VALUES][CONSENT_SECTION][CONSENT_LABEL] = "Given"


def show_consent() -> None:
    """Make the Profile's consent section say what the consent is.

    The consent itself is the one source: a session carried over from before
    it existed can hold the section as confirmed without it, and then asks again.
    """
    given = consent_given()
    st.session_state[SECTIONS][CONSENT_SECTION] = "ok" if given else "pend"
    st.session_state[VALUES][CONSENT_SECTION][CONSENT_LABEL] = "Given" if given else "Not given"


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
    """"Pierpaolo Filippelli" → "GR"."""
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
    """The user's current answers to our questions, as eligibility reads them.

    The work authorization declaration is the one source of the work facts
    (D-050): it is included under WORK_AUTH, and once one exists the UK
    answer is read from it, so no stored answer can contradict it.
    """
    decl = work_auth()
    if decl is None:
        return {**_answers(), WORK_AUTH: None}
    return {**_declared_answers(), WORK_AUTH: decl}


def _declared_answers() -> dict:
    """The stored answers once a declaration exists: the UK answer read from
    it, and no legacy per-country "work" answers (a session from before the
    declaration held them), so nothing stored can override it."""
    stored = {k: v for k, v in _answers().items() if k != "work"}
    return {**stored, "uk_work": uk_from_work_auth()}


def _answers() -> dict:
    """The answers as stored, without the declaration kept beside them."""
    return st.session_state.get(ANSWERS, {"uk_work": "yes"})


def uk() -> Optional[str]:
    """The current UK answer: "yes", "no", "unsure" or None."""
    return answers().get("uk_work")


def set_uk(choice: Optional[str]) -> None:
    """Record the UK answer (step 5, the question page): set_work_answer for GB.

    The stored UK answer is kept in step with the declaration for a session
    without one; answers() reads it from the declaration otherwise.
    """
    set_work_answer("GB", choice)


def work_answer(country: str) -> Optional[str]:
    """The answer to "Can you work in <country> without visa sponsorship?"
    the declaration gives: "yes" or "no" once settled, else None; the UK's is
    the UK answer (uk). Only a projection: "Not sure" is never stored."""
    if country == "GB":
        return uk()
    answer = eligibility.work_answer(eligibility.declared(declaration(), country))
    return None if answer == "unsure" else answer


def set_work_answer(country: str, choice: Optional[str]) -> None:
    """Record an answer to "Can you work in <country> without visa
    sponsorship?" in the declaration, the one source of the work facts.

    "yes" is authorized and no sponsorship needed, "no" not authorized and
    sponsorship needed. "Not sure" and no answer invent nothing: they keep
    unsettled facts (e.g. "None of these": false/null) and withdraw a "yes"
    or "no" being changed (eligibility.answer_declaration). Other countries
    are untouched. Everything downstream recomputes from it.
    """
    facts = eligibility.answer_declaration(choice, eligibility.declared(declaration(), country))
    decl = _with_country(declaration(), country, facts)
    if work_auth() is None:
        if not any(decl.values()):
            st.session_state[ANSWERS] = {**_answers(), "uk_work": choice} if country == "GB" else _answers()
            return
        # A clarification is not step 2's question: that stays to answer.
        st.session_state[WORK_QUESTION] = False
    _store_work_auth(decl)
    st.session_state[ANSWERS] = _declared_answers()


def set_answer(key: str, value: Any) -> None:
    """Record any other answer (e.g. the Fudan letter was uploaded)."""
    st.session_state[ANSWERS] = {**_answers(), key: value}


# ───────────────────────── Work authorization and sponsorship ─────────────────────────
#
# Declared in onboarding with one question, "Where can you work without
# employer sponsorship?" (D-050). Each platform country has two independent
# facts, as in the contract's WorkAuthorizationDeclaration: authorized_to_work
# and requires_sponsorship, each true, false or unknown. A country the user
# selects is authorized and needs no sponsorship. "None of these" makes every
# platform country not authorized and leaves sponsorship as it was. A country
# left out keeps what it held, unknown if nothing (answer_work_question).
# Nothing is inferred from citizenship, nor one fact from the other. Only ISO country codes are stored: "EU" is a shortcut in the form,
# never a declared country.
#
# It is the one session source of these facts: step 2, the UK question
# (step 5, the question page) and the role page's country question all read
# and write it (answer_work_question, set_work_answer), and eligibility
# reads every country in it (eligibility.declarations).

_MARKETS_PATH = Path(__file__).resolve().parent.parent / "config" / "markets.json"
#: The session key of the declaration, and the answers key eligibility reads it under.
WORK_AUTH = eligibility.DECLARATION
#: The declaration's four country lists, true then false for each fact.
WORK_AUTH_LISTS = tuple(k for pair in eligibility.DECLARATION_LISTS.values() for k in pair)
#: False while the declaration holds only clarification answers, before step
#: 2's question was answered. Not a fact: only whether that question was asked.
WORK_QUESTION = "work_question_answered"


@lru_cache(maxsize=1)
def markets() -> tuple[dict, ...]:
    """The countries the platform covers: {"code", "name", "eu"}, in display order."""
    return tuple(json.loads(_MARKETS_PATH.read_text("utf-8"))["countries"])


def eu_codes() -> tuple[str, ...]:
    """The platform countries in the EU; choosing "EU" selects all of them."""
    return tuple(c["code"] for c in markets() if c["eu"])


def country_name(code: str) -> str:
    return next(c["name"] for c in markets() if c["code"] == code)


def work_auth() -> Optional[dict]:
    """The declaration, or None until the user has made one.

    Four lists of country codes, in market order (WORK_AUTH_LISTS):
    "authorized" / "not_authorized" hold authorized_to_work true / false,
    "sponsorship" / "no_sponsorship" requires_sponsorship true / false. A
    country in neither list of a pair is unknown for that fact; a missing
    list is empty.
    """
    return st.session_state.get(WORK_AUTH)


def declaration() -> dict:
    """The declaration the work facts come from: the saved one, or before
    any is saved, the one the stored UK answer makes (the demo persona's)."""
    decl = work_auth()
    if decl is not None:
        return decl
    return _with_country({}, "GB", eligibility.answer_declaration(_answers().get("uk_work"), (None, None)))


def work_auth_complete() -> bool:
    """Whether the mandatory onboarding question has been answered. Sponsorship
    may still be unknown everywhere (D-050). A declaration a later
    clarification started (set_work_answer) does not answer it."""
    return work_auth() is not None and st.session_state.get(WORK_QUESTION, True)


def set_work_auth(declaration: dict[str, list[str]]) -> None:
    """Record the declaration (see work_auth); lists left out are empty.

    The UK part also answers the UK question, so step 5 and every screen
    start from it.

    Raises:
        ValueError: On a list or a country the platform does not know, a
            country both true and false for one fact, or one both authorized
            and in need of sponsorship.
    """
    lists = {k: set(declaration.get(k, ())) for k in WORK_AUTH_LISTS}
    extra = sorted(set(declaration) - set(WORK_AUTH_LISTS))
    if extra:
        raise ValueError(f"Not a declaration list: {', '.join(extra)}.")
    order = [c["code"] for c in markets()]
    unknown = sorted(set().union(*lists.values()) - set(order))
    if unknown:
        raise ValueError(f"Not a platform country: {', '.join(unknown)}.")
    for true, false in eligibility.DECLARATION_LISTS.values():
        if both := [c for c in order if c in lists[true] and c in lists[false]]:
            raise ValueError(f"Declared both ways: {', '.join(country_name(c) for c in both)}.")
    if both := [c for c in order if c in lists["authorized"] and c in lists["sponsorship"]]:
        names = ", ".join(country_name(c) for c in both)
        raise ValueError(f"You can’t need sponsorship where you can already work: {names}.")
    _store_work_auth(lists)
    st.session_state[ANSWERS] = _declared_answers()


def answer_work_question(countries: Optional[list[str]]) -> None:
    """Record an answer to step 2's question, "Where can you work without
    employer sponsorship?": the countries chosen, or None for "None of these".

    Only what the answer declares changes (D-050):
    - a country chosen can work there and needs no sponsorship (true/false),
      replacing whatever it held;
    - "None of these": no platform country is authorized (false). It does
      not answer sponsorship: a declared need (true) stays, and "not needed"
      (false), which contradicts it, becomes unknown;
    - a country left out keeps its facts, a sponsorship answer given later
      included. One the previous answer chose (authorized, shown selected)
      and the user unselected is withdrawn: both facts become unknown.

    Raises:
        ValueError: On a country the platform does not cover.
    """
    order = [c["code"] for c in markets()]
    if unknown := sorted(set(countries or ()) - set(order)):
        raise ValueError(f"Not a platform country: {', '.join(unknown)}.")
    before = work_auth()
    after = {k: [] for k in WORK_AUTH_LISTS}
    for country in order:
        authorized, sponsorship = eligibility.declared(before, country)
        if countries is None:
            facts = (False, True if sponsorship else None)
        elif country in countries:
            facts = (True, False)
        elif authorized:
            facts = (None, None)
        else:
            facts = (authorized, sponsorship)
        after = _with_country(after, country, facts)
    set_work_auth(after)
    st.session_state[WORK_QUESTION] = True


def _store_work_auth(declaration: dict) -> None:
    order = [c["code"] for c in markets()]
    st.session_state[WORK_AUTH] = {k: [c for c in order if c in declaration.get(k, ())] for k in WORK_AUTH_LISTS}


def _with_country(declaration: dict, country: str, facts: eligibility.Facts) -> dict:
    """The declaration with `country`'s two facts replaced by `facts`."""
    out = {k: [c for c in declaration.get(k, ()) if c != country] for k in WORK_AUTH_LISTS}
    for value, (true, false) in zip(facts, eligibility.DECLARATION_LISTS.values()):
        if value is not None:
            out[true if value else false].append(country)
    return out


def uk_from_work_auth() -> Optional[str]:
    """The UK answer the declaration gives (eligibility.work_answer): "yes" or
    "no" only for a complete answer, "unsure" for anything partial ("None of
    these" included), so step 5 still asks; None before a declaration."""
    decl = work_auth()
    if decl is None:
        return None
    return eligibility.work_answer(eligibility.declared(decl, "GB"))


def preferences() -> Optional[list[dict]]:
    """The preferences the candidate confirmed in onboarding, or None before
    they do (the demo roles' own preference fit applies until then)."""
    try:
        return st.session_state.get(PREFERENCES)
    except Exception:  # outside a Streamlit session (tests)
        return None


def set_preferences(prefs: list[dict]) -> None:
    """Confirm preferences (see ranking.preference_fit); every score follows."""
    ranking.preference_fit({}, prefs)  # raises if none carries weight
    st.session_state[PREFERENCES] = [dict(p, values=list(p["values"])) for p in prefs]


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


#: Profile sections the user can edit, with the short name used in evidence ids.
EDITABLE = (("skills", "skill"), ("education", "education"), ("experience", "experience"))
#: Prefix of the documents that hold the user's own edits to the profile.
EDIT_DOC = "profile-edit-"
#: The edits key for the languages and levels (HC_LANGUAGE answers): a list
#: of (ISO 639-1 code, level code or None) pairs, e.g. ("en", "CEFR:C1").
LANGUAGES = "languages"


#: Joins the parts of an education or experience value, as the extraction
#: prompt writes them: title · institution or employer · period.
ENTRY_SEP = " · "


def split_entry(value: str) -> tuple[str, str, str]:
    """An education or experience value as (title, organisation, period).

    A part the CV does not state is left out of the value, so the last part is
    the period only if it holds a year. Text that does not follow the format
    stays whole in the title, for the user to split.
    """
    parts = [p.strip() for p in value.split(ENTRY_SEP)]
    if len(parts) > 3:
        return value.strip(), "", ""
    period = parts.pop() if len(parts) > 1 and re.search(r"\d{4}", parts[-1]) else ""
    return parts[0], ENTRY_SEP.join(parts[1:]), period


def join_entry(title: str, organisation: str, period: str) -> str:
    """The value split_entry reads back: the stated parts, in order."""
    return ENTRY_SEP.join(p for p in (" ".join(x.split()) for x in (title, organisation, period)) if p)


def apply_edits(profile: CandidateProfile, edits: dict[str, list[str]]) -> CandidateProfile:
    """The profile with the user's version of its CV sections (FR-02).

    `edits` maps a section name in EDITABLE to the values the user kept, in
    order, and LANGUAGES to the languages kept with their levels. A value identical to one already in the section keeps that value's
    evidence, so what the CV said stays backed by the CV. Every other value is
    the user's word: all of them go into one questionnaire SourceDocument,
    each backed by a quote of itself, so a correction has provenance of its
    own and is never passed off as read from the CV. Blank values are dropped,
    and so is any evidence or edit document nothing refers to any more.
    """
    raw = profile.model_dump()
    prov = raw["provenance"]
    edit_ids = [int(d[len(EDIT_DOC):]) for d in prov["documents"] if d.startswith(EDIT_DOC)]
    doc_id = f"{EDIT_DOC}{max(edit_ids, default=0) + 1}"
    new_evidence: list[dict] = []
    for field, short in EDITABLE:
        old = list(raw[field])
        section = []
        for value in edits.get(field, [v["value"] for v in old]):
            value = " ".join(value.split())
            if not value:
                continue
            same = next((o for o in old if o["value"] == value), None)
            if same is not None:
                old.remove(same)
                section.append(same)
                continue
            evidence_id = f"ev-{doc_id}-{short}-{sum(e['field_path'] == field for e in new_evidence) + 1:03d}"
            new_evidence.append({"evidence_id": evidence_id, "document_id": doc_id, "quote": value, "field_path": field})
            section.append({"value": value, "evidence_ids": [evidence_id]})
        raw[field] = section
    if LANGUAGES in edits:
        raw["eligibility_answers"] = _edit_languages(raw["eligibility_answers"], edits[LANGUAGES], doc_id, new_evidence)
    if new_evidence:
        text = "\n".join(e["quote"] for e in new_evidence)
        prov["documents"][doc_id] = {
            "document_id": doc_id,
            "kind": "questionnaire",
            "text": text,
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "source_ref": "profile_edit",
        }
        prov["questionnaire_document_ids"].append(doc_id)
        prov["evidence"].extend(new_evidence)

    used = {i for field, _ in EDITABLE for v in raw[field] for i in v["evidence_ids"]}
    used |= {i for d in raw["declarations"]["work_authorizations"] for i in d["evidence_ids"]}
    used |= {i for answers in raw["eligibility_answers"].values() for a in answers for i in a["evidence_ids"]}
    prov["evidence"] = [e for e in prov["evidence"] if e["evidence_id"] in used]
    live = {e["document_id"] for e in prov["evidence"]}
    stale = {d for d in prov["documents"] if d.startswith(EDIT_DOC) and d not in live}
    prov["documents"] = {k: v for k, v in prov["documents"].items() if k not in stale}
    prov["questionnaire_document_ids"] = [d for d in prov["questionnaire_document_ids"] if d not in stale]
    return CandidateProfile.model_validate(raw)


def language_levels() -> dict[str, list[str]]:
    """The languages a profile can state, as ISO 639-1 codes, each with the
    levels its HC_LANGUAGE answer key allows, lowest first."""
    spec = eligibility.catalogue().get(LANGUAGE_CONSTRAINT_ID)
    return {k.answer_key.removeprefix("level_"): list(k.allowed_values or []) for k in spec.answer_keys}


def _edit_languages(answers: dict, kept: list, doc_id: str, new_evidence: list[dict]) -> dict:
    """The eligibility answers with the user's languages. A language kept at
    the level it had keeps its answer and evidence; any other is the user's
    word, recorded in the edit document `doc_id` like the other edits."""
    old = list(answers.get(LANGUAGE_CONSTRAINT_ID, []))
    out = []
    for code, level in kept:
        key = language_level_key(code)
        same = next((o for o in old if o["answer_key"] == key and o["value"] == level), None)
        if same is not None:
            out.append(same)
            continue
        n = sum(e["field_path"].startswith("eligibility_answers.") for e in new_evidence) + 1
        evidence_id = f"ev-{doc_id}-language-{n:03d}"
        new_evidence.append({
            "evidence_id": evidence_id, "document_id": doc_id, "quote": f"{code}: {level or 'level not stated'}",
            "field_path": f"eligibility_answers.{LANGUAGE_CONSTRAINT_ID}.{key}",
        })
        out.append({
            "constraint_id": LANGUAGE_CONSTRAINT_ID, "answer_key": key,
            "state": AnswerState.KNOWN if level else AnswerState.UNKNOWN, "answer_type": AnswerType.SINGLE_CHOICE,
            "value": level, "evidence_ids": [evidence_id], "source_document_id": doc_id,
        })
    rest = {k: v for k, v in answers.items() if k != LANGUAGE_CONSTRAINT_ID}
    return {**rest, LANGUAGE_CONSTRAINT_ID: out} if out else rest


def save_edits(edits: dict[str, list[str]]) -> None:
    """Replace the stored profile with the user's edited version of it."""
    st.session_state[CANDIDATE] = apply_edits(candidate(), edits)


def is_edited(profile: CandidateProfile, fact) -> bool:
    """Whether a profile value is the user's word rather than read from the CV."""
    docs = {e.evidence_id: e.document_id for e in profile.provenance.evidence}
    return any(docs[i] != profile.cv_document_id for i in fact.evidence_ids)


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


def checked_language(name: str, level: str) -> bool:
    """Whether a fixed rule checks this language requirement (CEFR, fluent, native)."""
    return eligibility.canonical_language(name, level) is not None


def view(role: RoleDef, ans: Optional[dict] = None) -> RoleView:
    """Check and score one role under `ans` (default: the current answers)."""
    d = data()
    ans = answers() if ans is None else ans
    result = eligibility.assess(role.raw, d.profile, ans)
    crit = eligibility_view.criteria(result, role.raw, d.profile, ans)
    standing = eligibility_view.standing(result)
    factors = role.factors
    prefs = preferences()
    if prefs:
        factors = {**factors, "preference": list(ranking.preference_fit(role.raw, prefs))}
    raw = ranking.raw_score(factors, d.weights)
    return RoleView(role, crit, standing, raw, ranking.priority(raw, standing, d.penalty),
                    ranking.contributions(factors, d.weights), factors,
                    limitations=eligibility_view.limitations(role.raw, d.profile, ans))


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
    return tally(ans, as_of)


def tally(ans: dict, as_of: Optional[str] = None) -> dict[str, int]:
    """Eligible / to verify / excluded among the roles available under `ans`."""
    out = {"eligible": 0, "verify": 0, "excluded": 0}
    for v in views(ans, as_of):
        out[v.standing] += 1
    return out


def uk_roles() -> list[RoleView]:
    """The available roles in the UK, the ones the UK question can settle."""
    return country_roles("GB")


def country_roles(country: str, as_of: Optional[str] = None) -> list[RoleView]:
    """The available roles in `country`, the ones its work question can settle."""
    return [v for v in views(as_of=as_of) if v.country == country]


def answers_with(country: str, choice: Optional[str]) -> dict:
    """The answers as they would be after answering "Can you work in
    <country> without visa sponsorship?" with `choice` (set_work_answer).
    Nothing is saved: previews run the same rules on it."""
    facts = eligibility.answer_declaration(choice, eligibility.declared(declaration(), country))
    out = {**answers(), WORK_AUTH: _with_country(declaration(), country, facts)}
    if country == "GB":
        out["uk_work"] = eligibility.work_answer(facts)
    return out


def pending_work_question(roles: list[RoleView]) -> Optional[str]:
    """The country whose "Can you work in <country> without visa sponsorship?"
    still decides the most of `roles` (ranked): their permission check is
    open and the declaration does not settle the country. Ties go to the
    country of the higher ranked role. None when no such question is left."""
    decl = declaration()
    n: dict[str, int] = {}
    for v in roles:
        if v.criterion("permission").status == "check" and \
                eligibility.work_answer(eligibility.declared(decl, v.country)) == "unsure":
            n[v.country] = n.get(v.country, 0) + 1
    return max(n, key=n.get) if n else None  # dicts keep rank order: the first maximum wins


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
