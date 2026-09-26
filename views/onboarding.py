"""Onboarding — seven steps from CV to a first shortlist (00_Onboarding.html).

Upload CV → Profile → Preferences (explore by swiping, then fine-tune) →
Analysis → Shortlist → Clarify → Updated ranking.

Every step renders the mockup's own markup (ui/onboarding_markup.py) with the
live values filled in; native buttons sit invisibly over each interactive
element at the position it has on the mockup's stage. The ranking shown is
the real one: the shortlist is ranked from the roles known on the day of
onboarding with the UK question unanswered, and the answer given in step 6
is saved and recomputes everything.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import streamlit as st

from core import clock, explore, ranking, store
from oi.intelligence.eligibility.catalogue import LANGUAGE_CONSTRAINT_ID, LanguageLevel
from oi.intelligence.extraction import extract_candidate
from oi.io.pdf import PdfExtractionError, extract_pdf_text
from oi.providers.kimi import KimiClient
from oi.providers.model_client import ExtractionError
from ui import onboarding_markup as M
from ui import parts, tabs
from ui.html import CK12, CK_WHITE, WN12, esc, html, squash
from ui.palette import orange
from ui.theme import page_css

d = store.data()
page_css("onboarding")
STORIES = json.loads((Path(__file__).resolve().parent.parent / "data" / "stories.json").read_text("utf-8"))
SWIPE_JS = (Path(__file__).resolve().parents[1] / "ui" / "js" / "swipe.js").read_text(encoding="utf-8")

#: (key, step number, footer info, call to action) — the mockup's own list.
FLOW = [
    ("1", 1, "<b>Step 1 of 7</b> · Upload your CV", "Continue"),
    ("2", 2, "<b>Step 2 of 7</b> · Every field links back to your CV", "Confirm profile"),
    ("3b", 3, "<b>Step 3 of 7</b> · Swipe or use ← ↑ → on your keyboard", "Continue"),
    ("3a", 3, "<b>Step 3 of 7</b> · Only what you confirm here shapes your ranking", "Find my roles"),
    ("4", 4, "<b>Step 4 of 7</b> · Ranking your roles…", "View shortlist"),
    ("5", 5, "<b>Step 5 of 7</b> · Some of your top matches need one answer", "Answer 1 question"),
    ("6", 6, "<b>Step 6 of 7</b> · One answer updates one field", "Save answer"),
    ("7", 7, "<b>Step 7 of 7</b> · Your shortlist is ready", "Start application"),
]
KEYS = [f[0] for f in FLOW]
STEP_NAMES = ["Upload CV", "Profile", "Preferences", "Analysis", "Shortlist", "Clarify", "Updated ranking"]

#: Positions of interactive elements on the mockup stage, relative to the
#: step body (x, y, w, h). Measured from 00_Onboarding.html.
TOP = [(355, 6, 119, 36), (476, 6, 93, 36), (570, 6, 128, 36), (700, 6, 105, 36),
       (807, 6, 104, 36), (914, 6, 93, 36), (1009, 6, 156, 36)]
SEG_3A = [(33, 27, 95, 28), (130, 27, 112, 28)]
#: The Fine-tune table: first row's segment top, row pitch, segment lefts.
IMP_Y0, IMP_DY = 189, 48
IMP_X = [588, 697, 806, 915]
ACTS_3B = [(422, 645, 61, 104), (505, 652, 49, 90), (576, 645, 72, 104)]
SEG_3B = [(24, 4, 95, 26), (121, 4, 111, 26)]
OPTS_6 = [(230, 375, 600, 68), (230, 453, 600, 68), (230, 531, 600, 68)]
FILT_7 = [(33, 107, 56, 26), (91, 107, 157, 26), (249, 107, 75, 26)]
#: Where a CV reading error sits: in the file card's place, below the drop zone.
CV_STATUS = (428, 458, 664)
BTN_7 = [(1336, 194, 135, 34), (1405, 324, 66, 34), (1405, 454, 66, 34), (1405, 583, 66, 34), (1405, 713, 66, 34)]
#: The "Edit profile" chip beside the step 2 title, as (right, y, w, h): its
#: panel stretches with the window, the fixed-width CV panel to its right does not.
EDIT_2 = (509, 29, 107, 27)

IMPORTANCE = ["Must have", "Important", "Nice to have", "Don’t mind"]

# ───────────────────────── State ─────────────────────────

S = st.session_state
S.setdefault("ob_step", "1")
S.setdefault("ob_prefs", None)  # the Fine-tune rows being edited (see pref_rows)
S.setdefault("ob_swipes", [])  # one verdict per story seen, in story order: "r" | "l" | "u"
S.setdefault("ob_tick", 0)
S.setdefault("ob_uk", "yes")
S.setdefault("ob_filter", 0)
S.setdefault("ob_file", None)  # (name, size in bytes) of the CV read
S.setdefault("ob_cv", None)

#: Work authorization and sponsorship must be declared in step 2 before any
#: later step opens.
GATE = KEYS.index("2")
NEEDS_WORK_AUTH = "Add your work authorization and sponsorship in Edit profile to continue."


def blocked(k: str) -> bool:
    """Whether step `k` lies past step 2 while the declaration is missing."""
    return KEYS.index(k) > GATE and not store.work_auth_complete()


def uk_declared() -> bool:
    """Whether step 2 settled the UK: authorized there, or needing sponsorship.
    Step 6 then has nothing to ask and is skipped."""
    return store.work_auth_complete() and store.uk() in ("yes", "no")


def resolve_step(k: str) -> str:
    """The step `k` leads to: step 6 is skipped once the UK is known."""
    return "7" if k == "6" and uk_declared() else k


qs = st.query_params.get("step")
if qs in KEYS and S.get("_ob_qs") != qs:
    S["_ob_qs"] = qs
    S["ob_step"] = "2" if blocked(qs) else resolve_step(qs)

step = S["ob_step"]
idx = KEYS.index(step)
key, num, info, cta = FLOW[idx]


def finish() -> None:
    """Leaving the wizard for the first time: the guided tour comes next."""
    if store.stage() == "onboarding":
        store.set_stage("tour")
        S["tour_step"] = 0


def go(k: str) -> None:
    if blocked(k):
        st.toast(NEEDS_WORK_AUTH)
        return
    S["ob_step"] = k = resolve_step(k)
    if k == "5":
        S["ob_tick"] = 0


def explored() -> bool:
    """Whether every Explore story has a verdict: Fine-tune waits for it."""
    return len(S["ob_swipes"]) >= len(STORIES["stories"])


def to_fine_tune() -> None:
    """From Explore to Fine-tune, with the rows the swipes now suggest."""
    S["ob_prefs"] = pref_rows()
    go("3a")


#: The answers the shortlist is first ranked with. A UK answer declared in
#: step 2 is used as given; without a declaration the UK starts unanswered.
BEFORE = store.answers() if store.work_auth_complete() else {**store.answers(), "uk_work": None}
AS_OF = d.profile["onboarded"]


#: Shown when a PDF has no usable text. Only text-based PDFs are read: there
#: is no OCR, so a scan fails here rather than reaching the model.
NO_PDF_TEXT = "No usable text was found in this PDF. Scanned PDFs/OCR are not supported in this MVP."


def read_cv(pdf_bytes: bytes) -> None:
    """Extract a profile from an uploaded CV and store it, or store why not.

    The same file uploaded again reuses the stored profile rather than
    calling the model a second time. Failures are stored, never papered over
    with the demo profile.
    """
    # Same hash extract_pdf_text puts on the SourceDocument, so it can be
    # checked before any reading or model call happens.
    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    if store.has_candidate_for(content_hash):
        return
    try:
        document = extract_pdf_text(pdf_bytes, f"cv-{content_hash[:12]}")
    except PdfExtractionError:
        store.set_extraction_error(NO_PDF_TEXT)
        return
    try:
        store.set_candidate(extract_candidate(document, KimiClient()))
    except (ValueError, RuntimeError, ExtractionError) as exc:
        store.set_extraction_error(str(exc))


def overlay(name: str, box, label: str, on_click=None, args=None, shortcut=None) -> bool:
    """A native button covering one element of the mockup at `box`."""
    x, y, w, h = box
    st.markdown(
        f"<style>.stApp .st-key-oo-{name}{{left:{x}px;top:{y}px}}"
        f".stApp .st-key-oo-{name} button{{width:{w}px;height:{h}px}}</style>",
        unsafe_allow_html=True,
    )
    return st.button(label, key=f"oo-{name}", on_click=on_click, args=args, shortcut=shortcut)


# ───────────────────────── Step markup ─────────────────────────


def step1(reading: tuple[str, int] | None = None) -> str:
    """The upload screen. Its file card shows the CV being read (`reading`) or the one read."""
    body = M.S_1
    shown = reading or S["ob_file"]
    card = ""
    if shown:
        name, size = shown
        status, bar = ("Reading your CV…", '<div class="u-pb run"><i></i></div>') if reading else (
            "Read · 100%", '<div class="u-pb"><i style="width:100%"></i></div>')
        card = (
            '<div class="w-card u-file"><span class="u-pdf">PDF</span><div style="flex:1">'
            f'<div style="display:flex;justify-content:space-between"><span class="u-fn">{esc(name)}</span>'
            f'<span class="u-fm">{status}</span></div><div class="u-fm">{max(1, round(size / 1024))} KB</div>{bar}'
            '</div></div>'
        )
    body = body.replace("<!-- CV_FILE_CARD -->", card)
    return body


#: Profile sections read from the CV: card title and CandidateProfile field.
CV_SECTIONS = [("Skills", "skills"), ("Education", "education"), ("Experience", "experience")]
#: The languages card: its title and the pseudo-field its answers are read
#: under (the HC_LANGUAGE eligibility answers, not a CandidateProfile section).
LANGUAGES = ("Languages", "languages")
#: How the languages card names the languages the rule catalogue knows, by
#: ISO 639-1 code. Any other code is shown as the code itself.
LANGUAGE_NAMES = {
    "en": "English", "it": "Italian", "de": "German", "fr": "French",
    "es": "Spanish", "nl": "Dutch", "zh": "Mandarin", "ja": "Japanese",
}
#: How many skills a card lists before summarising the rest as "+N".
SKILL_CHIPS = 8
#: How many entries an education or experience card lists before "+N more".
CARD_LINES = 3
#: How many quotes each section shows on the CV page, which does not scroll.
PAGE_QUOTES = 3

#: The mockup's own icons, by card title, and its source-line document icon.
ICONS = {title: icon for icon, title in re.findall(r'<div class="ic">(.*?)</div><b>(.*?)</b>', M.S_2)}
DOC_ICON = re.search(r'<div class="p-src">(<svg.*?</svg>)', M.S_2).group(1)
FOUND = '<span class="w-b ok"><i></i>Found</span>'
NOT_FOUND = '<span class="w-b ne"><i></i>Not found</span>'
NOT_READ = '<span class="w-b ne"><i></i>Not read</span>'
DECLARED = '<span class="w-b ok"><i></i>Declared</span>'
REQUIRED = '<span class="w-b am"><i></i>Required</span>'
#: Hover text of a value the user edited, which no CV quote backs.
EDITED = "Edited by you"
PENCIL = (
    '<svg width="12" height="12" viewBox="0 0 16 16"><path d="M10.5 2.5l3 3L6 13H3v-3z" stroke="currentColor" '
    'stroke-width="1.5" fill="none" stroke-linejoin="round"/></svg>'
)


def profile_card(title: str, badge: str, body: str, src: str = "") -> str:
    source = f'<div class="p-src">{DOC_ICON}{src}</div>' if src else ""
    return (
        f'<div class="w-card p-s"><div class="p-h"><div class="ic">{ICONS[title]}</div>'
        f"<b>{title}</b>{badge}</div>{body}{source}</div>"
    )


def fact_quote(profile, fact) -> str:
    """The CV text a fact rests on, for hovering over the fact."""
    if store.is_edited(profile, fact):
        return EDITED
    quotes = {e.evidence_id: e.quote for e in profile.provenance.evidence}
    return " … ".join(" ".join(quotes[i].split()) for i in fact.evidence_ids)


def section_facts(profile, field: str) -> list:
    """What one card shows: a CandidateProfile section, or for "languages"
    the HC_LANGUAGE answers the CV stated."""
    if field == LANGUAGES[1]:
        return list(profile.eligibility_answers.get(LANGUAGE_CONSTRAINT_ID, []))
    return getattr(profile, field)


def section_quotes(profile, field: str) -> list[str]:
    """The distinct CV quotes behind one section, in order. Several facts
    often rest on the same line of the CV; that line counts once. Values the
    user edited rest on no CV quote and are left out."""
    facts = [f for f in section_facts(profile, field) if not store.is_edited(profile, f)]
    return list(dict.fromkeys(fact_quote(profile, f) for f in facts))


def language_label(answer) -> str:
    """The language and its level on the scale the CV stated it on, e.g.
    "English · C1" or "Mandarin · HSK 4", or that no level could be read."""
    code = answer.answer_key.removeprefix("level_")
    level = LanguageLevel.parse(answer.value)
    return f"{LANGUAGE_NAMES.get(code, code.upper())} · {level.label if level else 'level not stated'}"


def quote_count(n: int) -> str:
    return f"{n} quote{'s' if n != 1 else ''}"


def swap(body: str, pattern: str, new: str) -> str:
    """Replace the one fragment of mockup markup `pattern` matches.

    Raises:
        RuntimeError: If the fragment is missing. The mockup's own content is
            the demo candidate's, so a silent miss would show it as extracted.
    """
    # A function, so backslashes in CV text are never read as group references.
    out, n = re.subn(pattern, lambda _m: new, body, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f"Step 2 mockup markup has changed: nothing matches {pattern!r}.")
    return out


def cv_card(profile, title: str, field: str) -> str:
    """A card for one section read from the CV: its facts, or why there are none."""
    if profile is None:
        return profile_card(title, NOT_READ, '<div class="p-v">Upload your CV in step 1</div>')
    facts = section_facts(profile, field)
    if not facts:
        return profile_card(title, NOT_FOUND, '<div class="p-v">Not stated in your CV</div>')
    text = language_label if field == LANGUAGES[1] else (lambda fact: fact.value)

    def item(fact, tag: str, cls: str = "") -> str:
        return f'<{tag}{cls} title="{esc(fact_quote(profile, fact))}">{esc(text(fact))}</{tag}>'

    if field in ("skills", LANGUAGES[1]):
        chips = "".join(item(f, "span", ' class="w-chip"') for f in facts[:SKILL_CHIPS])
        if len(facts) > SKILL_CHIPS:
            chips += f'<span class="w-chip">+{len(facts) - SKILL_CHIPS}</span>'
        body = f'<div class="p-chips">{chips}</div>'
    else:  # one line per entry, so three roles read as three roles
        body = "".join(item(f, "div", ' class="p-v p-e"') for f in facts[:CARD_LINES])
        if len(facts) > CARD_LINES:
            body += f'<div class="p-m">+{len(facts) - CARD_LINES} more</div>'
    quotes = len(section_quotes(profile, field))
    edited = sum(store.is_edited(profile, f) for f in facts)
    src = [f"From your CV · {quote_count(quotes)}"] if quotes else []
    src += [f"{edited} edited by you"] if edited else []
    return profile_card(title, FOUND, body, " · ".join(src))


def country_list(codes: list[str]) -> str:
    """Declared countries as the user chose them: the EU as one entry."""
    eu = store.eu_codes()
    names = ["EU"] if set(eu) <= set(codes) else []
    names += [store.country_name(c) for c in codes if not (names and c in eu)]
    return ", ".join(names)


def work_auth_cards() -> list[str]:
    """The work authorization and sponsorship cards: the user's declaration,
    or a note that it is required before continuing."""
    decl = store.work_auth()
    if decl is None:
        body = '<div class="p-v">Required · add it in Edit profile</div>'
        return [profile_card(t, REQUIRED, body) for t in ("Work authorization", "Sponsorship")]
    authorized = country_list(decl["authorized"]) or "None of our countries"
    sponsorship = country_list(decl["sponsorship"]) or "Not needed anywhere"
    return [
        profile_card("Work authorization", DECLARED, f'<div class="p-v">{esc(authorized)}</div>', "Declared by you"),
        profile_card("Sponsorship", DECLARED, f'<div class="p-v">{esc(sponsorship)}</div>', "Declared by you"),
    ]


def languages_card(profile) -> str:
    """The languages the CV stated, each with its level and the quote it came
    from. A read CV that states none says so, like any other CV section."""
    if profile is None:
        return profile_card(LANGUAGES[0], NOT_READ, '<div class="p-v">Not read from your CV</div>')
    return cv_card(profile, *LANGUAGES)


def cv_page(profile) -> str:
    """The CV panel: the quotes each section was read from, highlighted."""
    if profile is None:
        return '<div class="p-m" style="margin-top:0">Quotes from your CV appear here once it has been read.</div>'
    filler = '<div class="p-ln" style="width:92%"></div><div class="p-ln" style="width:78%"></div>'
    blocks = []
    for title, field in [*CV_SECTIONS, LANGUAGES]:
        quotes = section_quotes(profile, field)
        if not quotes:
            continue
        shown = "".join(
            f'<div style="font-size:12px;line-height:1.5;color:var(--t1)">{esc(q)}</div>' for q in quotes[:PAGE_QUOTES]
        )
        if len(quotes) > PAGE_QUOTES:
            shown += f'<div style="font-size:11.5px;color:var(--t3)">+{len(quotes) - PAGE_QUOTES} more</div>'
        blocks.append(f'<div class="p-hl b"><span class="tg">{title}</span>{shown}</div>')
    return filler.join(blocks)


def step2() -> str:
    """What was read from the CV, each value backed by the quote it came from.

    Nothing here comes from the demo profile. Sections the CV extraction does
    not read are marked as such rather than filled in.
    """
    profile = store.candidate()
    body = M.S_2
    if profile is None:
        sub = "No CV read yet. <b>Upload your CV in step 1</b> to fill in your profile."
        quotes = "Not uploaded"
    else:
        found = sum(bool(getattr(profile, field)) for _, field in CV_SECTIONS)
        sub = f"{found} of {len(CV_SECTIONS)} sections found in your CV. <b>Each value is backed by a quote from it.</b>"
        distinct = {q for _, field in [*CV_SECTIONS, LANGUAGES] for q in section_quotes(profile, field)}
        quotes = quote_count(len(distinct))
    cards = [cv_card(profile, title, field) for title, field in CV_SECTIONS] + work_auth_cards() + [languages_card(profile)]
    # Always offered: without a CV the editor still takes the mandatory declaration.
    body = swap(
        body, re.escape('<div class="w-h1">Here’s what we found</div>'),
        f'<div class="p-top"><div class="w-h1">Here’s what we found</div>'
        f'<span class="w-chip p-edit">{PENCIL}Edit profile</span></div>',
    )
    body = swap(body, r'<div class="w-sub">.*?</div>', f'<div class="w-sub">{sub}</div>')
    body = swap(
        body, r'<div class="p-grid">.*?</div></div>\n<div class="p-r">',
        f'<div class="p-grid">{"".join(cards)}</div></div>\n<div class="p-r">',
    )
    body = swap(body, re.escape("Your CV<span>Page 2 of 2</span>"), f"Your CV<span>{quotes}</span>")
    return swap(body, r'<div class="p-page">.*?</div></div>$', f'<div class="p-page">{cv_page(profile)}</div></div>')


#: The editor's tabs: title, CandidateProfile field, entry icon and add button
#: label. Skills are chips; the other entries have one field per part.
EDIT_TABS = [
    ("Experience", "experience", ":material/work:", "Add experience"),
    ("Education", "education", ":material/school:", "Add education"),
    ("Skills", "skills", None, None),
]
#: Sections whose entries have their own fields, with the label of each part
#: of the value (store.split_entry).
EDIT_PARTS = {
    "experience": ("Role", "Company", "Dates"),
    "education": ("Degree", "Institution", "Dates"),
}


#: Placeholder examples for each part of an entry.
EDIT_EXAMPLES = {
    "experience": ("Strategy Consultant", "Accenture", "Jun 2026 – Aug 2026"),
    "education": ("MSc in International Management", "Fudan University", "Sep 2025 – Jul 2027"),
}


#: The work authorization tab: its title and the "none" choice of each question.
WORK_TAB = "Work authorization"
NONE = "NONE"


def work_auth_choices() -> tuple[list[str], list[str]]:
    """Pill options: authorization offers the EU as one choice, then the other
    countries; sponsorship offers every country. Both end with "none"."""
    others = [c["code"] for c in store.markets() if not c["eu"]]
    return ["EU", *others, NONE], [c["code"] for c in store.markets()] + [NONE]


def work_auth_label(value: str) -> str:
    if value == "EU":
        return "EU · all EU countries"
    return "None of these" if value == NONE else store.country_name(value)


def draft_work_auth() -> None:
    """Fill the two questions from the saved declaration, or leave them blank."""
    decl = store.work_auth()
    if decl is None:
        S["ed-wa-auth"], S["ed-wa-sp"] = [], []
        return
    eu = store.eu_codes()
    auth = (["EU"] if set(eu) <= set(decl["authorized"]) else []) + [
        c for c in decl["authorized"] if c not in eu]
    S["ed-wa-auth"] = auth or [NONE]
    S["ed-wa-sp"] = list(decl["sponsorship"]) or [NONE]


def read_work_auth() -> tuple[list[str], list[str]]:
    """The two answers as country codes, the EU expanded.

    Raises:
        ValueError: If a question is unanswered or mixes "none" with countries.
    """
    answers = []
    for key, question in (("ed-wa-auth", "where you are currently authorized to work"),
                          ("ed-wa-sp", "where you would require employer sponsorship")):
        chosen = list(S.get(key) or [])
        if not chosen:
            raise ValueError(f"Tell us {question}, or choose “None of these”.")
        if NONE in chosen and len(chosen) > 1:
            raise ValueError(f"“None of these” can’t be combined with countries ({question}).")
        answers.append([] if chosen == [NONE] else chosen)
    authorized, sponsorship = answers
    if "EU" in authorized:
        authorized = [*store.eu_codes(), *(c for c in authorized if c != "EU")]
    return authorized, sponsorship


def open_editor() -> None:
    """Start a draft of the CV sections and the work authorization answers.
    The editor changes the draft only; the profile changes on "Save changes",
    so Cancel or closing loses nothing."""
    profile = store.candidate()
    S["ed_draft"] = (
        {field: [f.value for f in getattr(profile, field)] for _, field in CV_SECTIONS} if profile else {}
    )
    S["ed_rev"] = S.get("ed_rev", 0) + 1
    S["ed-skill-new"] = ""
    S.pop("ed_error", None)
    draft_work_auth()


def entry_key(field: str, i: int, part: int) -> str:
    # The revision renumbers every field after a removal, so no field keeps
    # the text of the entry that was above it.
    return f"ed-{field}-{S['ed_rev']}-{i}-{part}"


def sync_draft() -> None:
    """Copy what was typed into the draft, before the draft changes shape."""
    if not S["ed_draft"]:  # no CV: only the work authorization tab
        return
    for field in EDIT_PARTS:
        S["ed_draft"][field] = [
            store.join_entry(*(S.get(entry_key(field, i, n), part) for n, part in enumerate(store.split_entry(v))))
            for i, v in enumerate(S["ed_draft"][field])
        ]


def add_entry(field: str) -> None:
    sync_draft()
    S["ed_draft"][field].append("")


def remove_entry(field: str, i: int) -> None:
    sync_draft()
    del S["ed_draft"][field][i]
    S["ed_rev"] += 1


def remove_skill(i: int) -> None:
    sync_draft()
    del S["ed_draft"]["skills"][i]
    S["ed_rev"] += 1


def take_skill() -> None:
    """Add the skill typed in the skill field to the draft, once."""
    value = " ".join(S.get("ed-skill-new", "").split())
    if value and value not in S["ed_draft"]["skills"]:
        S["ed_draft"]["skills"].append(value)


def add_skill() -> None:
    take_skill()
    S["ed-skill-new"] = ""  # allowed here: callbacks run before the field is drawn


def save_editor() -> None:
    """Save everything, or nothing: the work authorization answers are
    mandatory, so an incomplete tab keeps the editor open with the reason."""
    try:
        authorized, sponsorship = read_work_auth()
        store.set_work_auth(authorized, sponsorship)
    except ValueError as exc:
        S["ed_error"] = str(exc)
        return
    S.pop("ed_error", None)
    S["ob_uk"] = store.uk_from_work_auth()  # step 6 starts from the declared answer
    if S["ed_draft"]:
        sync_draft()
        take_skill()  # one typed but not yet added with Enter
        store.save_edits(S["ed_draft"])
    S.pop("ed_draft")


def cancel_editor() -> None:
    S.pop("ed_draft", None)
    S.pop("ed_error", None)


def clear_error() -> None:
    """An answer changed: the last save's error no longer applies."""
    S.pop("ed_error", None)


def work_auth_tab() -> None:
    """The mandatory questions. Declared by the user, never read from the CV
    or inferred from citizenship."""
    auth, sponsor = work_auth_choices()
    st.markdown(
        '<div class="ed-sub">Required to continue. Countries you leave out count as “no”.</div>',
        unsafe_allow_html=True,
    )
    st.pills("In which countries are you currently authorized to work?", auth, selection_mode="multi",
             key="ed-wa-auth", format_func=work_auth_label, help="Choosing EU selects every EU country we cover.",
             on_change=clear_error)
    st.pills("In which countries would you require employer sponsorship?", sponsor, selection_mode="multi",
             key="ed-wa-sp", format_func=work_auth_label, on_change=clear_error)


@st.dialog("Edit your profile", width="large")
def edit_profile() -> None:
    """Change what was read from the CV: edit, add or remove entries.

    Values the CV does not say are saved as the user's own statements, apart
    from the CV quotes (store.apply_edits)."""
    if "ed_draft" not in S:  # saved or cancelled: close
        st.rerun()
    draft = S["ed_draft"]
    sub = (
        "Review what we read from your CV. What you change is saved as your own statement, not as read from your CV."
        if draft else "Tell us where you can work. Your answers are saved as your own statement."
    )
    st.markdown(f'<div class="ed-sub">{sub}</div>', unsafe_allow_html=True)
    cv_tabs = EDIT_TABS if draft else []
    names = [t for t, *_ in cv_tabs] + [WORK_TAB]
    shown = st.tabs(names, key="ed-tabs", default=None if store.work_auth_complete() else WORK_TAB)
    with shown[-1]:
        work_auth_tab()
    for tab, (title, field, icon, add) in zip(shown, cv_tabs):
        with tab:
            if icon is None:  # skills
                with st.container(key="ed-chips", horizontal=True, gap="small"):
                    for i, skill in enumerate(draft["skills"]):
                        st.button(skill, icon=":material/close:", key=f"ed-chip-{S['ed_rev']}-{i}",
                                  on_click=remove_skill, args=(i,), help="Remove")
                st.text_input("Add a skill", key="ed-skill-new", placeholder="Add a skill and press Enter",
                              label_visibility="collapsed", on_change=add_skill, icon=":material/add:")
                continue
            if not draft[field]:
                st.markdown(f'<div class="ed-none">No {title.lower()} yet.</div>', unsafe_allow_html=True)
            labels = EDIT_PARTS[field]
            for i, value in enumerate(draft[field]):
                parts = store.split_entry(value)
                with st.container(key=f"ed-row-{field}-{i}"):
                    with st.container(horizontal=True, vertical_alignment="bottom"):
                        st.text_input(labels[0], value=parts[0], key=entry_key(field, i, 0), icon=icon,
                                      placeholder=f"e.g. {EDIT_EXAMPLES[field][0]}")
                        st.button("", icon=":material/delete:", key=f"ed-del-{field}-{S['ed_rev']}-{i}",
                                  type="tertiary", on_click=remove_entry, args=(field, i), help="Remove")
                    with st.container(horizontal=True):
                        for n in (1, 2):
                            st.text_input(labels[n], value=parts[n], key=entry_key(field, i, n),
                                          placeholder=f"e.g. {EDIT_EXAMPLES[field][n]}")
            st.button(add, icon=":material/add:", key=f"ed-add-{field}", on_click=add_entry, args=(field,))
    if S.get("ed_error"):
        st.error(S["ed_error"], icon=":material/error:")
    with st.container(key="ed-foot", horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
        st.button("Cancel", key="ed-cancel", type="tertiary", on_click=cancel_editor)
        st.button("Save changes", key="ed-save", type="primary", on_click=save_editor)


#: Fine-tune weight bar shades, strongest first: (fill, ink). Mockup blues,
#: mapped to the palette on the way out like every other colour.
SHADES = [("#0071E3", "#fff"), ("#5AA2F0", "#fff"), ("#A9CDF7", "#0B3F7A"),
          ("#D6E7FB", "#0B3F7A"), ("#EEF4FC", "#0B3F7A"), ("#F7FAFF", "#0B3F7A")]
SUGGESTED = "Suggested by your swipes"
NO_MATCH = ('<svg width="12" height="12" viewBox="0 0 16 16"><path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="#AEAEB2" '
            'stroke-width="1.8" stroke-linecap="round"/></svg>')


def pref_rows() -> list[dict]:
    """The Fine-tune rows (D-045): the role families and industries the likes
    suggest, then the profile's cities and hybrid work. A row the candidate
    already set keeps its level."""
    stories, verdicts = STORIES["stories"], S["ob_swipes"]
    fams, _ = explore.direction(stories, verdicts)
    cities = list(d.profile["preferred_cities"])
    rows = [{"field": "role_family", "values": [f], "label": f"{f} roles", "hint": SUGGESTED, "level": "important"} for f in fams]
    rows += [{"field": "industry", "values": [i], "label": i, "hint": SUGGESTED, "level": "important"}
             for i in explore.industries(stories, verdicts)]
    rows.append({"field": "city", "values": cities, "label": ", ".join(cities[:-1]) + " or " + cities[-1] if len(cities) > 1 else cities[0],
                 "hint": "From your profile", "level": "important"})
    rows.append({"field": "mode", "values": ["Hybrid"], "label": "Hybrid work", "hint": "Some days in the office", "level": "nice"})
    before = {(r["field"], tuple(r["values"])): r["level"] for r in (S["ob_prefs"] or store.preferences() or [])}
    return [dict(r, level=before.get((r["field"], tuple(r["values"])), r["level"])) for r in rows]


def weight(r: dict) -> float:
    return ranking.IMPORTANCE_WEIGHT[r["level"]]


def pref_row(r: dict) -> str:
    on = ranking.IMPORTANCE.index(r["level"])
    spans = "".join(
        f'<span class="{"on" + (" must" if i == 0 else " imp" if i == 1 else "") if i == on else ""}">{t}</span>'
        for i, t in enumerate(IMPORTANCE)
    )
    return f'<div class="v3-r"><div class="k">{esc(r["label"])}<small>{esc(r["hint"])}</small></div><div class="v3-seg">{spans}</div></div>'


def short(r: dict) -> str:
    """A row's name in the two-column weight legend."""
    return {"city": "Location", "mode": "Hybrid work"}.get(r["field"], r["values"][0])


def weights_box(rows: list[dict], total: float) -> str:
    """How preference fit splits between the rows that carry weight."""
    if not total:
        return '<div class="v3-nt">Mark at least one preference to see how your fit is built.</div>'
    held = [(r, 100 * weight(r) / total) for r in rows if weight(r)]
    bar = "".join(
        f'<i style="flex:{s:.1f};background:{SHADES[i][0]};color:{SHADES[i][1]}">{f"{s:.0f}%" if s >= 9 else ""}</i>'
        for i, (_, s) in enumerate(held)
    )
    legend = "".join(
        f'<span><i style="background:{SHADES[i][0]}{";border:1px solid #D6E7FB" if i >= 4 else ""}"></i>'
        f'{esc(short(r))}<b>{s:.0f}%</b></span>'
        for i, (r, s) in enumerate(held)
    )
    return f'<div class="v3-wb">{bar}</div>\n<div class="v3-wl">{legend}</div>'


def example_box(rows: list[dict], total: float) -> str:
    """The demo role these rows fit best, and which of them it meets."""
    head = '<div class="v3-box"><div class="w-lab">Example · how a role reads you<span>Preference fit</span></div>'
    if not total:
        return head + '<div class="v3-nt">No preference carries weight yet.</div></div>'
    roles = [v for v in store.views(None, AS_OF) if v.standing != "excluded"]
    fit = {v.id: ranking.preference_fit(v.role.raw, rows)[0] for v in roles}
    v = ranking.order(roles, lambda v: fit[v.id])[0]
    checks = "".join(
        f'<div>{CK12 if v.get(r["field"]) in r["values"] else NO_MATCH}{esc(r["label"])}'
        f'<span>{100 * weight(r) / total:.0f}%</span></div>'
        for r in rows if weight(r)
    )
    return (
        head + '<div style="display:flex;align-items:center;gap:12px">'
        f'<span class="w-logo" style="background:{v.bg};width:34px;height:34px">{v.mono}</span>'
        f'<div style="flex:1"><div style="font-size:13.5px;font-weight:600">{esc(v.title)}</div>'
        f'<div style="font-size:12px;color:var(--t2)">{esc(v.company)} · {esc(v.city)} · {esc(v.mode)}</div></div>'
        f'<span style="font-size:24px;font-weight:700;letter-spacing:-0.03em">{fit[v.id]}</span></div>'
        f'<div class="v3-ck">{checks}</div></div>'
    )


def step3a() -> str:
    """Fine-tune: how much each suggested or declared preference matters."""
    rows = S["ob_prefs"]
    total = sum(weight(r) for r in rows)
    body = M.S_3A
    body = swap(
        body, r'<span class="segm">.*?</span></span>',
        '<span class="segm"><span data-go="3b" style="cursor:pointer">1 · Explore</span><span class="on">2 · Fine-tune</span></span>',
    )
    body = swap(
        body, re.escape("Describe it in your own words. We turn it into preferences you can see and adjust."),
        "Your swipes suggested the first rows. Set how much each one matters: only what you confirm here shapes your ranking.",
    )
    # The free-text description is gone: Explore is where preferences start.
    body = swap(body, r'<div><div class="v3-sec"><span class="n">1</span>Your ideal internship.*?(?=<div><div class="v3-sec"><span class="n">2</span>)', "")
    body = swap(
        body, re.escape('<span class="n">2</span>How much each one matters<span>Must-haves filter roles · the rest shape your ranking</span>'),
        '<span class="n">1</span>How much each one matters<span>Preferences order your roles · they never filter them</span>',
    )
    note = "" if any(r["hint"] == SUGGESTED for r in rows) else (
        '<div class="v3-nt">Your swipes don’t point to a role type or industry yet. '
        'Like a few stories in Explore to get suggestions.</div>'
    )
    body = swap(body, r'<div class="v3-tb">.*?(?=\n<div class="v3-el">)',
                f'<div class="v3-tb">{"".join(pref_row(r) for r in rows)}</div>{note}</div>')
    body = swap(
        body, re.escape("<b>312</b><span>roles fit · 41 unpaid removed by your must-have</span>"),
        f"<b>{len(store.views(None, AS_OF))}</b><span>demo roles · your preferences only change their order</span>",
    )
    body = swap(body, r'<div class="v3-wb">.*?</div>\n<div class="v3-wl">.*?</span></div>', weights_box(rows, total))
    return swap(body, r'<div class="v3-box"><div class="w-lab">Example · how a role reads you.*?(?=\n<div style="flex:1"></div>)',
                example_box(rows, total))


def story_card(s: dict) -> str:
    """The story on top of the stack. "Why" names the CV skills it uses, if any."""
    tags = "".join(f'<span class="w-b ne">{esc(t)}</span>' for t in s["tags"])
    sk = "".join(f'<span class="w-chip">{esc(t)}</span>' for t in s["sk"])
    profile = store.candidate()
    shared = explore.cv_overlap(s, [f.value for f in profile.skills]) if profile else []
    why = (
        "your CV mentions " + " and ".join(f"<b>{esc(k)}</b>" for k in shared[:2]) if shared
        else f"it shows a day in <b>{esc(s['tags'][0])}</b>"
    )
    return (
        f'<div class="sw-card"><span class="stamp">I’D ENJOY THIS</span><div class="cd-tags">{tags}</div>'
        f'<div class="cd-time">{esc(s["time"])}</div><div class="cd-h">{esc(s["h"])}</div>'
        f'<div class="cd-p">{esc(s["p"])}</div><div class="cd-viz">{s["viz"]}</div>'
        f'<div class="cd-sk"><span class="k">You’d use</span>{sk}</div>'
        '<div class="cd-why"><svg width="12" height="12" viewBox="0 0 16 16"><path d="M8 2.2 9.3 6.7 13.8 8 9.3 9.3 8 '
        '13.8 6.7 9.3 2.2 8 6.7 6.7z" fill="#0071E3"/></svg>'
        f'<span>Why this story: {why}</span></div></div>'
    )


def done_card(verdicts: list[str]) -> str:
    """What replaces the stack once every story has a verdict."""
    n = {v: verdicts.count(v) for v in explore.VERDICTS}
    return (
        f'<div class="sw-card sw-done"><div class="cd-time">All {len(verdicts)} stories</div>'
        '<div class="cd-h">That’s every story for now.</div>'
        f'<div class="cd-p">You’d enjoy {n[explore.LIKE]}, passed on {n[explore.PASS]} and weren’t sure about '
        f'{n[explore.UNSURE]}. What we learned is on the right. Continue to confirm what matters to you.</div></div>'
    )


#: The RIASEC radar: centre, radius and label anchors, as the mockup draws it.
RADAR_C, RADAR_R = (190.0, 122.0), 92.0
RADAR_LABELS = [(190.0, 18.0, "middle"), (283.5, 72.0, "start"), (283.5, 180.0, "start"),
                (190.0, 234.0, "middle"), (96.5, 180.0, "end"), (96.5, 72.0, "end")]


def radar_xy(i: int, r: float) -> tuple[float, float]:
    a = math.radians(-90 + 60 * i)
    return RADAR_C[0] + r * math.cos(a), RADAR_C[1] + r * math.sin(a)


def radar(values: list[float]) -> str:
    """The RIASEC hexagon for `values` (shares of the radius); the strongest two in bold."""

    def ring(r: float) -> str:
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (radar_xy(i, r) for i in range(6)))

    grid = "".join(f'<polygon points="{ring(RADAR_R * k / 3)}" fill="none" stroke="#E5E5EA" stroke-width="1"/>' for k in (1, 2, 3))
    spokes = "".join(
        f'<line x1="{RADAR_C[0]:g}" y1="{RADAR_C[1]:g}" x2="{x:.1f}" y2="{y:.1f}" stroke="#EFEFF2"/>'
        for x, y in (radar_xy(i, RADAR_R) for i in range(6))
    )
    pts = [radar_xy(i, RADAR_R * v) for i, v in enumerate(values)]
    shape = (
        f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="rgba(0,113,227,.12)" '
        'stroke="#0071E3" stroke-width="1.8" stroke-linejoin="round"/>'
        + "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#0071E3"/>' for x, y in pts)
    )
    top = explore.top_interests(values)
    labels = "".join(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="11.5" font-weight="{700 if i in top else 500}" '
        f'fill="{"#1D1D1F" if i in top else "#6E6E73"}" font-family="-apple-system,Inter,sans-serif">{name}</text>'
        for i, ((x, y, anchor), name) in enumerate(zip(RADAR_LABELS, explore.RIASEC))
    )
    return f'<svg width="370" height="246" viewBox="0 0 380 246">{grid}{spokes}{shape}{labels}</svg>'


def role_count(match: str) -> str:
    n = sum(match.lower() in v.title.lower() for v in store.views())
    return f"{n} demo role{'s' if n != 1 else ''}" if n else "no demo roles yet"


def direction_box(dirs: list[str], role: dict | None) -> str:
    if not dirs:
        return (
            '<div style="font-size:14px;font-weight:620;color:var(--t3)">Not clear yet</div>'
            '<div style="font-size:12px;color:var(--t2);margin-top:3px">Swipe right on stories you’d enjoy to see where they point.</div>'
        )
    return (
        f'<div style="font-size:14px;font-weight:620">{" · ".join(esc(d) for d in dirs)}</div>'
        f'<div style="font-size:12px;color:var(--t2);margin-top:3px">Role type to consider: '
        f'<b style="color:var(--blue);font-weight:600">{esc(role["role"])}</b> · {role_count(role["match"])}</div>'
    )


#: Roughly how long one story takes to read and swipe, in seconds.
STORY_SECONDS = 8


def time_left(remaining: int) -> str:
    if remaining <= 0:
        return "all done"
    secs = remaining * STORY_SECONDS
    return "less than a minute left" if secs < 60 else f"about {round(secs / 60)} minute{'s' if secs >= 90 else ''} left"


def step3b() -> str:
    """The story stack and, beside it, everything the verdicts so far say."""
    stories, verdicts = STORIES["stories"], S["ob_swipes"]
    total, seen = len(stories), len(verdicts)
    done = seen >= total
    body = M.S_3B
    story_n = f"All {total} stories" if done else f"Story {seen + 1} of {total}"
    body = swap(body, re.escape("<b>Story 8 of 12</b> · about 1 minute left"), f"<b>{story_n}</b> · {time_left(total - seen)}")
    bars = "".join(f'<i class="{"d" if i < seen else "c" if i == seen else ""}"></i>' for i in range(total))
    body = swap(body, r'<div class="sw-pb">.*?</div>', f'<div class="sw-pb">{bars}</div>')
    behind = total - seen - 1  # cards still under the top one
    backs = ('<div class="sw-cb b2"></div>' if behind >= 2 else "") + ('<div class="sw-cb b1"></div>' if behind >= 1 else "")
    body = swap(
        body, r'<div class="sw-stack">.*?</div></div>\s*<div class="acts">',
        f'<div class="sw-stack">{backs}{done_card(verdicts) if done else story_card(stories[seen])}</div>\n<div class="acts{" off" if done else ""}">',
    )
    body = swap(body, re.escape("Live · from 7 swipes"), f"Live · from {seen} swipe{'s' if seen != 1 else ''}")
    body = swap(body, r'<svg width="370" height="246".*?</svg>', radar(explore.interests(stories, verdicts)))

    def bp(label: list[str], pos: float) -> str:
        side = explore.leaning(pos)
        lt = f"<b>{label[0]}</b>" if side == "l" else label[0]
        rt = f"<b>{label[1]}</b>" if side == "r" else label[1]
        return f'<div class="bp"><span>{lt}</span><span class="tr"><i style="left:{pos:.0f}%"></i></span><span>{rt}</span></div>'

    rows = iter(zip(STORIES["sliders"], explore.sliders(stories, verdicts)))
    body, n = re.subn(r'<div class="bp">.*?</span></div>', lambda _m: bp(*next(rows)), body, flags=re.S)
    if n != len(STORIES["sliders"]):
        raise RuntimeError(f"Step 3b mockup markup has changed: {n} work-design sliders, not {len(STORIES['sliders'])}.")
    hist = "".join(f'<span class="{c}">{"✓" if c == "y" else "✕"} {esc(t)}</span>' for c, t in explore.history(stories, verdicts))
    hist = hist or '<span class="e">Nothing yet</span>'
    body = swap(body, r'<div class="hist">.*?</div>', f'<div class="hist">{hist}</div>')
    lab = '<div class="w-lab">Emerging direction<span>Updates each swipe</span></div>'
    body = swap(body, re.escape(lab) + r".*?</div></div>", lab + direction_box(*explore.direction(stories, verdicts)) + "</div>")
    # Likes only suggest preferences; they count once confirmed in Fine-tune (D-045).
    body = swap(
        body, re.escape("This is for you, not employers. It adjusts your Preference fit only — you review it before it’s used."),
        "Just for you. Your likes suggest role types and industries: you confirm them next.",
    )
    tune = ' data-go="3a" style="cursor:pointer"' if done else ' class="off"'
    return swap(
        body, re.escape('<span class="segm"><span data-go="3a" style="cursor:pointer">1 · Describe</span><span class="on">2 · Explore</span></span>'),
        f'<span class="segm"><span class="on">1 · Explore</span><span{tune}>2 · Fine-tune</span></span>',
    )


def funnel_row(label: str, small: str, width: float, n: int, color: str) -> str:
    return (
        f'<div class="f4"><div class="k">{label}<small>{small}</small></div>'
        f'<div class="f4b"><i style="width:{width:.1f}%;background:{color}"></i></div><div class="n">{n}</div></div>'
    )


def step4() -> str:
    """The analysis funnel, counted over the demo roles actually available.

    The demo has no larger catalogue behind it, so every number here is a
    count of those roles under the same checks the other screens run.
    """
    c = store.counts(None, AS_OF)
    total = sum(c.values())
    ranked = c["eligible"] + c["verify"]
    share = 100 * ranked / total if total else 0
    fun = (
        '<div class="fun">\n'
        + funnel_row("Roles in the demo data", "Synthetic postings · not a live catalogue", 100, total, "#D1D1D6")
        + funnel_row("Checked for eligibility", "Mandatory requirements", 100, total, "#6E6E73")
        + '<div class="f4"><div class="k">Eligibility result<small>Fixed rules</small></div><div class="f4b" style="background:none">'
        f'<i style="flex:{c["eligible"]};background:#30A14E;border-radius:6px"></i>'
        f'<i style="flex:{c["verify"]};background:#E3A03A;border-radius:6px"></i>'
        f'<i style="flex:{c["excluded"]};background:repeating-linear-gradient(135deg,#F3C9C5 0 3px,#FBEAE8 3px 6px);border-radius:6px"></i>'
        f'</div><div class="n">{total}</div></div>'
        f'<div class="lg4"><span><i style="background:#30A14E"></i>{c["eligible"]} eligible</span>'
        f'<span><i style="background:#E3A03A"></i>{c["verify"]} to verify</span>'
        f'<span><i style="background:#F3C9C5"></i>{c["excluded"]} excluded · conflict</span></div>'
        + funnel_row("Ranked for you", "Eligible + to verify", share, ranked, "var(--blue);border-radius:9px")
        .replace('<div class="n">', '<div class="n" style="color:var(--blue)">')
        + '\n</div></div>\n<div class="a4-r">'
    )
    first = "".join(
        f'<div style="display:flex;align-items:center;gap:12px{";margin-top:12px" if i else ""}">'
        f'<span class="w-logo" style="background:{v.bg};width:34px;height:34px">{v.mono}</span>'
        f'<div style="flex:1"><div style="font-size:13.5px;font-weight:600">{esc(v.title)}</div>'
        f'<div style="font-size:12px;color:var(--t2)">{esc(v.company)} · {esc(v.city)}</div></div>'
        f'<span style="font-size:22px;font-weight:700;letter-spacing:-0.03em">{v.shown}</span></div>'
        for i, v in enumerate(store.ranked(BEFORE, AS_OF)[:2])
    )
    body = M.S_4
    body = swap(body, r'<div class="fun">.*?\n</div></div>\n<div class="a4-r">', fun)
    body = swap(
        body, r'<div class="w-lab">First results<span>Updating</span></div>.*?</div>\n<div class="w-tip">',
        f'<div class="w-lab">First results<span>Updating</span></div>{first}</div>\n<div class="w-tip">',
    )
    body = swap(body, "from 312 postings", f"from {total} postings")
    body = swap(body, "78 roles · 23 conflicts removed", f"{total} roles · {c['excluded']} conflict{'s' if c['excluded'] != 1 else ''} removed")
    return swap(body, "Rank 55 roles", f"Rank {ranked} roles")


def shortlist_roles():
    return store.ranked(BEFORE, AS_OF)[:5]


def cc_card(v, cls: str, first_verify: bool) -> str:
    badge = '<span class="w-b ok"><i></i>Eligible</span>' if v.standing == "eligible" else '<span class="w-b am"><i></i>To verify</span>'
    delta = f"{v.raw_shown} − {d.penalty:g} until verified" if v.standing == "verify" else ""
    segs = "".join(f'<i style="flex:{p:.1f};background:{parts.COL[i]}"></i>' for i, p in enumerate(v.parts))
    segs += f'<i style="flex:{max(0, 100 - v.score):.1f}"></i>'
    checks = "".join(
        f'<div>{CK12 if k == "ok" else WN12}<span>{esc(t)}</span></div>' for k, t in v.card_checks
    )
    kind, auth = parts.work_auth_check(v)
    if kind != "ok":
        checks += f'<div>{WN12}<span>{esc(auth)}</span></div>'
    n = clock.days_until(v.closes)
    close = (
        f'<div class="cc-pill u">Closes in {n} days<small>{esc(" ".join(v.closes_label.split()[-2:]))}</small></div>'
        if n <= 9 else f'<div class="cc-pill">Closes {esc(v.closes_label)}<small></small></div>'
    )
    need = ""
    if v.standing == "verify":
        text = "One answer from you could make this your #1" if first_verify else "Same answer unlocks this role"
        need = f'<div class="cc-need">{WN12}{text}</div>'
    return (
        f'<div class="cc {cls}"><div class="cc-scan"><i></i></div><div class="cc-top">'
        f'<span class="w-logo" style="background:{v.bg};width:44px;height:44px">{v.mono}</span>'
        f'<div style="flex:1"><div class="cc-t">{esc(v.title)}</div><div class="cc-m">{esc(v.company)} · {esc(v.city)} · {esc(v.mode)}</div></div>{badge}</div>'
        f'<div class="cc-sc"><b>{v.shown}<small>/100</small></b><span style="font-size:12px;color:var(--amber);font-weight:600">{delta}</span></div>'
        f'<div class="cc-bar">{segs}</div><div class="cc-ck">{checks}</div>'
        f'<div class="cc-ft">{close}<div class="cc-pill">Demo data<small>No source date</small></div></div>{need}</div>'
    )


def step5(cur: int, done: bool) -> str:
    roles = shortlist_roles()
    pos = {-2: "l2", -1: "l1", 0: "c0", 1: "r1", 2: "r2"}
    first_v = next((i for i, v in enumerate(roles) if v.standing == "verify"), None)
    cards = []
    for i, v in enumerate(roles):
        o = i - cur
        cls = pos.get(o, "hl" if o < 0 else "hr")
        if i == cur:
            cls += " doneck" if done else " run"
        cards.append(cc_card(v, cls, i == first_v))
    slots = []
    for i, v in enumerate(roles):
        fin = done or i < cur
        now = not done and i == cur
        if not fin and not now:
            slots.append(f'<div class="slot wait">{i + 1} · waiting</div>')
            continue
        state = "Eligible" if v.standing == "eligible" else "Needs 1 answer"
        color = "color:var(--amber)" if fin and v.standing != "eligible" else ""
        slots.append(
            f'<div class="slot{" cur" if now or (done and i == cur) else ""}">'
            f'<span class="w-logo" style="background:{v.bg};width:28px;height:28px">{v.mono}</span>'
            f'<div><div class="t">{esc(v.company.replace(" Group", ""))}</div><div class="s" style="{color}">'
            f'{"Checking…" if now else state}</div></div><b>{"…" if now else v.shown}</b></div>'
        )
    n_verify = sum(v.standing == "verify" for v in roles)
    sub = (
        f'All 5 checked · <b style="color:var(--amber)">{n_verify} need one answer from you</b>' if done
        else f"Checking your top matches one by one · <b>{cur + 1} of 5</b>"
    )
    return (
        f'<div class="cr"><div class="cr-h"><div class="w-h1">Building your shortlist</div><div class="w-sub" id="cr-sub">{sub}</div></div>'
        f'<div class="cr-row" id="cr-row">{"".join(cards)}</div><div class="slots" id="cr-slots">{"".join(slots)}</div></div>'
    )


def preview_rows(ans: dict) -> str:
    moves = store.movement(BEFORE, ans, as_of=AS_OF)
    rows = []
    for i, v in enumerate(store.ranked(ans, AS_OF)[:5], start=1):
        mv = moves.get(v.id, "—")
        up = mv == "New" or mv.startswith("↑")
        rows.append(
            f'<div class="mr{" nw" if up else ""}"><span class="p">{i}</span>'
            f'<span class="w-logo" style="background:{v.bg};width:28px;height:28px">{v.mono}</span>'
            f'<div><div class="nm">{esc(v.title)}</div><div class="co">{esc(v.company)} · {esc(v.city)}</div></div>'
            f'<span class="mv" style="color:{"var(--green)" if up else "var(--t3)"}">{mv}</span></div>'
        )
    return "".join(rows)


def step6() -> str:
    body = M.S_6
    choice = S["ob_uk"]
    ks = ["yes", "no", "unsure"]
    opts = re.findall(r'<div class="o6[^"]*">', body)
    for k, o in zip(ks, opts):
        body = body.replace(o, f'<div class="o6{" on" if k == choice else ""}" data-k="{k}">', 1)
    before, after = store.counts(None), store.counts(choice)
    # The UK roles and what each answer does, counted as the question screen counts them.
    uk = store.uk_roles()
    more = f" and {len(uk) - 3} more" if len(uk) > 3 else ""
    yes, no = store.counts("yes"), store.counts("no")
    body = swap(body, "<b>14 roles in London</b>", f"<b>{len(uk)} roles in the UK</b>")
    body = swap(
        body, re.escape("Replai, Bolton Consulting Group, Lazarde &amp; Co. and 11 more"),
        esc(", ".join(v.company for v in uk[:3])) + more,
    )
    body = swap(body, re.escape(">+11 roles<"), f">+{yes['eligible'] - before['eligible']} roles<")
    body = swap(body, re.escape(">4 roles stay<"), f">{no['eligible'] - before['eligible']} roles stay<")
    label = {"yes": "Yes", "no": "No", "unsure": "I’m not sure"}[choice]
    body = body.replace("<h3>If you answer “Yes”</h3>", f"<h3>If you answer “{label}”</h3>")

    def v(old: int, new: int) -> str:
        if old == new:
            return str(new)
        dlt = new - old
        return f"<s>{old}</s>{new}" + (f"<small>+{dlt}</small>" if dlt > 0 else "")

    body = re.sub(
        r'<div class="st6">.*?</div></div></div>',
        f'<div class="st6"><div><div class="l">Eligible roles</div><div class="v">{v(before["eligible"], after["eligible"])}</div></div>'
        f'<div><div class="l">To verify</div><div class="v">{v(before["verify"], after["verify"])}</div></div></div>',
        body, count=1, flags=re.S,
    )
    body = re.sub(
        r'<div class="mini">.*?</div></div></div>\s*<div style="flex:1">',
        f'<div class="mini">{preview_rows({**BEFORE, "uk_work": choice})}</div></div>\n<div style="flex:1">',
        body, count=1, flags=re.S,
    )
    return body


def ring(score: int) -> str:
    return (
        '<svg width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="27" stroke="#EDEDF0" stroke-width="5" fill="none"/>'
        f'<circle cx="32" cy="32" r="27" stroke="#0071E3" stroke-width="5" fill="none" stroke-linecap="round" '
        f'stroke-dasharray="{169.6 * score / 100:.1f} 169.6" transform="rotate(-90 32 32)"/></svg>'
    )


def step7() -> str:
    ans = store.answers()
    top = store.ranked(ans, AS_OF)[:5]
    moves = store.movement(BEFORE, ans, as_of=AS_OF)
    c, c0 = store.counts(), store.counts(None)
    items = []
    for i, v in enumerate(top):
        mv = moves.get(v.id, "—")
        up = mv == "New" or mv.startswith("↑")
        n = clock.days_until(v.closes)
        urgent = n <= 9
        month, day = ("SEP", v.closes[-2:].lstrip("0")) if v.closes[5:7] == "09" else ("OCT", v.closes[-2:].lstrip("0"))
        gap = (
            f'<span class="ix">{WN12}{esc(v.gaps[0])}</span>' if v.gaps else '<span class="in">No gaps found</span>'
        )
        first_ok = next((t for k, t in v.card_checks if k == "ok"), v.highlight)
        show = S["ob_filter"] == 0 or (S["ob_filter"] == 1 and urgent) or (S["ob_filter"] == 2 and mv == "New")
        items.append(
            f'<div class="it{" top" if i == 0 else ""}" style="{"" if show else "display:none"}">'
            f'<div class="it-rk">{i + 1}<small style="color:{"var(--green)" if up else "var(--t3)"}">{mv}</small></div>'
            f'<div class="it-sc">{ring(v.shown)}<b>{v.shown}</b></div>'
            f'<div class="it-main"><span class="w-logo" style="background:{v.bg};width:40px;height:40px">{v.mono}</span>'
            f'<div style="min-width:0"><div class="it-t">{esc(v.title)}</div>'
            f'<div class="it-m">{esc(v.company)} · {esc(v.city)} · {esc(v.mode)} · {"Eligible" if v.standing == "eligible" else "To verify"}</div></div></div>'
            f'<div class="it-ln"><span class="ig">{CK12}{esc(first_ok)}</span>{gap}</div>'
            f'<div class="dt"><span class="cal{" u" if urgent else ""}"><i>{month}</i><b>{day}</b></span><div>'
            f'<div class="k{" u" if urgent else ""}">{"Closes in %d days" % n if urgent else "Closes " + esc(v.closes_label)}</div>'
            f'<small>{"Apply this week" if urgent else "%d days left" % n}</small></div></div>'
            f'<div class="fs"><span class="d" style="background:#C7C7CC"></span><div>Demo data<small>No source date</small></div></div>'
            f'<div class="btn">{"Start application" if i == 0 else "Open"}</div></div>'
        )
    closing = sum(clock.days_until(v.closes) <= 9 for v in top)
    new = sum(moves.get(v.id) == "New" for v in top)
    f = S["ob_filter"]
    seg = (
        f'<span class="segm"><span class="{"on" if f == 0 else ""}">All 5</span>'
        f'<span class="{"on" if f == 1 else ""}">Closing this week · {closing}</span>'
        f'<span class="{"on" if f == 2 else ""}">New · {new}</span></span>'
    )
    gained = c["eligible"] - c0["eligible"]
    lead = top[0]
    lead_n = clock.days_until(lead.closes)
    sub = (
        f"Your answer unlocked {gained} roles. " if gained > 0 else "Your shortlist is ready. "
    ) + f"<b>Start with {esc(lead.company)} — it closes in {lead_n} days.</b>"
    uk = store.uk()
    chip = {"yes": '<span class="w-b ok">Yes</span>', "no": '<span class="w-b am">No · needs sponsorship</span>',
            "unsure": '<span class="w-b ne">Not sure</span>', None: '<span class="w-b ne">Unknown</span>'}[uk]
    delta = f"<small>+{gained}</small>" if gained > 0 else ""
    uk_line = (
        f"Work authorization · UK {chip}<span style=\"color:var(--t3);margin-left:8px\">Declared by you</span>"
        if uk_declared() else
        'Work authorization · UK <span style="color:var(--t3);text-decoration:line-through">Unknown</span> → '
        f'{chip}<span style="color:var(--t3);margin-left:8px">Recalculated {d.updated}</span>'
    )
    return (
        f'<div class="f7"><div class="f7-top"><div><div class="w-h1">Your priorities</div><div class="w-sub">{sub}</div></div>'
        f'<div class="s5-sum"><div class="s5-k"><div class="l">Eligible</div><div class="v">{c["eligible"]}{delta}</div></div>'
        f'<div class="s5-k"><div class="l">To verify</div><div class="v" style="color:var(--amber)">{c["verify"]}</div></div>'
        f'<div class="s5-k"><div class="l">Excluded</div><div class="v" style="color:var(--t3)">{c["excluded"]}</div></div></div></div>'
        f'<div class="f7-flt">{seg}<div class="chg2"><svg width="13" height="13" viewBox="0 0 16 16"><path d="M10.5 2.5l3 3L6 13H3v-3z" '
        'stroke="#6E6E73" stroke-width="1.5" fill="none" stroke-linejoin="round"/></svg>'
        f'{uk_line}</div></div>'
        f'<div class="f7-list">{"".join(items)}</div></div>'
    )


# ───────────────────────── Frame ─────────────────────────

html(
    '<div class="bgx"><i style="width:620px;height:420px;left:-120px;top:-140px;background:#CFE3FB"></i>'
    '<i style="width:560px;height:380px;right:-100px;top:60px;background:#E4DDF7"></i>'
    '<i style="width:640px;height:360px;left:420px;bottom:-200px;background:#DDF0E6"></i>'
    '<i style="width:420px;height:300px;right:260px;bottom:-120px;background:#FBEBD5;opacity:.7"></i></div>'
)

with st.container(key="otop"):
    html(
        '<div class="w-brand"><div class="mark"><svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 11 7 3l4 8M4.6 8h4.8" '
        'stroke="#fff" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div><b>Applicable.ai</b></div>'
    )
    pills = []
    for n, name in enumerate(STEP_NAMES, start=1):
        cls = " done" if n < num else " cur" if n == num else ""
        mark = CK_WHITE if n < num else str(n)
        pills.append(f'<span class="w-st{cls}"><span class="c">{mark}</span>{name}</span>')
        if n < 7:
            pills.append(f'<span class="w-ln{" done" if n + 1 <= num else ""}"></span>')
    with st.container(key="osteps"):
        html(f'<div class="w-steps gl">{"".join(pills)}</div>')
    for n, box in enumerate(TOP, start=1):
        if n > 3 and not (explored() or store.preferences()):
            continue  # Explore is not optional: no jumping past it
        target = next(k for k, s, _, _ in FLOW if s == n)
        overlay(f"st{n}", box, f"Go to step {n}: {STEP_NAMES[n - 1]}", on_click=go, args=(target,))
    with st.container(key="oexit"):
        if st.button("Save and exit", key="exit"):
            finish()
            tabs.go("home")
        html(f'<span class="av">{esc(store.initials(store.user()["name"]))}</span>')

with st.container(key="obody"):
    if step == "1":
        # The screen is a placeholder so the file card itself can show the CV being read.
        screen = st.empty()

        def draw(reading: tuple[str, int] | None = None) -> None:
            markup = squash(f'<section class="w-sec">{step1(reading)}</section>')
            screen.markdown(f'<div class="x">{orange(markup)}</div>', unsafe_allow_html=True)

        draw()
        with st.container(key="oup"):
            up = st.file_uploader("Drop your CV here", type=["pdf"], key="ob-cv", label_visibility="collapsed")
        x, y, w = CV_STATUS
        st.markdown(
            f"<style>.stApp .st-key-ocv{{position:absolute!important;z-index:7;left:{x}px;top:{y}px;width:{w}px!important}}</style>",
            unsafe_allow_html=True,
        )
        with st.container(key="ocv"):
            # Emptied first, so an earlier error never sits over the card while a new CV is read.
            status = st.empty()
            if up is not None and S["ob_cv"] != up.file_id:
                S["ob_cv"] = up.file_id
                draw((up.name, up.size))
                read_cv(up.getvalue())
                S["ob_file"] = (up.name, up.size) if store.candidate() else None
                st.rerun()
            if store.extraction_error():
                status.error(f"We couldn’t read your CV. {store.extraction_error()}")
    elif step == "2":
        html(f'<section class="w-sec">{step2()}</section>')
        right, y, w, h = EDIT_2
        st.markdown(f"<style>.stApp .st-key-oo-edit{{left:auto!important;right:{right}px}}</style>", unsafe_allow_html=True)
        if overlay("edit", (0, y, w, h), "Edit profile", on_click=open_editor):
            edit_profile()
    elif step == "3a":
        if S["ob_prefs"] is None:  # reached without Explore, e.g. "Adjust preferences"
            S["ob_prefs"] = pref_rows()
        html(f'<section class="w-sec">{step3a()}</section>')
        overlay("to3b", SEG_3A[0], "1 · Explore", on_click=go, args=("3b",))

        def set_level(r: int, i: int) -> None:
            S["ob_prefs"] = [dict(p, level=ranking.IMPORTANCE[i]) if j == r else p for j, p in enumerate(S["ob_prefs"])]

        for r in range(len(S["ob_prefs"])):
            for i, x in enumerate(IMP_X):
                overlay(f"imp{r}{i}", (x, IMP_Y0 + r * IMP_DY, 107, 25), IMPORTANCE[i], on_click=set_level, args=(r, i))
    elif step == "3b":
        html(f'<section class="w-sec">{step3b()}</section>')
        if explored():
            overlay("to3a", SEG_3B[1], "2 · Fine-tune", on_click=to_fine_tune)


        def swipe(verdict: str) -> None:
            if len(S["ob_swipes"]) < len(STORIES["stories"]):
                S["ob_swipes"] = [*S["ob_swipes"], verdict]

        if len(S["ob_swipes"]) < len(STORIES["stories"]):
            for i, (dirn, label, sc) in enumerate(
                [("l", "Not for me", "ArrowLeft"), ("u", "Not sure", "ArrowUp"), ("r", "I’d enjoy this", "ArrowRight")]
            ):
                overlay(f"sw{dirn}", ACTS_3B[i], label, on_click=swipe, args=(dirn,), shortcut=sc)
        # Dragging the card: animates in the browser, then presses the button above.
        with st.container(key="aa-js-swipe"):
            st.html(f"<script>{SWIPE_JS}</script>", unsafe_allow_javascript=True)
    elif step == "4":
        html(f'<section class="w-sec">{step4()}</section>')
    elif step == "5":
        done_now = S["ob_tick"] >= 5

        @st.fragment(run_every=None if done_now else 1.7)
        def shortlist() -> None:
            tick = S["ob_tick"]
            done = tick >= 5
            cur = 2 if done else tick
            html(f'<section class="w-sec">{step5(cur, done)}</section>')
            if not done:
                S["ob_tick"] = tick + 1
                if S["ob_tick"] >= 6:
                    st.rerun()
            elif not done_now:
                st.rerun()

        shortlist()
    elif step == "6":
        html(f'<section class="w-sec">{step6()}</section>')
        for i, k in enumerate(["yes", "no", "unsure"]):
            overlay(f"o6{k}", OPTS_6[i], k, on_click=S.__setitem__, args=("ob_uk", k), shortcut=str(i + 1))
    elif step == "7":
        html(f'<section class="w-sec">{step7()}</section>')
        for i, box in enumerate(FILT_7):
            overlay(f"flt{i}", box, ["All", "Closing this week", "New"][i], on_click=S.__setitem__, args=("ob_filter", i))
        top = store.ranked(store.answers(), AS_OF)[:5]
        if S["ob_filter"] == 0:
            for i, v in enumerate(top):
                if overlay(f"it{i}", BTN_7[i], f"Open {v.company}"):
                    finish()
                    if i == 0:
                        store.save_application(v.id)
                        tabs.go("applications", id=v.id)
                    tabs.go("role", id=v.id)

if step == "3b" and not explored():
    info = "<b>Step 3 of 7</b> · Swipe every story to continue — or use ← ↑ → on your keyboard"
unweighted = step == "3a" and not any(weight(r) for r in S["ob_prefs"])
if unweighted:
    info = "<b>Step 3 of 7</b> · Mark at least one preference to continue"
gated = step == "2" and not store.work_auth_complete()
if gated:
    info = f"<b>Step 2 of 7</b> · {NEEDS_WORK_AUTH}"
if step == "5" and uk_declared():
    info, cta = "<b>Step 5 of 7</b> · Your UK work authorization is already declared", "View shortlist"

with st.container(key="ofoot"):
    html(f'<span class="i">{info}</span>')
    if idx > 0:
        if st.button("Back", key="back"):
            back = KEYS[idx - 1]
            go("5" if back == "6" and uk_declared() else back)  # step 6 is skipped both ways
            st.rerun()
    waiting = (step == "5" and S["ob_tick"] < 5) or (step == "3b" and not explored()) or unweighted
    if st.button(cta, type="primary", key="next", disabled=waiting or gated):
        if step == "3b":
            S["ob_prefs"] = pref_rows()
        if step == "3a":
            store.set_preferences(S["ob_prefs"])
        if step == "6":
            store.set_uk(S["ob_uk"])
            st.toast(f"Answer saved · Work authorization · UK = {store.UK_LABELS[S['ob_uk']]}")
        if step == "7":
            v = store.ranked(store.answers(), AS_OF)[0]
            store.save_application(v.id)
            S["flash"] = f"Application started · {v.company}"
            finish()
            tabs.go("applications", id=v.id)
        go(KEYS[idx + 1])
        st.rerun()
