"""Display-only markup, and the icons the mockups draw inline.

Everything here renders; nothing here acts. Actions are always native
Streamlit widgets placed next to (or on top of) this markup.

Markup goes through `st.markdown(..., unsafe_allow_html=True)` rather than
`st.html()`: in Streamlit 1.64 `st.html()` strips inline SVG, and the
mockups' icons, rings and charts are all SVG. The markup is squashed onto one
line first, so Markdown treats it as a single raw HTML block and never
reinterprets indentation, asterisks or underscores inside it.
"""

from __future__ import annotations

import base64
import re
from html import escape

import streamlit as st

from ui.palette import orange

_BETWEEN_TAGS = re.compile(r">\s+<")
_NEWLINES = re.compile(r"\s*\n\s*")


def squash(markup: str) -> str:
    """Put markup on one line without changing what it renders."""
    return _BETWEEN_TAGS.sub("><", _NEWLINES.sub(" ", markup.strip()))


def html(markup: str) -> None:
    """Render display-only markup. Blues are mapped to the palette on the way.

    Args:
        markup: HTML. It is wrapped in a `.x` root, which resets margins.
    """
    st.markdown(
        f'<div class="x">{orange(squash(markup))}</div>', unsafe_allow_html=True
    )


def esc(text: object) -> str:
    """Escape user or data text for inclusion in markup."""
    return escape(str(text), quote=True)


def svg_uri(svg: str) -> str:
    """An SVG as a data URI, for places that take an image (button labels)."""
    raw = orange(svg)
    if "xmlns" not in raw:
        raw = raw.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    return "data:image/svg+xml;base64," + base64.b64encode(raw.encode()).decode()


def md_icon(svg: str, alt: str = "") -> str:
    """An SVG as a Markdown image, usable inside a widget label."""
    return f"![{alt}]({svg_uri(svg)})"


# ───────────────────────── Icons, verbatim from the mockups ─────────────────────────

MARK = (
    '<span class="mark"><svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 11 7 3l4 8M4.6 8h4.8" '
    'stroke="#fff" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>'
)
SEARCH = (
    '<svg width="15" height="15" viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.5" stroke="#3A3A3C" '
    'stroke-width="1.6" fill="none"/><path d="M10.5 10.5 14 14" stroke="#3A3A3C" stroke-width="1.6" '
    'stroke-linecap="round"/></svg>'
)
BELL = (
    '<svg width="15" height="15" viewBox="0 0 16 16"><path d="M4 11V7.5a4 4 0 0 1 8 0V11l1 1.5H3z M6.5 14h3" '
    'stroke="#3A3A3C" stroke-width="1.5" fill="none" stroke-linejoin="round"/></svg>'
)
PREV = (
    '<svg width="14" height="14" viewBox="0 0 16 16"><path d="M10 3 5 8l5 5" stroke="#3A3A3C" '
    'stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
NEXT = (
    '<svg width="14" height="14" viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" stroke="#3A3A3C" '
    'stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
CK = (
    '<svg width="11" height="11" viewBox="0 0 16 16"><path d="M3 8.5 6.3 12 13 4.5" stroke="#248A3D" '
    'stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
CK12 = (
    '<svg width="12" height="12" viewBox="0 0 16 16"><path d="M3 8.5 6.3 12 13 4.5" stroke="#248A3D" '
    'stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>'
)
CK_WHITE = (
    '<svg width="10" height="10" viewBox="0 0 16 16"><path d="M3 8.5 6.3 12 13 4.5" stroke="#fff" '
    'stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
WN = (
    '<svg width="11" height="11" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#B25E09" '
    'stroke-width="1.8" fill="none"/><path d="M8 4.8v3.6M8 11h0" stroke="#B25E09" stroke-width="2" '
    'stroke-linecap="round"/></svg>'
)
WN12 = (
    '<svg width="12" height="12" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#B25E09" '
    'stroke-width="1.6" fill="none"/><path d="M8 5v3.5M8 11h0" stroke="#B25E09" stroke-width="1.8" '
    'stroke-linecap="round"/></svg>'
)
XR = (
    '<svg width="10" height="10" viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" stroke="#C4302B" '
    'stroke-width="2.4" stroke-linecap="round"/></svg>'
)
SH = (
    '<svg width="16" height="16" viewBox="0 0 16 16" style="flex:none;margin-top:2px"><path d="M8 2 13.5 '
    '4v3.8c0 3-2.3 5.3-5.5 6.2-3.2-.9-5.5-3.2-5.5-6.2V4z" stroke="#0071E3" stroke-width="1.5" fill="none"/>'
    '<path d="M5.7 8.2 7.3 9.8 10.4 6.5" stroke="#0071E3" stroke-width="1.5" fill="none" '
    'stroke-linecap="round"/></svg>'
)
LOCK = (
    '<svg width="13" height="13" viewBox="0 0 16 16"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" '
    'stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" '
    'stroke="currentColor" stroke-width="1.6" fill="none"/></svg>'
)
CLOCK = (
    '<svg width="13" height="13" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="currentColor" '
    'stroke-width="1.6" fill="none"/><path d="M8 5v3l2 1.5" stroke="currentColor" stroke-width="1.6" '
    'fill="none" stroke-linecap="round"/></svg>'
)
CHEV = (
    '<svg width="9" height="9" viewBox="0 0 10 10"><path d="M2 3.5 5 6.5 8 3.5" stroke="#6E6E73" '
    'stroke-width="1.4" fill="none"/></svg>'
)
SPARK = (
    '<svg width="12" height="12" viewBox="0 0 16 16"><path d="M8 2.2 9.3 6.7 13.8 8 9.3 9.3 8 13.8 6.7 9.3 '
    '2.2 8 6.7 6.7z" fill="#0071E3"/></svg>'
)
DOC = (
    '<svg width="11" height="11" viewBox="0 0 16 16"><path d="M4 2h5.5L12 4.5V14H4z" stroke="#AEAEB2" '
    'stroke-width="1.6" fill="none"/></svg>'
)

#: Section and criterion glyphs (16 px viewBox, stroked).
GLYPH = {
    "skills": '<path d="M8 2.2 9.3 6.7 13.8 8 9.3 9.3 8 13.8 6.7 9.3 2.2 8 6.7 6.7z"/>',
    "edu": '<path d="M1.5 6 8 3l6.5 3L8 9z"/><path d="M4.5 7.5v3.2c1 1 2.2 1.5 3.5 1.5s2.5-.5 3.5-1.5V7.5"/>',
    "exp": '<rect x="2" y="4.5" width="12" height="9" rx="1.6"/><path d="M5.5 4.5V3.2c0-.7.5-1.2 1.2-1.2h2.6c.7 0 1.2.5 1.2 1.2v1.3"/>',
    "pref": '<path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11"/><circle cx="5.5" cy="4.5" r="1.3" fill="#fff"/><circle cx="10.5" cy="8" r="1.3" fill="#fff"/><circle cx="7" cy="11.5" r="1.3" fill="#fff"/>',
    "auth": '<rect x="2" y="3" width="12" height="10" rx="1.6"/><circle cx="6" cy="7.2" r="1.6"/><path d="M3.8 11c.4-1.1 1.2-1.7 2.2-1.7s1.8.6 2.2 1.7M10 6.5h2M10 9h2"/>',
    "spons": '<path d="M8 2 13.5 4v3.8c0 3-2.3 5.3-5.5 6.2-3.2-.9-5.5-3.2-5.5-6.2V4z"/><path d="M5.7 8.2 7.3 9.8 10.4 6.5"/>',
    "decl": '<path d="M4 2h5.5L12 4.5V14H4z"/><path d="M6 9.5 7.3 10.8 10 8"/>',
    "lang": '<path d="M2.5 3.5h7M6 2v1.5M4 3.5c.5 2.5 2 4.5 4 5.5M8 3.5c-.5 2.5-2 4.5-4.5 5.5"/><path d="M9 14l2.5-6 2.5 6M9.8 12h3.4"/>',
    "field": '<circle cx="8" cy="8" r="5.5"/><path d="M5.5 8h5M8 5.5v5"/>',
    "loc": '<path d="M8 14s-4.5-4.2-4.5-7.5a4.5 4.5 0 0 1 9 0C12.5 9.8 8 14 8 14z"/><circle cx="8" cy="6.5" r="1.6"/>',
}


def glyph(name: str, color: str | None = None, size: int = 17) -> str:
    """One stroked glyph from GLYPH, as the mockups draw section icons."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 16 16" fill="none" stroke="{color or "#3A3A3C"}" '
        f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{GLYPH[name]}</svg>'
    )


def logo(mono: str, bg: str, size: int, font: float, radius: int = 10) -> str:
    """A company monogram tile (`.lg`)."""
    return (
        f'<span class="lg" style="background:{bg};width:{size}px;height:{size}px;'
        f'font-size:{font}px;border-radius:{radius}px">{esc(mono)}</span>'
    )


def check_icon(status: str) -> str:
    """The round status badge (`.ci`) for met / check / not met."""
    if status == "met":
        return f'<span class="ci">{CK}</span>'
    if status == "not_met":
        return f'<span class="ci r">{XR}</span>'
    return f'<span class="ci a">{WN}</span>'


def hit(key: str, markup: str, label: str = "Select", on_click=None, args=None) -> bool:
    """A tile drawn in markup with a native button over the whole of it.

    The markup is what the user sees; the invisible button is what they
    press. Returns True on the run the tile was clicked.

    Args:
        key: Unique suffix; the container is keyed "hit-<key>".
        markup: The tile.
        label: Accessible name of the button (read by screen readers).
        on_click: Optional callback, as for st.button.
        args: Callback arguments.
    """
    with st.container(key=f"hit-{key}"):
        html(markup)
        return st.button(label, key=f"ov-{key}", on_click=on_click, args=args)
