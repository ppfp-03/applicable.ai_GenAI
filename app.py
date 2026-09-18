"""Render the initial Applicable.ai application shell."""

import streamlit as st

st.set_page_config(page_title="Applicable.ai")

st.title("Applicable.ai")
st.write("AI-powered application prioritization assistant for students and recent graduates.")
st.warning("Development mode - foundation stage")

with st.sidebar:
    st.header("Candidate Profile")
    st.info("CV upload and candidate information will appear here.")

st.header("Top Opportunities")
st.info("Job prioritization pipeline under development.")
