import streamlit as st
from core import store
from ui import shell
shell.topbar("onboarding", store.nav_counts())
st.write("onboarding")
