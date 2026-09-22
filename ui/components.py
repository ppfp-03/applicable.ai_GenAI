"""Pure render helpers: data in, HTML string out.

Every function here is pure -- same input, same markup, no Streamlit calls and
no state. The markup mirrors design-system/components/<Name>/preview.html and
uses that system's `aa-` classes, so the stylesheet does the visual work and
this module only decides structure.

These functions render; they never act. A button written into this HTML cannot
reach Python, so anything clickable is a native Streamlit widget placed beside
the rendered block. See design-system/30-streamlit.md.

On escaping. Text arriving here comes from CVs, job postings and model output,
none of which is trusted. `hl()` escapes it, and applies the highlight span
*before* escaping, because escaping changes the length of the string: "&"
becomes "&amp;" and every offset after it would otherwise shift.
"""

from __future__ import annotations

import re
from html import escape

from oi.contracts import (
    Evidence,
    Opportunity,
    ReqStatus,
    Requirement,
    Source,
    Verdict,
)

#: Requirement status -> the verdict colour its segment takes in the bar.
_REQ_SEGMENT: dict[str, str] = {
    "met": "is-go",
    "confirm": "is-clarify",
    "conflict": "is-skip",
}

#: Under this many days, the deadline is styled as urgent.
_SOON_DAYS = 10

#: Label and glyph per verdict. Closed has no glyph: the design system renders
#: it as a dashed outline, since it is history rather than a decision.
_VERDICTS: dict[str, tuple[str, str]] = {
    "apply": ("is-go", "✓"),
    "clarify": ("is-clarify", "?"),
    "skip": ("is-skip", "–"),
    "closed": ("is-closed", ""),
}

_DEFAULT_LABELS: dict[str, str] = {
    "apply": "Apply this week",
    "clarify": "Answer 1 question first",
    "skip": "Not for now",
    "closed": "Closed",
}


def _span_is_usable(span: tuple[int, int] | None, length: int) -> bool:
    """Report whether a highlight span can be applied to text of `length`.

    A malformed span means a bug upstream, not something the reader should be
    shown an error for: the caller falls back to plain text.
    """
    if span is None:
        return False
    start, end = span
    return 0 <= start < end <= length


def hl(evidence: Evidence) -> str:
    """Render evidence text with its highlighted span, fully escaped.

    Args:
        evidence: The quote and the span to mark within it.

    Returns:
        HTML-safe text, with the marked span wrapped in `<span class="aa-hl">`.
        When there is no span, or it does not fit the text, the escaped text is
        returned unmarked.
    """
    text = evidence.text
    span = evidence.highlight

    if not _span_is_usable(span, len(text)):
        return escape(text)

    start, end = span
    # Escape each piece separately, so the marker sits at the boundary the
    # original offsets describe rather than at a shifted one.
    return (
        f"{escape(text[:start])}"
        f'<span class="aa-hl">{escape(text[start:end])}</span>'
        f"{escape(text[end:])}"
    )


def verdict_chip(verdict: Verdict, label: str | None = None) -> str:
    """Render the decision chip that opens every opportunity.

    Args:
        verdict: One of "apply", "clarify", "skip", "closed".
        label: Overrides the default wording, e.g. the short "Apply" used on
            a card inside a section already titled "Apply this week".

    Returns:
        The chip markup: glyph plus word, never colour alone.

    Raises:
        ValueError: If `verdict` is not one of the four.
    """
    if verdict not in _VERDICTS:
        raise ValueError(
            f"Unknown verdict {verdict!r}. "
            f"Expected one of {', '.join(sorted(_VERDICTS))}."
        )

    css_class, glyph = _VERDICTS[verdict]
    word = escape(label if label is not None else _DEFAULT_LABELS[verdict])
    disc = f"<i>{glyph}</i>" if glyph else ""

    return f'<span class="aa-verdict {css_class}">{disc}{word}</span>'


def deadline(days: int) -> str:
    """Render the deadline pill.

    Args:
        days: Days until the posting closes.

    Returns:
        The pill markup, marked urgent under ten days.
    """
    soon = " is-soon" if days < _SOON_DAYS else ""
    word = "day" if abs(days) == 1 else "days"
    return f'<span class="aa-deadline{soon}">⏱ <b>{days} {word}</b></span>'


def requirement_bar(requirements: list[Requirement]) -> str:
    """Render the segmented bar summarising requirement statuses.

    One segment per requirement, coloured by status, followed by the plain
    count. The count is what carries the meaning; the bar makes it glanceable.

    Args:
        requirements: The requirements to summarise.

    Returns:
        The bar markup plus an "N of M met" caption.
    """
    segments = "".join(
        f'<span class="{_REQ_SEGMENT.get(r.status, "is-clarify")}"></span>'
        for r in requirements
    )
    met = sum(1 for r in requirements if r.status == "met")
    return (
        f'<span class="req"><span class="aa-reqbar">{segments}</span>'
        f"{met} of {len(requirements)} met</span>"
    )


def card_top(opportunity: Opportunity, show_verdict: bool = True) -> str:
    """Render everything on an opportunity card except its button.

    The card is five lines and no more: verdict and deadline, title, meta,
    one why sentence, requirement bar. Sources, factor breakdowns and tags
    belong on the opportunity page, not here.

    Args:
        opportunity: The opportunity to render.
        show_verdict: Pass False inside a section whose heading already states
            the verdict, so the card does not repeat its own section title.

    Returns:
        The card's inner markup. The caller places a native Streamlit button
        beside it -- a button in this HTML could not reach Python.
    """
    chip = verdict_chip(opportunity.verdict) if show_verdict else ""
    caption = "provisional" if opportunity.provisional else "priority"

    meta = " · ".join(
        part
        for part in (opportunity.company, opportunity.city, opportunity.contract)
        if part
    )

    # The `aa-opp2` wrapper is what the stylesheet hangs the card's layout
    # rules off (.aa-opp2 .top, .title, .why ...). Streamlit's own bordered
    # container supplies the card surface, so `aa-card` is deliberately not
    # repeated here -- that would draw a second border inside the first.
    return (
        f'<div class="aa aa-opp2">'
        f'<div class="top">{chip}{deadline(opportunity.deadline_days)}'
        f'<span class="pr">{opportunity.priority}<small>{caption}</small></span></div>'
        f'<div class="title">{escape(opportunity.title)}</div>'
        f'<div class="aa-small">{escape(meta)}</div>'
        f'<p class="why">{hl(opportunity.why)}</p>'
        f"</div>"
    )


# --------------------------------------------------------------------------
# The redesign's components.
#
# Everything above renders the first pass. Everything below is the approved
# direction: eligibility separated from fit, the score never shown without
# its four factors, warnings kept apart from gaps.
# --------------------------------------------------------------------------

#: Monograms we spell by hand, where initials alone would read badly.
_MONOGRAMS: dict[str, str] = {}

#: Eligibility outcome -> the word shown beside it. Never colour alone.
_ELIGIBILITY_WORD: dict[str, str] = {
    "met": "Eligible",
    "confirm": "Verify",
    "conflict": "Conflict",
}

#: Eligibility outcome -> its glyph, so the state survives without colour.
_ELIGIBILITY_GLYPH: dict[str, str] = {"met": "✓", "confirm": "?", "conflict": "–"}


def set_monograms(overrides: dict[str, str]) -> None:
    """Install the hand-written monograms from the dataset.

    Args:
        overrides: Company name -> the two letters to show.
    """
    _MONOGRAMS.clear()
    _MONOGRAMS.update(overrides)


def monogram(company: str) -> str:
    """Two letters standing in for a company, never its real logo.

    Args:
        company: The company name.

    Returns:
        Two uppercase letters: the hand-written pair where the dataset gives
        one, else the initials of the first two words, else the first two
        letters of the only word.
    """
    if company in _MONOGRAMS:
        return _MONOGRAMS[company]
    words = [w for w in re.split(r"[^A-Za-z]+", company) if w]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return (words[0][:2] if words else "?").upper()


def mono_tile(company: str, size: int = 48, tint: str = "") -> str:
    """Render the company monogram tile.

    Args:
        company: The company name.
        size: 32, 40, 48 or 56 -- the sizes the stylesheet defines.
        tint: "", "brand", "go" or "clarify".

    Returns:
        The tile markup.
    """
    classes = "aa-mono-logo"
    if size != 48:
        classes += f" sz-{size}"
    if tint:
        classes += f" tint-{tint}"
    return f'<span class="{classes}">{escape(monogram(company))}</span>'


def source_line(source: Source) -> str:
    """Render one source attribution: the kind badge and where it came from.

    Args:
        source: The source to attribute.

    Returns:
        The mono-spaced source line.
    """
    return (
        f'<span class="aa-src"><span class="aa-doc">{escape(source.kind)}</span>'
        f"{escape(source.where)}</span>"
    )


def eligibility_chip(status: ReqStatus, long: bool = False) -> str:
    """Render the hard-constraint verdict as a pill.

    This is deliberately not `verdict_chip`: eligibility and fit must never
    borrow each other's language. The word carries the meaning; the colour
    only reinforces it.

    Args:
        status: The strictest outcome among an opportunity's checks.
        long: Whether to spell the outcome out in full.

    Returns:
        The pill markup.
    """
    cls = {"met": "is-go", "confirm": "is-clarify", "conflict": "is-skip"}[status]
    word = _ELIGIBILITY_WORD[status]
    if long:
        word = {
            "met": "Eligible under checked rules",
            "confirm": "Needs verification",
            "conflict": "Blocked by a rule",
        }[status]
    return (
        f'<span class="aa-verdict {cls}"><i>{_ELIGIBILITY_GLYPH[status]}</i>'
        f"{word}</span>"
    )


def gap_note(requirements: list[Requirement]) -> str:
    """Render the requirement summary with the open gap named.

    A bar alone says how many are missing; it never says which. Naming the
    first open requirement is what makes the line worth reading.

    Args:
        requirements: The requirements to summarise.

    Returns:
        The bar, the count, and the name of the first thing still open.
    """
    segments = "".join(
        f'<span class="{_REQ_SEGMENT.get(r.status, "is-clarify")}"></span>'
        for r in requirements
    )
    met = sum(1 for r in requirements if r.status == "met")
    open_reqs = [r for r in requirements if r.status != "met"]
    if open_reqs:
        first = open_reqs[0]
        word = "to confirm" if first.status == "confirm" else "blocked"
        tail = f' · <span class="gap">1 {word}:</span> {escape(first.ask)}'
        if len(open_reqs) > 1:
            tail = (
                f' · <span class="gap">{len(open_reqs)} {word}:</span> '
                f"{escape(first.ask)} +{len(open_reqs) - 1}"
            )
    else:
        tail = ""
    return (
        f'<span class="aa-reqnote"><span class="aa-reqbar">{segments}</span>'
        f"<span><b>{met} of {len(requirements)} met</b>{tail}</span></span>"
    )


def band_cell(label: str, count: int, unit: str, tail: str, urgent: bool = False) -> str:
    """Render one cell of the dashboard's attention band.

    Not a KPI: each cell names something to act on and ends with where it
    leads. A number with no next step has no place on this page.

    Args:
        label: The heading, e.g. "Closing soon".
        count: How many.
        unit: What they are, e.g. "within 7 days".
        tail: The line that says what to do about it.
        urgent: Whether this cell is the one asking for an answer.

    Returns:
        The cell markup.
    """
    cls = "aa-bandcell is-clarify" if urgent else "aa-bandcell"
    return (
        f'<div class="{cls}"><span class="aa-label">{escape(label)}</span>'
        f'<span class="k"><b>{count}</b><span>{escape(unit)}</span></span>'
        f'<span class="go">{escape(tail)}</span></div>'
    )


def lead_card(opportunity: Opportunity) -> str:
    """Render the first decision on the page, at full weight.

    The card's chrome -- the mandarin edge, the radius, the lift -- belongs to
    the Streamlit container this markup goes inside, so that the view's one
    primary button can sit within the same card instead of under it.

    Args:
        opportunity: The opportunity to render.

    Returns:
        The card's inner markup, button excluded.
    """
    posted = (
        f" · posted {opportunity.posted_days_ago} d ago"
        if opportunity.posted_days_ago is not None
        else ""
    )
    meta = " · ".join(
        p for p in (opportunity.company, opportunity.city, opportunity.contract) if p
    )
    return (
        f'<div class="aa aa-lead-head"><div class="head">'
        f"{mono_tile(opportunity.company, 56, 'brand')}"
        f'<div style="flex-grow:1;min-width:0">'
        f'<div class="aa-row" style="gap:9px">'
        f"{eligibility_chip(opportunity.eligibility_status)}"
        f"{deadline(opportunity.deadline_days)}</div>"
        f'<h3 class="title">{escape(opportunity.title)}</h3>'
        f'<p class="aa-small">{escape(meta)}{escape(posted)}</p></div>'
        f'<div class="aa-pri"><span class="num">{opportunity.priority}</span>'
        f'<span class="cap">priority</span></div></div>'
        f'<p style="margin:14px 0 0;font-size:15px;line-height:24px">'
        f"{hl(opportunity.why)}</p></div>"
    )


def list_row(opportunity: Opportunity, selected: bool = False) -> str:
    """Render one row of the opportunities list, beside the detail pane.

    Args:
        opportunity: The opportunity to render.
        selected: Whether this is the row the detail pane is showing.

    Returns:
        The row markup.
    """
    status = opportunity.eligibility_status
    classes = "aa-li"
    if selected:
        classes += " is-on"
    if opportunity.verdict == "skip":
        classes += " is-skip"
    cls = {"met": "is-go", "confirm": "is-clarify", "conflict": "is-skip"}[status]
    pill = (
        f'<span class="aa-verdict {cls}" style="height:21px;font-size:11px;'
        f'padding:0 8px 0 3px;gap:5px"><i style="width:15px;height:15px;'
        f'font-size:9px">{_ELIGIBILITY_GLYPH[status]}</i>'
        f"{_ELIGIBILITY_WORD[status]}</span>"
    )
    return (
        f'<div class="{classes}">'
        f"{mono_tile(opportunity.company, 32, 'brand' if selected else '')}"
        f'<div style="min-width:0">{pill}'
        f'<p class="t">{escape(opportunity.title)}</p>'
        f'<p class="aa-small" style="font-size:12px">'
        f"{escape(opportunity.company)} · {escape(opportunity.city)}</p></div>"
        f'<div style="text-align:right">'
        f'<span style="font:800 16px/1 var(--font-display)">{opportunity.priority}</span>'
        f'<span class="aa-small" style="display:block;font-size:11.5px;margin-top:4px">'
        f"{opportunity.deadline_days} d</span></div></div>"
    )


def decision_strip(opportunity: Opportunity, rank: int, total: int) -> str:
    """Render the two halves of the decision: the gate, then the ranking.

    They sit side by side with a rule between them because they are different
    kinds of claim. The left half can stop an application; the right half only
    orders what is already allowed.

    Args:
        opportunity: The opportunity to render.
        rank: Its position in the list.
        total: How many opportunities there are.

    Returns:
        The strip markup.
    """
    passed = sum(1 for c in opportunity.eligibility if c.status == "met")
    return (
        f'<div class="aa aa-strip"><div>'
        f'<p class="aa-sech">Eligibility · checked by rules</p>'
        f'<div class="aa-row" style="gap:10px;margin-top:8px">'
        f"{eligibility_chip(opportunity.eligibility_status, long=True)}"
        f'<span class="aa-small">{passed} of {len(opportunity.eligibility)} pass</span>'
        f"</div></div>"
        f'<div class="rule"></div><div>'
        f'<p class="aa-sech">Priority · weighted score</p>'
        f'<div class="aa-row" style="gap:12px;margin-top:8px">'
        f'<span style="font:800 28px/1 var(--font-display);letter-spacing:-.02em">'
        f"{opportunity.priority}</span>"
        f'<span class="aa-small">of 100 · #{rank} of {total}</span>'
        f"</div></div></div>"
    )


def factor_rows(opportunity: Opportunity, labels: dict[str, list[str]]) -> str:
    """Render the score's decomposition: every factor that produced it.

    The number is never shown alone. Each bar is neutral ink, never a verdict
    colour, so fit cannot be mistaken for eligibility.

    Args:
        opportunity: The opportunity whose factors to show.
        labels: Factor key -> [name, one line of plain English].

    Returns:
        The rows plus the total.
    """
    #: Each factor carries at most a quarter of the score.
    per_factor_max = 100 / max(len(opportunity.factors), 1)
    rows = []
    for key, value in opportunity.factors.items():
        name, note = labels.get(key, [key.replace("_", " ").title(), ""])
        width = max(0.0, min(100.0, value / per_factor_max * 100))
        rows.append(
            f'<div class="aa-factor"><span class="lbl">{escape(name)}</span>'
            f'<span class="track"><span class="fill" style="width:{width:.0f}%"></span></span>'
            f'<span class="v">{value:.1f}</span>'
            f'<span class="aa-small note">{escape(note)}</span></div>'
        )
    total = sum(opportunity.factors.values())
    rows.append(
        f'<div class="aa-factor is-total">'
        f'<span class="lbl" style="font-weight:700">Priority</span><span></span>'
        f'<span class="v" style="font-size:18px">{total:.1f}</span></div>'
    )
    return f'<div class="aa">{"".join(rows)}</div>'


def eligibility_rows(opportunity: Opportunity) -> str:
    """Render the hard constraints, each with the rule that decided it.

    Args:
        opportunity: The opportunity whose checks to show.

    Returns:
        One row per check, in the order the eligibility layer returns them.
    """
    rows = []
    for check in opportunity.eligibility:
        rows.append(
            f'<div class="aa-elig is-{check.status}">'
            f'<span class="g">{_ELIGIBILITY_GLYPH[check.status]}</span>'
            f'<div><p style="margin:0;font-weight:600">{escape(check.label)}</p>'
            f'<p class="aa-small" style="margin-top:2px">{escape(check.explanation)}</p>'
            f'<p style="margin-top:4px">{source_line(check.source)}</p></div>'
            f'<span class="out">{_ELIGIBILITY_WORD[check.status]}</span></div>'
        )
    return f'<div class="aa">{"".join(rows)}</div>'


def warning_rows(opportunity: Opportunity) -> str:
    """Render the posting's caveats, kept apart from the candidate's gaps.

    Args:
        opportunity: The opportunity whose warnings to show.

    Returns:
        One row per warning, or an empty string when there are none.
    """
    if not opportunity.warnings:
        return ""
    rows = "".join(
        f'<div class="aa-warn"><span class="m">!</span>'
        f"<span>{escape(w.text)}</span></div>"
        for w in opportunity.warnings
    )
    return f'<div class="aa">{rows}</div>'


def req_open(requirement: Requirement) -> str:
    """Render a requirement that is still open, at full width.

    Args:
        requirement: The requirement, with status "confirm" or "conflict".

    Returns:
        The two-column "they ask / you have" block.
    """
    glyph = "?" if requirement.status == "confirm" else "–"
    have = (
        hl(requirement.evidence)
        if requirement.evidence is not None
        else '<span class="aa-none">Not stated in your CV</span>'
    )
    return (
        f'<div class="aa aa-reqopen" style="grid-template-columns:28px minmax(0,1fr) '
        f'minmax(0,1.15fr)"><span class="dot">{glyph}</span>'
        f'<div style="min-width:0"><p class="aa-label" style="margin-bottom:4px">They ask</p>'
        f'<p style="margin:0;font-weight:600">{escape(requirement.ask)}</p>'
        f'<p style="margin-top:6px">{source_line(requirement.job_source)}</p></div>'
        f'<div style="min-width:0"><p class="aa-label" style="margin-bottom:4px">You have</p>'
        f'<p style="margin:0">{have}</p></div></div>'
    )


def req_line(requirement: Requirement, show_sources: bool = False) -> str:
    """Render a satisfied requirement on one line.

    Args:
        requirement: The requirement, with status "met".
        show_sources: Whether to print the quote's source beneath it.

    Returns:
        The single-line row.
    """
    have = hl(requirement.evidence) if requirement.evidence is not None else "—"
    if show_sources and requirement.evidence is not None:
        have += (
            f'<span style="display:block;margin-top:3px">'
            f"{source_line(requirement.evidence.source)}</span>"
        )
    return (
        f'<div class="aa aa-reqline"><span class="ok">✓</span>'
        f'<span class="ask">{escape(requirement.ask)}</span>'
        f"<span>{have}</span></div>"
    )


def mark(text: str) -> str:
    """Render text whose highlight is written inline as ``==like this==``.

    The dataset writes a profile note the way the design system writes one in
    prose. Escaping happens first and the span is added after, so a quote
    containing "&" cannot break the markup.

    Args:
        text: The text, with at most one ``==...==`` span.

    Returns:
        HTML with the span wrapped in the highlighter class.
    """
    parts = text.split("==")
    if len(parts) != 3:
        return escape(text)
    return (
        f'{escape(parts[0])}<span class="aa-hl">{escape(parts[1])}</span>'
        f"{escape(parts[2])}"
    )
