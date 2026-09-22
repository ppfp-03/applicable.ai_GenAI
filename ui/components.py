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

from html import escape

from oi.contracts import Evidence, Opportunity, Requirement, Verdict

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
