import streamlit as st
from core import store
from ui import shell
shell.topbar("applications", store.nav_counts())
st.write("applications")
