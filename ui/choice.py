"""Single-choice selectors (segmented controls and pills) that always keep one
option lit.

Streamlit clears a single-select control when its lit option is clicked again,
which would leave the glass capsule with nothing selected and the screen back
on its fallback. These wrappers undo that: a second click on the lit option
does nothing.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

SHOWN = "_{}_shown"  # the option lit on the last run, per widget key


def _hold(key: str) -> None:
    """on_change: a click on the lit option cleared it, so light it again."""
    if st.session_state.get(key) is None:
        st.session_state[key] = st.session_state.get(SHOWN.format(key))


def _one(widget: Callable, label: str, options, key: str, default=None, **kw):
    # The default goes in through Session State, not the widget's own
    # default: _hold also writes that key, and Streamlit warns when a widget
    # has both.
    if default is not None:
        st.session_state.setdefault(key, default)
    value = widget(label, options, key=key, on_change=_hold, args=(key,), **kw)
    st.session_state[SHOWN.format(key)] = value
    return value


def segmented(label: str, options, key: str, default=None, **kw):
    """st.segmented_control that cannot be switched off."""
    return _one(st.segmented_control, label, options, key, default, **kw)


def pills(label: str, options, key: str, default=None, **kw):
    """Single-select st.pills that cannot be switched off."""
    return _one(st.pills, label, options, key, default, **kw)
