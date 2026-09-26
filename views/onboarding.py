"""Onboarding — seven steps from CV to a first shortlist (00_Onboarding.html).

Upload CV → Profile → Preferences (describe, then explore by swiping) →
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

from core import clock, explore, store
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
    ("3a", 3, "<b>Step 3 of 7</b> · Change anytime — your ranking updates instantly", "Find my roles"),
    ("3b", 3, "<b>Step 3 of 7</b> · Swipe or use ← ↑ → on your keyboard", "Continue"),
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
SEG_3A = [(33, 27, 104, 28), (139, 27, 98, 28)]
IMP_Y = [391, 439, 487, 535, 583, 631, 680]
IMP_X = [588, 697, 806, 915]
ACTS_3B = [(422, 645, 61, 104), (505, 652, 49, 90), (576, 645, 72, 104)]
SEG_3B = [(24, 4, 104, 26)]
OPTS_6 = [(230, 375, 600, 68), (230, 453, 600, 68), (230, 531, 600, 68)]
FILT_7 = [(33, 107, 56, 26), (91, 107, 157, 26), (249, 107, 75, 26)]
#: Where a CV reading error sits: in the file card's place, below the drop zone.
CV_STATUS = (428, 458, 664)
BTN_7 = [(1336, 194, 135, 34), (1405, 324, 66, 34), (1405, 454, 66, 34), (1405, 583, 66, 34), (1405, 713, 66, 34)]

IMPORTANCE = ["Must have", "Important", "Nice to have", "Don’t mind"]

# ───────────────────────── State ─────────────────────────

S = st.session_state
S.setdefault("ob_step", "1")
S.setdefault("ob_imp", [0, 1, 1, 1, 2, 2, 3])
S.setdefault("ob_swipes", [])  # one verdict per story seen, in story order: "r" | "l" | "u"
S.setdefault("ob_tick", 0)
S.setdefault("ob_uk", "yes")
S.setdefault("ob_filter", 0)
S.setdefault("ob_file", None)  # (name, size in bytes) of the CV read
S.setdefault("ob_cv", None)

qs = st.query_params.get("step")
if qs in KEYS and S.get("_ob_qs") != qs:
    S["_ob_qs"] = qs
    S["ob_step"] = qs

step = S["ob_step"]
idx = KEYS.index(step)
key, num, info, cta = FLOW[idx]


def finish() -> None:
    """Leaving the wizard for the first time: the guided tour comes next."""
    if store.stage() == "onboarding":
        store.set_stage("tour")
        S["tour_step"] = 0


def go(k: str) -> None:
    S["ob_step"] = k
    if k == "5":
        S["ob_tick"] = 0


BEFORE = {**store.answers(), "uk_work": None}
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
    if shown:
        name, size = shown
        status, bar = ("Reading your CV…", '<div class="u-pb run"><i></i></div>') if reading else (
            "Read · 100%", '<div class="u-pb"><i style="width:100%"></i></div>')
        body = swap(body, re.escape("Synthetic_CV_Giulia_Rossi.pdf"), esc(name))
        body = swap(body, re.escape("Reading text · 64%"), status)
        body = swap(body, re.escape("184 KB · 2 pages"), f"{max(1, round(size / 1024))} KB")
        body = swap(body, re.escape('<div class="u-pb"><i></i></div>'), bar)
    if store.extraction_error() and not reading:  # the error takes the file card's place
        body = body.replace('<div class="w-card u-file">', '<div class="w-card u-file" style="visibility:hidden">')
    return body


#: Profile sections read from the CV: card title and CandidateProfile field.
CV_SECTIONS = [("Skills", "skills"), ("Education", "education"), ("Experience", "experience")]
#: Sections the mockup shows that CV extraction does not read.
UNREAD_SECTIONS = ["Work authorization", "Sponsorship", "Languages"]
#: How many skills a card lists before summarising the rest as "+N".
SKILL_CHIPS = 8
#: How many values an education or experience card lists before "+N more".
CARD_LINES = 3
#: How many quotes each section shows on the CV page, which does not scroll.
PAGE_QUOTES = 3

#: The mockup's own icons, by card title, and its source-line document icon.
ICONS = {title: icon for icon, title in re.findall(r'<div class="ic">(.*?)</div><b>(.*?)</b>', M.S_2)}
DOC_ICON = re.search(r'<div class="p-src">(<svg.*?</svg>)', M.S_2).group(1)
FOUND = '<span class="w-b ok"><i></i>Found</span>'
NOT_FOUND = '<span class="w-b ne"><i></i>Not found</span>'
NOT_READ = '<span class="w-b ne"><i></i>Not read</span>'


def profile_card(title: str, badge: str, body: str, src: str = "") -> str:
    source = f'<div class="p-src">{DOC_ICON}{src}</div>' if src else ""
    return (
        f'<div class="w-card p-s"><div class="p-h"><div class="ic">{ICONS[title]}</div>'
        f"<b>{title}</b>{badge}</div>{body}{source}</div>"
    )


def fact_quote(profile, fact) -> str:
    """The CV text a fact rests on, for hovering over the fact."""
    quotes = {e.evidence_id: e.quote for e in profile.provenance.evidence}
    return " … ".join(" ".join(quotes[i].split()) for i in fact.evidence_ids)


def section_quotes(profile, field: str) -> list[str]:
    """The distinct CV quotes behind one section, in order. Several facts
    often rest on the same line of the CV; that line counts once."""
    return list(dict.fromkeys(fact_quote(profile, f) for f in getattr(profile, field)))


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
    facts = getattr(profile, field)
    if not facts:
        return profile_card(title, NOT_FOUND, '<div class="p-v">Not stated in your CV</div>')

    def item(fact, tag: str, cls: str = "") -> str:
        return f'<{tag}{cls} title="{esc(fact_quote(profile, fact))}">{esc(fact.value)}</{tag}>'

    if field == "skills":
        chips = "".join(item(f, "span", ' class="w-chip"') for f in facts[:SKILL_CHIPS])
        if len(facts) > SKILL_CHIPS:
            chips += f'<span class="w-chip">+{len(facts) - SKILL_CHIPS}</span>'
        body = f'<div class="p-chips">{chips}</div>'
    else:
        first, rest = facts[0], facts[1:CARD_LINES]
        more = len(facts) - CARD_LINES
        lines = " · ".join(item(f, "span") for f in rest) + (f" · +{more} more" if more > 0 else "")
        body = f'<div class="p-v">{item(first, "span")}</div>' + (f'<div class="p-m">{lines}</div>' if lines else "")
    return profile_card(title, FOUND, body, f"From your CV · {quote_count(len(section_quotes(profile, field)))}")


def cv_page(profile) -> str:
    """The CV panel: the quotes each section was read from, highlighted."""
    if profile is None:
        return '<div class="p-m" style="margin-top:0">Quotes from your CV appear here once it has been read.</div>'
    filler = '<div class="p-ln" style="width:92%"></div><div class="p-ln" style="width:78%"></div>'
    blocks = []
    for title, field in CV_SECTIONS:
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
        distinct = {q for _, field in CV_SECTIONS for q in section_quotes(profile, field)}
        quotes = quote_count(len(distinct))
    cards = [cv_card(profile, title, field) for title, field in CV_SECTIONS] + [
        profile_card(title, NOT_READ, '<div class="p-v">Not read from your CV</div>') for title in UNREAD_SECTIONS
    ]
    body = swap(body, r'<div class="w-sub">.*?</div>', f'<div class="w-sub">{sub}</div>')
    body = swap(
        body, r'<div class="p-grid">.*?</div></div>\n<div class="p-r">',
        f'<div class="p-grid">{"".join(cards)}</div></div>\n<div class="p-r">',
    )
    body = swap(body, re.escape("Your CV<span>Page 2 of 2</span>"), f"Your CV<span>{quotes}</span>")
    return swap(body, r'<div class="p-page">.*?</div></div>$', f'<div class="p-page">{cv_page(profile)}</div></div>')


def step3a() -> str:
    body = M.S_3A
    rows = iter(S["ob_imp"])

    def seg(_m: re.Match) -> str:
        on = next(rows)
        spans = "".join(
            f'<span class="{"on" + (" must" if i == 0 else " imp" if i == 1 else "") if i == on else ""}">{t}</span>'
            for i, t in enumerate(IMPORTANCE)
        )
        return f'<div class="v3-seg">{spans}</div>'

    body = re.sub(r'<div class="v3-seg">.*?</div>', seg, body, flags=re.S)
    # The demo roles carry no pay data, so nothing is filtered: say so.
    body = swap(
        body, re.escape("<b>312</b><span>roles fit · 41 unpaid removed by your must-have</span>"),
        f"<b>{len(store.views())}</b><span>demo roles · preferences shape your Preference fit</span>",
    )
    if S["ob_imp"][0] != 0:  # "Paid internship" is no longer a must-have
        body = body.replace('<span class="v3-p m"><small>Must</small>Paid</span>', '<span class="v3-p"><small>Value</small>Paid</span>')
    return body


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
        f'{n[explore.UNSURE]}. What we learned is on the right. Continue to rank your roles.</div></div>'
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
    # The swipes shape this panel only; the ranking never reads them.
    return swap(
        body, re.escape("This is for you, not employers. It adjusts your Preference fit only — you review it before it’s used."),
        "Just for you: it never changes your ranking.",
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
    return (
        f'<div class="f7"><div class="f7-top"><div><div class="w-h1">Your priorities</div><div class="w-sub">{sub}</div></div>'
        f'<div class="s5-sum"><div class="s5-k"><div class="l">Eligible</div><div class="v">{c["eligible"]}{delta}</div></div>'
        f'<div class="s5-k"><div class="l">To verify</div><div class="v" style="color:var(--amber)">{c["verify"]}</div></div>'
        f'<div class="s5-k"><div class="l">Excluded</div><div class="v" style="color:var(--t3)">{c["excluded"]}</div></div></div></div>'
        f'<div class="f7-flt">{seg}<div class="chg2"><svg width="13" height="13" viewBox="0 0 16 16"><path d="M10.5 2.5l3 3L6 13H3v-3z" '
        'stroke="#6E6E73" stroke-width="1.5" fill="none" stroke-linejoin="round"/></svg>Work authorization · UK '
        f'<span style="color:var(--t3);text-decoration:line-through">Unknown</span> → {chip}'
        f'<span style="color:var(--t3);margin-left:8px">Recalculated {d.updated}</span></div></div>'
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
    elif step == "3a":
        html(f'<section class="w-sec">{step3a()}</section>')
        overlay("to3b", SEG_3A[1], "2 · Explore", on_click=go, args=("3b",))

        def set_imp(r: int, i: int) -> None:
            S["ob_imp"] = [i if j == r else v for j, v in enumerate(S["ob_imp"])]

        for r, y in enumerate(IMP_Y):
            for i, x in enumerate(IMP_X):
                overlay(f"imp{r}{i}", (x, y, 107, 25), IMPORTANCE[i], on_click=set_imp, args=(r, i))
    elif step == "3b":
        html(f'<section class="w-sec">{step3b()}</section>')
        overlay("to3a", SEG_3B[0], "1 · Describe", on_click=go, args=("3a",))


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

with st.container(key="ofoot"):
    html(f'<span class="i">{info}</span>')
    if idx > 0:
        label = "Skip for now" if step == "3b" else "Back"
        if st.button(label, key="back"):
            go(KEYS[idx + 1] if step == "3b" else KEYS[idx - 1])
            st.rerun()
    waiting = step == "5" and S["ob_tick"] < 5
    if st.button(cta, type="primary", key="next", disabled=waiting):
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
