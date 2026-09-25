"""Deliver the stylesheets to the page.

The approved mockups carry their own CSS; `ui/css/` holds it, split into one
shared file and one file per screen. Every file goes through
`ui.palette.orange()` on the way out, so the blues the mockups were drawn in
reach the browser as the palette's oranges.

Inside the tab host (ui/tabs.py) five screens share one page, so each
screen's stylesheet is confined to its own tab container before publishing:
two screens can style the same class differently without meeting.

Delivery goes through `static/`: Streamlit strips `<style>` elements from
`st.html()`, so each stylesheet is written to a hashed file and linked with
`st.markdown`, which carries a `<link>` through. The hash in the name means a
changed file is fetched fresh and an unchanged one is never rewritten.

The mockups are drawn on a 1600 px stage. `inject()` also sets `--aa-k`, the
zoom that makes that stage fill the window width, and loads the floating glass
top bar (`ui/js/nav.js`). base.css applies it to the stage and the capsule
only: zooming <html> would shrink the 100vh scroll container with it and
leave an empty band under the page.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import streamlit as st

from ui import tabs
from ui.palette import orange

_UI_DIR = Path(__file__).resolve().parent
_CSS_DIR = _UI_DIR / "css"
_STATIC_DIR = _UI_DIR.parent / "static"
_NAV_JS = _UI_DIR / "js" / "nav.js"

#: Width of the mockups' stage, in CSS pixels.
STAGE_WIDTH = 1600

_ZOOM_JS = f"""
<script>
(function(){{
  const fit=()=>{{const k=Math.max(.5,Math.min(window.innerWidth/{STAGE_WIDTH},1.25));
    const h=document.documentElement;h.style.zoom='';h.style.setProperty('--aa-k',k);}};
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


_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_DOC_ROOT = re.compile(r"(html|:root|body)(\S*)\s*(.*)", re.S)


def _split(prelude: str) -> list[str]:
    """Split a selector list on its top-level commas (not those in :not(...))."""
    parts, depth, cur = [], 0, ""
    for ch in prelude:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return [p.strip() for p in parts + [cur] if p.strip()]


def _scope_selector(sel: str, root: str) -> str:
    m = _DOC_ROOT.fullmatch(sel)
    if m:  # html.state .x → html.state <root> .x
        head, rest = m.group(1) + m.group(2), m.group(3)
        return f"{head} {root} {rest}" if rest else sel
    return f"{root} {sel}"


def _scope(css: str, root: str) -> str:
    """Confine every rule in a stylesheet to descendants of `root`.

    @media and @supports are entered; @keyframes and other at-rules are kept
    as they are.
    """
    css = _COMMENT.sub("", css)
    out, i = [], 0
    while True:
        j = css.find("{", i)
        if j < 0:
            break
        depth, k = 1, j + 1
        while depth:
            depth += (css[k] == "{") - (css[k] == "}")
            k += 1
        prelude, body = css[i:j].strip(), css[j + 1 : k - 1]
        if prelude.startswith(("@media", "@supports")):
            out.append(f"{prelude}{{{_scope(body, root)}}}")
        elif prelude.startswith("@"):
            out.append(f"{prelude}{{{body}}}")
        else:
            out.append(",".join(_scope_selector(s, root) for s in _split(prelude)) + f"{{{body}}}")
        i = k
    return "\n".join(out)


def _mtime(name: str) -> float:
    """Modification time of one stylesheet, so edits bust the cache."""
    return (_CSS_DIR / f"{name}.css").stat().st_mtime


@lru_cache(maxsize=32)
def _published(name: str, mtime: float, tab: str | None = None) -> str:
    """Write one stylesheet under static/ and return its served URL.

    Args:
        name: Stylesheet name in ui/css/, without extension.
        mtime: Its modification time; part of the cache key only.
        tab: Confine the rules to this tab's container (ui/tabs.py).

    Returns:
        The app-relative URL of the published copy.
    """
    css = orange((_CSS_DIR / f"{name}.css").read_text(encoding="utf-8"))
    if tab:
        css = _scope(css, f".st-key-tab-{tab}")
    css = _strengthen(css)
    digest = hashlib.sha256(css.encode("utf-8")).hexdigest()[:12]
    stem = f"aa-tab-{name}" if tab else f"aa-{name}"
    target = _STATIC_DIR / f"{stem}-{digest}.css"
    if not target.exists():
        for stale in _STATIC_DIR.glob(f"{stem}-*.css"):
            stale.unlink()
        target.write_text(css, encoding="utf-8")
    return f"app/static/{target.name}"


def _link(name: str, tab: str | None = None) -> None:
    st.markdown(
        f'<link rel="stylesheet" href="{_published(name, _mtime(name), tab)}">',
        unsafe_allow_html=True,
    )


def inject() -> None:
    """Link the shared stylesheet and fit the stage to the window.

    Call once in `app.py`, before the page runs.
    """
    _link("base")
    with st.container(key="aa-js"):
        nav = _NAV_JS.read_text(encoding="utf-8")
        st.html(_ZOOM_JS + f"<script>{nav}</script>", unsafe_allow_javascript=True)


def page_css(name: str) -> None:
    """Link one screen's stylesheet. Call at the top of that screen."""
    _link(name, tabs.running())
