import streamlit as st
from core import store
from ui import shell
shell.topbar("explore", store.nav_counts())
st.write("explore")
