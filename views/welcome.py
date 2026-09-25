"""Welcome — the first thing a visitor sees: landing, sign up, log in.

Access is staged for the demo. Nothing entered here is stored or sent
anywhere, and any input is accepted: signing up leads into onboarding with an
empty account, logging in opens the demo profile as it stands after
onboarding. The stage lives in the session (core/store.py); app.py keeps
every other page closed until the flow allows it.
"""

from __future__ import annotations

import streamlit as st

from core import store
from ui import tabs
from ui.html import MARK, html
from ui.theme import page_css

page_css("welcome")

S = st.session_state
stage = store.stage()

html(
    '<div class="bgx"><i style="width:620px;height:420px;left:-120px;top:-140px;background:#CFE3FB"></i>'
    '<i style="width:560px;height:380px;right:-100px;top:60px;background:#E4DDF7"></i>'
    '<i style="width:640px;height:360px;left:420px;bottom:-200px;background:#DDF0E6"></i>'
    '<i style="width:420px;height:300px;right:260px;bottom:-120px;background:#FBEBD5;opacity:.7"></i></div>'
)

with st.container(key="wtop"):
    html(f'<div class="brand">{MARK}Applicable.ai</div>')


def to(name: str) -> None:
    store.set_stage(name)


if stage == "landing":
    with st.container(key="whero"):
        html(
            '<div class="wh-k">For students and new graduates</div>'
            '<h1 class="wh-h">Know where to apply this week,<br>and why.</h1>'
            '<div class="wh-p">Upload your CV once. Applicable.ai checks every role against the rules that decide '
            'whether you can take it, ranks what’s left, and tells you what to do first.</div>'
        )
        with st.container(key="wacts"):
            st.button("Get started", type="primary", key="w-start", on_click=to, args=("signup",))
            st.button("I have an account", type="tertiary", key="w-have", on_click=to, args=("login",))
        html(
            '<div class="wh-pts">'
            '<div><b>Eligibility first</b><span>Dates, degree and work permits, checked by fixed rules.</span></div>'
            '<div><b>Every claim sourced</b><span>From your CV, the posting, your answers or a rule.</span></div>'
            '<div><b>One question at a time</b><span>Only when a real role needs the answer.</span></div>'
            "</div>"
        )

elif stage == "signup":
    with st.container(key="wcard"):
        html(
            '<div class="wc-h">Create your account</div>'
            '<div class="wc-p">Then we read your CV and build your first shortlist.</div>'
        )
        name = st.text_input("Full name", key="w-name", placeholder="Your name")
        email = st.text_input("Email", key="w-email", placeholder="you@university.edu")
        st.text_input("Password", key="w-pw", type="password")
        if S.get("w-err"):
            html(f'<div class="wc-err">{S["w-err"]}</div>')
        if st.button("Create account", type="primary", key="w-create", width="stretch"):
            if not name.strip():
                S["w-err"] = "Tell us your name."
            elif "@" not in email:
                S["w-err"] = "That email doesn’t look right."
            else:
                store.sign_up(name, email)
                tabs.go("onboarding")
            st.rerun()
        html('<div class="wc-or"><span>or</span></div>')
        if st.button("Continue with Google", key="w-google", width="stretch"):
            store.sign_up(name or "Giulia Rossi", email if "@" in email else "giulia.rossi@example.com")
            tabs.go("onboarding")
        with st.container(key="wswitch"):
            html('<span>Already have an account?</span>')
            st.button("Log in", type="tertiary", key="w-tologin", on_click=to, args=("login",))

elif stage == "login":
    with st.container(key="wcard"):
        html(
            '<div class="wc-h">Welcome back</div>'
            '<div class="wc-p">Pick up where you left off.</div>'
        )
        st.text_input("Email", key="w-lemail", placeholder="you@university.edu")
        st.text_input("Password", key="w-lpw", type="password")
        if st.button("Log in", type="primary", key="w-login", width="stretch"):
            store.log_in()
            tabs.go("home")
        with st.container(key="wswitch"):
            html('<span>New here?</span>')
            st.button("Create an account", type="tertiary", key="w-tosignup", on_click=to, args=("signup",))

with st.container(key="wfoot"):
    html('<span class="syn">DEMO</span>Nothing you enter here is stored or sent anywhere.')
