"""Inject the design system's stylesheet into the Streamlit page.

The design system ships two files -- `tokens.css` (custom properties) and
`bundle.css` (the `aa-` component classes). Both are copied verbatim from
`design-system/` and must not be hand-edited here. A third file,
`redesign.css`, is ours: it is loaded last and carries every change the
redesign makes, so the two copies stay refreshable.

Two wrinkles are worth explaining.

First, delivery. Streamlit 1.64 strips `<style>` elements out of `st.html()`,
so inlining the stylesheet silently produces unstyled markup -- the classes
are in the DOM and nothing paints them. We therefore write the stylesheet to
`static/` and pull it in with a `<link>`, which survives sanitisation, served
by `enableStaticServing`.

Second, the dark palette. `tokens.css` switches on `[data-theme="dark"]`, an
attribute the page is expected to set on `<html>`. Streamlit owns that element
and sets its own theme attributes there, so we cannot add ours. When the
active theme is dark we promote that block to `:root`, where it wins by
cascade order. The design system's own file is never edited; the rewrite
happens on the copy we serve.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import streamlit as st

_UI_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _UI_DIR.parent / "static"

#: The dark block's selector in tokens.css, and what it becomes when promoted.
_DARK_SELECTOR = '[data-theme="dark"]'


def _promote_dark(css: str) -> str:
    """Rewrite a file's dark block so it applies at `:root`.

    Only the selector changes; the declarations inside are left exactly as
    they were written. The light block keeps its own `:root` rule, but the
    dark one comes later in the file and therefore wins.

    Args:
        css: The stylesheet text.

    Returns:
        The same text with the dark scope promoted and any remaining
        attribute-scoped rules (e.g. `[data-theme=dark] .x`) unscoped, since
        those selectors could never match once Streamlit owns `<html>`.
    """
    css = css.replace(_DARK_SELECTOR + " {", ":root {")
    return re.sub(re.escape(_DARK_SELECTOR) + r"\s+", "", css)


@lru_cache(maxsize=2)
def _stylesheet(dark: bool) -> str:
    """Build the stylesheet for one theme, read from disk once per theme.

    Three files, in cascade order: `tokens.css` and `bundle.css` are copies
    from the design system and are never hand-edited, so everything the
    redesign changes lives in `redesign.css` and is loaded last.

    Args:
        dark: Whether to promote the dark palette to `:root`.

    Returns:
        The full CSS text, tokens first so components can use the variables.
    """
    tokens = (_UI_DIR / "tokens.css").read_text(encoding="utf-8")
    bundle = (_UI_DIR / "bundle.css").read_text(encoding="utf-8")
    redesign = (_UI_DIR / "redesign.css").read_text(encoding="utf-8")

    # The stylesheet is served from static/, so font URLs resolve relative to
    # that directory: the "app/static/" prefix the file carries would look for
    # static/app/static/.
    tokens = tokens.replace("url('app/static/", "url('")

    if dark:
        tokens = _promote_dark(tokens)
        redesign = _promote_dark(redesign)

    return "\n".join((tokens, bundle, redesign))


def is_dark() -> bool:
    """Report whether Streamlit is currently rendering the dark theme.

    `st.context.theme` arrives in Streamlit 1.46. If it is unavailable or
    unset, we fall back to light, which is the design system's default.
    """
    try:
        theme = st.context.theme
    except Exception:
        return False
    return bool(theme) and getattr(theme, "type", None) == "dark"


@lru_cache(maxsize=2)
def _published(dark: bool) -> str:
    """Write the stylesheet under static/ and return its served URL.

    The filename carries a hash of the contents, so a changed stylesheet is
    fetched rather than served from cache, and an unchanged one is not
    rewritten on every rerun.
    """
    css = _stylesheet(dark)
    digest = hashlib.sha256(css.encode("utf-8")).hexdigest()[:12]
    name = f"applicable-{'dark' if dark else 'light'}-{digest}.css"

    target = _STATIC_DIR / name
    if not target.exists():
        # Clear older builds for this theme so static/ does not accumulate.
        for stale in _STATIC_DIR.glob(
            f"applicable-{'dark' if dark else 'light'}-*.css"
        ):
            stale.unlink()
        target.write_text(css, encoding="utf-8")

    return f"app/static/{name}"


def inject() -> None:
    """Link the design system's stylesheet into the page.

    Call once in `app.py`, after `st.navigation` has resolved and before the
    page runs. `st.markdown` is the route that carries a `<link>` through to
    the DOM; `st.html` drops it.
    """
    st.markdown(
        f'<link rel="stylesheet" href="{_published(is_dark())}">',
        unsafe_allow_html=True,
    )
