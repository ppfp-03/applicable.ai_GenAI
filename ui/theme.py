"""Deliver the stylesheets to the page.

The approved mockups carry their own CSS; `ui/css/` holds it, split into one
shared file and one file per screen. Every file goes through
`ui.palette.orange()` on the way out, so the blues the mockups were drawn in
reach the browser as the palette's oranges.

Delivery goes through `static/`: Streamlit strips `<style>` elements from
`st.html()`, so each stylesheet is written to a hashed file and linked with
`st.markdown`, which carries a `<link>` through. The hash in the name means a
changed file is fetched fresh and an unchanged one is never rewritten.

The mockups are drawn on a 1600 px stage. `inject()` also sets the page zoom
so that stage fills the window width, the way the mockups scale themselves.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import streamlit as st

from ui.palette import orange

_UI_DIR = Path(__file__).resolve().parent
_CSS_DIR = _UI_DIR / "css"
_STATIC_DIR = _UI_DIR.parent / "static"

#: Width of the mockups' stage, in CSS pixels.
STAGE_WIDTH = 1600

_ZOOM_JS = f"""
<script>
(function(){{
  const fit=()=>{{const k=Math.max(.5,Math.min(window.innerWidth/{STAGE_WIDTH},1.25));
    document.documentElement.style.zoom=k;}};
  if(!window.__aaZoom){{window.__aaZoom=1;window.addEventListener('resize',fit);}}
  fit();
}})();
</script>
"""


#: A selector that starts with a keyed-container class, at the start of a rule
#: or after a comma. Streamlit's own emotion classes are injected after our
#: stylesheet, so a bare `.st-key-x` loses to them on equal specificity.
_KEYED = re.compile(r'(\A|[{},/])(\s*)(?=\.st-key-|\[class\*="st-key-)', re.MULTILINE)


def _strengthen(css: str) -> str:
    """Prefix keyed-container selectors with `.stApp` so they win."""
    return _KEYED.sub(lambda m: f"{m.group(1)}{m.group(2)}.stApp ", css)


def _mtime(name: str) -> float:
    """Modification time of one stylesheet, so edits bust the cache."""
    return (_CSS_DIR / f"{name}.css").stat().st_mtime


@lru_cache(maxsize=32)
def _published(name: str, mtime: float) -> str:
    """Write one stylesheet under static/ and return its served URL.

    Args:
        name: Stylesheet name in ui/css/, without extension.
        mtime: Its modification time; part of the cache key only.

    Returns:
        The app-relative URL of the published copy.
    """
    css = _strengthen(orange((_CSS_DIR / f"{name}.css").read_text(encoding="utf-8")))
    digest = hashlib.sha256(css.encode("utf-8")).hexdigest()[:12]
    target = _STATIC_DIR / f"aa-{name}-{digest}.css"
    if not target.exists():
        for stale in _STATIC_DIR.glob(f"aa-{name}-*.css"):
            stale.unlink()
        target.write_text(css, encoding="utf-8")
    return f"app/static/{target.name}"


def _link(name: str) -> None:
    st.markdown(
        f'<link rel="stylesheet" href="{_published(name, _mtime(name))}">',
        unsafe_allow_html=True,
    )


def inject() -> None:
    """Link the shared stylesheet and fit the stage to the window.

    Call once in `app.py`, before the page runs.
    """
    _link("base")
    with st.container(key="aa-js"):
        st.html(_ZOOM_JS, unsafe_allow_javascript=True)


def page_css(name: str) -> None:
    """Link one screen's stylesheet. Call at the top of that screen."""
    _link(name)
