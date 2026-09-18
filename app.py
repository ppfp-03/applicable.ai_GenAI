"""Render the initial Applicable.ai application shell."""

import streamlit as st

st.set_page_config(page_title="Applicable.ai")

st.title("Applicable.ai")
st.write(
    "An AI-powered career and application assistant for university students "
    "and recent graduates."
)
st.warning(
    "Development mode: this application is a foundation only. "
    "AI extraction, eligibility checks, and opportunity ranking are not implemented."
)

with st.sidebar:
    st.header("Candidate Profile")
    st.info("Your candidate profile will appear here once this feature is implemented.")

st.header("Top Opportunities")
st.info("Opportunities will appear here once this feature is implemented.")
