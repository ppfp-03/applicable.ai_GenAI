# ScreenOnboarding

Three steps: **Your CV** (upload + named reading stages) → **Check what we understood** (4 summary numbers + only the 2–3 uncertain items) → **Essentials** (countries, roles, availability, weekly hours) with a live *effect* line. Nothing else is asked up front: visas, languages and licences become questions only when a real opportunity needs them; work permits that follow from citizenship (e.g. Swiss permits for EU citizens) are resolved by rules without asking.

**Streamlit:** single centred column (`st.columns([1,2,1])`); stepper via `st.html()`; `st.pills`, `st.date_input`, `st.segmented_control`; CTA `st.button("Show my week", type="primary")`.
