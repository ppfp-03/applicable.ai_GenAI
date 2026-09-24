"""The one place blue becomes orange.

The approved mockups were drawn in a blue accent. The product's palette is
orange, so every blue or light-blue value they use is mapped here to the
matching step of the orange scale, and nothing else changes: greens, ambers,
reds and greys stay exactly as drawn. The stylesheet copied from the mockups
and any inline colour a page renders both go through `orange()`, so a blue
cannot slip back in from either side.
"""

from __future__ import annotations

import re

#: Mockup blue -> palette orange, darkest to lightest.
HEX = {
    "#0071E3": "#F26A3D",  # accent            -> brand
    "#0B3F7A": "#8A3413",  # ink on light blue -> ink on light orange
    "#5AA2F0": "#F6915F",  # accent, step 2
    "#A9CDF7": "#FAC0A3",  # accent, step 3
    "#B9D6F8": "#FBCDB6",
    "#D6E7FB": "#FDDFD0",  # accent, step 4
    "#CFE3FB": "#FCD8C5",  # background glow
    "#E4DDF7": "#FBE1D5",  # background glow (lavender)
    "#EAF3FE": "#FFEFE7",  # accent background
    "#EEF4FC": "#FEF3ED",
    "#F7FAFF": "#FFF9F6",
}

#: rgb triplets used inside rgba(): the accent and the navy shadow tint.
RGB = {
    "0,113,227": "242,106,61",
    "28,40,64": "64,40,28",
}

_HEX_RE = re.compile("|".join(re.escape(k) for k in HEX), re.IGNORECASE)
_RGB_RE = re.compile(r"rgba?\(\s*(0\s*,\s*113\s*,\s*227|28\s*,\s*40\s*,\s*64)")

# The accent as the pages use it in Python, already mapped.
ACCENT = HEX["#0071E3"]
ACCENT_BG = HEX["#EAF3FE"]
ACCENT_2 = HEX["#5AA2F0"]
ACCENT_3 = HEX["#A9CDF7"]
ACCENT_4 = HEX["#D6E7FB"]
ACCENT_5 = HEX["#EEF4FC"]
ACCENT_INK = HEX["#0B3F7A"]


def orange(text: str) -> str:
    """Replace every mockup blue in `text` with its orange counterpart.

    Args:
        text: CSS or HTML.

    Returns:
        The same text with blues mapped; every other colour untouched.
    """
    text = _HEX_RE.sub(lambda m: HEX[m.group(0).upper()], text)

    def _rgb(m: re.Match[str]) -> str:
        key = re.sub(r"\s+", "", m.group(1))
        return m.group(0).replace(m.group(1), RGB[key])

    return _RGB_RE.sub(_rgb, text)
