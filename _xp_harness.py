# Temporary visual-check harness (deleted after the check).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import streamlit as st
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
from core import store
from ui.theme import inject
inject(); store.init()
if "xp_init" not in st.session_state:
    from oi.intelligence.extraction import extract_candidate
    from tests.test_candidate_extraction import FakeModelClient, fact, make_cv, make_fields
    roles = [fact(f"Senior Business Analyst Intern at Mediobanco Corporate & Investment Banking {i}", "Summer Analyst, Mediobanco, June-August 2025") for i in range(1, 6)]
    skills = [fact(f"Skill number {i}", "Skills: Python, SQL, Excel, Valuation") for i in range(1, 13)]
    st.session_state[store.CANDIDATE] = extract_candidate(make_cv(), FakeModelClient(fields=make_fields(experience=roles, skills=skills)))
    st.session_state["ob_step"] = "2"
    st.session_state["xp_init"] = 1
st.navigation([st.Page("views/onboarding.py")], position="hidden").run()
